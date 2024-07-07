#!/usr/bin/env python
#
# Lara Maia <dev@lara.monster> 2015 ~ 2024
#
# The Steam Tools NG is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
#
# The Steam Tools NG is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see http://www.gnu.org/licenses/.
#
import asyncio
import functools
import html
import inspect
import logging
import sys
import traceback
from collections import OrderedDict
from traceback import StackSummary
from types import FrameType
from typing import Any, Callable, List, Type, Tuple
from xml.etree import ElementTree

from gi.repository import Gtk, Gdk, Gio, GObject
from stlib import internals

from . import async_gtk
from .. import i18n, config, core

log = logging.getLogger(__name__)
_ = i18n.get_translation


# noinspection PyUnusedLocal
class ClickableLabel(Gtk.Label):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self.set_hexpand(True)

        pointer = Gdk.Cursor.new_from_name('pointer')
        self.set_cursor(pointer)

        self.gesture = Gtk.GestureClick()
        self.add_controller(self.gesture)

    def connect(self, signal: str, callback: Callable[..., Any]) -> None:
        if signal == 'clicked':
            self.gesture.connect('pressed', callback)
        else:
            raise NotImplementedError


class VariableButton(Gtk.Button):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        super().connect('clicked', self.__callback)
        self._user_callback: Callable[..., Any] | None = None
        self._user_args: Any = None
        self._user_kwargs: Any = None

    def __callback(self, button: Gtk.Button) -> None:
        if not self._user_callback:
            return

        self._user_callback(button, *self._user_args, **self._user_kwargs)

    def connect(self, signal: str, callback: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        if signal != "clicked":
            raise NotImplementedError

        self._user_callback = callback
        self._user_args = args
        self._user_kwargs = kwargs


class AsyncButton(Gtk.Button):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        super().connect('clicked', self.__callback)
        self._user_callback: Callable[..., Any] | None = None
        self._user_args: Any = None
        self._user_kwargs: Any = None

    def __callback(self, button: Gtk.Button) -> None:
        if not self._user_callback:
            return

        loop = asyncio.get_event_loop()
        task = loop.create_task(self._user_callback(button, *self._user_args, **self._user_kwargs))
        task.add_done_callback(safe_task_callback)

    def connect(self, signal: str, callback: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        if signal != "clicked":
            super().connect(signal)
        else:
            self._user_callback = callback
            self._user_args = args
            self._user_kwargs = kwargs

    def emit(self, signal: str) -> None:
        if signal != "clicked":
            super().emit(signal)
        else:
            self.__callback(self)


class StatusBar(Gtk.Grid):
    def __init__(self) -> None:
        super().__init__()
        _separator = Gtk.Separator()
        self.attach(_separator, 0, 0, 1, 1)

        self._status = Gtk.Label()
        self._status.set_hexpand(True)
        self.attach(self._status, 0, 1, 1, 1)

        self.messages = {}
        for module in config.plugins.keys():
            self.messages[module] = {"warning": "", "critical": ""}

        loop = asyncio.get_event_loop()
        task = loop.create_task(self.__loop_messages())
        task.add_done_callback(safe_task_callback)

    async def __loop_messages(self) -> None:
        while True:
            # when query is empty
            if all(all(value == '' for value in messages.values()) for messages in self.messages.values()):
                self._status.set_css_classes([])
                self._status.set_text('')
                await asyncio.sleep(1)
                continue

            for module_name, module_messages in self.messages.items():
                for level in ["warning", "critical"]:
                    if module_messages[level]:
                        self._status.set_css_classes([level])
                        self._status.set_text(f"{module_name}: {module_messages[level]}")
                        await asyncio.sleep(3)

    def set_warning(self, module: str, message: str) -> None:
        self.messages[module]["warning"] = message

    def set_critical(self, module: str, message: str) -> None:
        self.messages[module]["critical"] = message

    def clear(self, module: str) -> None:
        self.messages[module] = {"warning": "", "critical": ""}


class SimpleTextTreeItem(GObject.Object):
    def __init__(self, *args: str, headers: Tuple[str, ...], **kwargs: Any) -> None:
        for name, value in kwargs.items():
            setattr(self, name, value)

        for index, header in enumerate(headers):
            name = header.replace('_', '').replace(' ', '_').lower()

            try:
                setattr(self, name, args[index])
            except IndexError:
                log.debug(f'{name} param not set in {self}')

        super(GObject.Object, self).__init__()
        self.children: List[SimpleTextTreeItem] = []


class SimpleTextTree(Gtk.Grid):
    def __init__(
            self,
            *headers: str,
            overlay_scrolling: bool = False,
            resizable: bool = True,
            fixed_width: int = 0,
    ) -> None:
        super().__init__()
        self.headers = headers

        self._scrolled_window = Gtk.ScrolledWindow()
        self._scrolled_window.set_overlay_scrolling(overlay_scrolling)
        self.attach(self._scrolled_window, 0, 0, 1, 1)

        self._view = Gtk.ColumnView()
        self._view.set_show_column_separators(True)
        self._view.set_hexpand(True)
        self._view.set_vexpand(True)
        self._scrolled_window.set_child(self._view)

        expander_column = Gtk.ColumnViewColumn()
        expander_column.set_resizable(False)
        expander_column.set_fixed_width(25)
        expander_factory = Gtk.SignalListItemFactory()
        expander_factory.connect('setup', self.setup, False)
        expander_factory.connect('bind', self.bind)
        expander_column.set_factory(expander_factory)
        self._view.append_column(expander_column)

        for element in self.headers:
            column = Gtk.ColumnViewColumn()
            column.set_resizable(resizable)

            if element.startswith('_'):
                element = element[1:]
                column.set_title(_(element))

            if fixed_width:
                column.set_fixed_width(fixed_width)

            factory = Gtk.SignalListItemFactory()
            factory.connect('setup', self.setup)
            factory.connect('bind', self.bind, element)
            column.set_factory(factory)
            self._view.append_column(column)

        self._store = Gio.ListStore.new(SimpleTextTreeItem)
        self._tree = Gtk.TreeListModel.new(self._store, False, False, self.item_factory)
        self._tree_sort = Gtk.TreeListRowSorter()
        self._tree_sort.set_sorter(self._view.get_sorter())
        self._list_sort = Gtk.SortListModel()
        self._list_sort.set_sorter(self._tree_sort)
        self._list_sort.set_model(self._tree)
        self._model = Gtk.SingleSelection.new(self._list_sort)
        self._view.set_model(self._model)

        self._lock = False
        self._lock_label = Gtk.Label()
        self._lock_label.set_visible(False)
        self._lock_label.set_vexpand(True)
        self._lock_label.set_hexpand(True)

        self._lock_label.set_markup(
            markup(
                _("Waiting another process"),
                background="#0000FF77",
                color="white",
                font_size="xx-large",
            )
        )

        self.attach(self._lock_label, 0, 0, 1, 1)

        self._disabled = False
        self._disabled_label = Gtk.Label()
        self._disabled_label.set_visible(False)
        self._disabled_label.set_vexpand(True)
        self._disabled_label.set_hexpand(True)

        self._disabled_label.set_markup(
            markup(
                _("Disabled"),
                background="#FF000077",
                color="white",
                font_size="xx-large",
            )
        )

        self.attach(self._disabled_label, 0, 0, 1, 1)

    @staticmethod
    def setup(view: Gtk.ListView, item: Gtk.ListItem, hide_expander: bool = True) -> None:
        expander = Gtk.TreeExpander()
        expander.set_hide_expander(hide_expander)
        label = Gtk.Label()
        expander.set_child(label)
        item.set_child(expander)

    @staticmethod
    def bind(view: Gtk.ListView, item: Gtk.ListItem, element: str | None = None) -> None:
        expander = item.get_child()
        assert isinstance(expander, Gtk.TreeExpander)

        label = expander.get_child()
        assert isinstance(label, Gtk.Label)

        list_row = item.get_item()
        expander.set_list_row(list_row)
        data = list_row.get_item()

        if isinstance(data, Gtk.TreeListRow):
            data = data.get_item()

        if element:
            column_text = getattr(data, element.replace(' ', '_').lower())
            label.set_markup(column_text)
            label.set_hexpand(True)

    def item_factory(self, item: Gtk.ListItem) -> Gtk.TreeListModel | None:
        store = Gio.ListStore.new(SimpleTextTreeItem)

        if isinstance(item, Gtk.TreeListRow):
            item = item.get_item()

        if item.children:
            for child in item.children:
                store.append(child)

            return Gtk.TreeListModel.new(store, False, False, self.item_factory)

        return None

    def new_item(self, *data: str, **kwargs: Any) -> SimpleTextTreeItem:
        return SimpleTextTreeItem(*data, headers=self.headers, **kwargs)

    def append_row(self, row: Gtk.TreeListRow) -> None:
        self._store.append(row)

    def remove_row(self, row: Gtk.TreeListRow) -> bool:
        item = row.get_item()
        found, position = self._store.find(item)

        if found:
            self._store.remove(position)
            return True
        else:
            return False

    def clear(self) -> None:
        self._store.remove_all()

    async def wait_available(self) -> None:
        while self.lock or self.disabled:
            await asyncio.sleep(1)

    @property
    def lock(self) -> bool:
        return self._lock

    @lock.setter
    def lock(self, enable_lock: bool) -> None:
        if enable_lock:
            log.debug(_("Waiting another process"))
            self.set_focusable(False)
            self.set_sensitive(False)
            self._lock_label.set_visible(True)
            self._lock = True
        else:
            self.set_focusable(True)
            self.set_sensitive(True)
            self._lock_label.set_visible(False)
            self._lock = False

    @property
    def disabled(self) -> bool:
        return self._disabled

    @disabled.setter
    def disabled(self, disabled: bool) -> None:
        if disabled:
            self.set_focusable(False)
            self.set_sensitive(False)
            self._disabled_label.set_visible(True)
            self._disabled = True
        else:
            self.set_focusable(True)
            self.set_sensitive(True)
            self._disabled_label.set_visible(False)
            self._disabled = False

    @property
    def tree(self) -> Gtk.TreeListModel:
        return self._tree

    @property
    def store(self) -> Gio.ListStore:
        return self._store

    @property
    def view(self) -> Gtk.ColumnView:
        return self._view

    @property
    def model(self) -> Gtk.SingleSelection:
        return self._model


class SimpleStatus(Gtk.Frame):
    def __init__(self) -> None:
        super().__init__()
        self._style_context = self.get_style_context()
        self._style_provider = Gtk.CssProvider()
        self._style_provider.load_from_data(b"frame { background-color: black; }")
        self._style_context.add_provider(self._style_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self._grid = Gtk.Grid()
        self._grid.set_margin_start(10)
        self._grid.set_margin_end(10)
        self._grid.set_margin_top(10)
        self._grid.set_margin_bottom(10)
        self.set_child(self._grid)

        self._label = Gtk.Label()
        self._label.set_halign(Gtk.Align.START)
        self._grid.attach(self._label, 0, 0, 1, 1)

        self.info(_("Waiting"))
        self.set_hexpand(True)

    def error(self, text: str) -> None:
        self._label.set_markup(markup(text, color='hotpink', face='monospace'))

    def info(self, text: str) -> None:
        self._label.set_markup(markup(text, color='cyan', face='monospace'))


def when_running(function: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(function)
    def wrapper(self: 'Status', *args: Any, **kwargs: Any) -> None:
        if self.play_event.is_set():
            function(self, *args, **kwargs)

    return wrapper


class Status(Gtk.Frame):
    def __init__(self, display_size: int) -> None:
        super().__init__()

        # noinspection PyUnusedLocal
        self._default_display_text = ' '.join(['_' for n in range(1, display_size)])
        self._gtk_settings = Gtk.Settings.get_default()
        self.set_margin_top(0)
        self.set_margin_bottom(0)

        self._grid = Gtk.Grid()
        self._grid.set_margin_top(10)
        self._grid.set_margin_bottom(0)
        self.set_child(self._grid)

        self._display = ClickableLabel()
        self._display.set_markup(markup(self._default_display_text, font_size='large', font_weight='bold'))
        self._display.connect("clicked", self.__on_display_event_changed)
        self._display.set_has_tooltip(True)
        self._grid.attach(self._display, 0, 0, 1, 1)

        self._play_pause_button = Gtk.ToggleButton()
        self._play_pause_button.set_margin_end(10)
        self._play_pause_button.set_icon_name("media-playback-start")
        self._play_pause_button.set_can_focus(False)
        self._play_pause_button.connect("toggled", self.__on_play_pause_button_toggled)
        self._grid.attach(self._play_pause_button, 1, 0, 1, 1)

        self._play_event = asyncio.Event()
        self._play_pause_button.emit("clicked")

        self._status = Gtk.Label()
        self._status.set_markup(markup(_("Loading..."), color='green', font_size='small'))
        self._grid.attach(self._status, 0, 1, 1, 1)

        self._info = Gtk.Label()
        self._grid.attach(self._info, 0, 2, 1, 1)

        self._level_bar = Gtk.LevelBar()
        self._grid.attach(self._level_bar, 0, 3, 2, 1)

        self.display = Gdk.Display.get_default()
        self.clipboard = self.display.get_clipboard()

    @property
    def play_event(self) -> asyncio.Event:
        return self._play_event

    @play_event.setter
    def play_event(self, value: bool) -> None:
        if value:
            self._play_event.set()
        else:
            self._play_event.clear()

    @staticmethod
    def __sanitize_text(text: str, max_length: int) -> str:
        return f'{text[:max_length]}...' if len(text) >= max_length else text

    def __disable_tooltip(self, event_status: Gtk.Label) -> None:
        self._grid.remove(event_status)
        self._grid.attach(self._status, 0, 1, 1, 1)
        self._display.set_has_tooltip(False)
        self._display.set_sensitive(True)

    def __on_display_event_changed(self, *args: Any, **kwargs: Any) -> None:
        message = _("Text Copied to Clipboard")

        if self._gtk_settings.props.gtk_application_prefer_dark_theme:
            color = 'lightblue'
        else:
            color = 'blue'

        self._display.set_tooltip_text(message)

        event_status = Gtk.Label()
        self._grid.remove(self._status)
        self._grid.attach(event_status, 0, 1, 1, 1)

        event_status.set_markup(markup(message, font_size='small', color=color))
        content = Gdk.ContentProvider.new_for_value(self._display.get_text())
        self.clipboard.set_content(content)
        asyncio.get_event_loop().call_later(5, self.__disable_tooltip, event_status)

        self._display.set_sensitive(False)

    def __on_play_pause_button_toggled(self, button: Gtk.ToggleButton) -> None:
        if button.get_active():
            button.set_icon_name("media-playback-pause")
            self.play_event.set()
        else:
            button.set_icon_name("media-playback-start")
            self.play_event.clear()

    def set_pausable(self, value: bool = True) -> None:
        if value:
            self._play_pause_button.set_visible(True)
        else:
            self._play_pause_button.set_visible(False)

    @when_running
    def set_display(self, text: str) -> None:
        text = self.__sanitize_text(text, 25)
        self._display.set_markup(markup(text, font_size='large', font_weight='bold'))

    @when_running
    def set_status(self, text: str) -> None:
        text = self.__sanitize_text(text, 55)
        if self._gtk_settings.props.gtk_application_prefer_dark_theme:
            color = 'lightgreen'
        else:
            color = 'green'

        self._status.set_markup(markup(text, color=color, font_size='small'))

    @when_running
    def set_info(self, text: str) -> None:
        text = self.__sanitize_text(text, 55)
        if self._gtk_settings.props.gtk_application_prefer_dark_theme:
            color = 'lightgreen'
        else:
            color = 'green'

        self._info.set_markup(markup(text, color=color, font_size='small'))

    @when_running
    def set_error(self, text: str) -> None:
        text = self.__sanitize_text(text, 55)
        if self._gtk_settings.props.gtk_application_prefer_dark_theme:
            color = 'hotpink'
        else:
            color = 'red'

        self._status.set_markup(markup(text, color=color, font_size='small'))

    @when_running
    def set_level(self, value: int, max_value: int) -> None:
        self._level_bar.set_value(value)
        self._level_bar.set_max_value(max_value)

    def unset_display(self) -> None:
        self._display.set_markup(markup(self._default_display_text, font_size='large', font_weight='bold'))

    def unset_level(self) -> None:
        self._level_bar.set_value(0)
        self._level_bar.set_max_value(0)


class _SectionItem(Gtk.Grid):
    def __init__(self,
                 section: 'Section',
                 name: str,
                 label: str | None,
                 widget: Type[Gtk.Widget],
                 items: OrderedDict[str, str] | None = None,
                 ) -> None:
        super().__init__()
        self.set_column_homogeneous(True)

        self.section = section
        self.items = items
        self.set_name(name)

        self.widget = widget()
        self.widget.set_hexpand(True)

        if isinstance(self.widget, Gtk.Switch):
            self.widget.set_halign(Gtk.Align.END)

        if label:
            self.label = Gtk.Label()
            self.label.set_name(name)
            self.label.set_text(label)
            # self.label.set_halign(Gtk.Align.START)

            self.attach(self.label, 0, 0, 1, 1)
            self.attach_next_to(self.widget, self.label, Gtk.PositionType.RIGHT, 1, 1)
        else:
            self.attach(self.widget, 0, 0, 1, 1)

        if items:
            string_list = Gtk.StringList()

            for option_label in items.values():
                string_list.append(_(option_label))

            self.widget.set_model(string_list)

    def __getattr__(self, item: str) -> Any:
        return getattr(self.widget, item)

    def __update_dropdown(self) -> None:
        assert isinstance(self.items, OrderedDict), "received None from items"
        value = config.parser.get(self.section.get_name(), self.get_name())

        try:
            current_option = list(self.items).index(value)
        except ValueError:
            error_message = _("Please, fix your config file. Accepted values for {} are:\n{}").format(
                self.name,
                ', '.join(self.items.keys()),
            )
            log.exception(error_message)
            traceback_info = sys.exc_info()[2]
            fatal_error_dialog(ValueError(error_message), traceback.extract_tb(traceback_info))
            # unset active item
            current_option = -1

        self.widget.set_selected(current_option)

    def __update_switch(self) -> None:
        value = config.parser.getboolean(self.section.get_name(), self.get_name())

        self.widget.set_active(value)

    def __update_entry(self) -> None:
        value = config.parser.get(self.section.get_name(), self.get_name())

        self.widget.get_buffer().set_text(value, -1)

    def update_values(self) -> None:
        if config.config_file.is_file():
            config.parser.read(config.config_file)
        else:
            log.debug("Config file not read")

        if isinstance(self.widget, Gtk.DropDown):
            self.__update_dropdown()
        elif isinstance(self.widget, Gtk.Switch):
            self.__update_switch()
        else:
            self.__update_entry()

    def set_visible(self, state: bool) -> None:
        self.label.set_visible(state)
        super(self.__class__, self).set_visible(state)

    def connect(self, name: str, callback: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        self.widget.connect(name, lambda widget, *data: callback(self, *data, *args, **kwargs))


class Section(Gtk.Grid):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.items: List[_SectionItem] = []

        self.set_name(name)
        self.set_row_spacing(10)
        self.set_margin_top(10)
        self.set_margin_bottom(10)
        self.set_margin_start(10)
        self.set_margin_end(10)

    def new_item(
            self,
            name: str,
            label: str | None,
            widget: Type[Gtk.Widget],
            *grid_position: int,
            items: OrderedDict[str, str] | None = None,
    ) -> Gtk.Widget:
        item = _SectionItem(self, name, label, widget, items=items)
        self.attach(item, *grid_position, 1, 1)
        self.items.append(item)

        if not name.startswith('_'):
            item.update_values()

        return item

    def stackup_section(self, text: str, stack: Gtk.Stack, *, scroll: bool = False) -> None:
        name = self.get_name()

        if scroll:
            scrolled_window = Gtk.ScrolledWindow()
            scrolled_window.set_overlay_scrolling(True)
            scrolled_window.set_child(self)
            stack.add_titled(scrolled_window, name, text)
        else:
            stack.add_titled(self, name, text)


class PopupWindowBase(Gtk.Window):
    def __init__(self, parent_window: Gtk.Window, application: Gtk.Application) -> None:
        super().__init__()
        self.parent_window = parent_window
        self.application = application

        self.set_default_size(400, 50)
        self.set_transient_for(parent_window)
        self.set_destroy_with_parent(True)
        self.set_modal(True)
        self.set_resizable(False)

        self.header_bar = Gtk.HeaderBar()
        self.set_titlebar(self.header_bar)

        self.gtk_settings_class = Gtk.Settings.get_default()

        self.content_grid = Gtk.Grid()
        self.content_grid.set_row_spacing(10)
        self.content_grid.set_column_spacing(10)
        self.set_child(self.content_grid)

        self.connect('destroy', lambda *args: self.destroy())
        self.connect('close-request', lambda *args: self.destroy())

        self.key_event = Gtk.EventControllerKey()
        self.add_controller(self.key_event)

        self.key_event.connect('key-released', self.on_key_released_event)

    def on_key_released_event(
            self,
            controller: Gtk.EventControllerKey,
            keyval: int,
            keycode: int,
            state: Gdk.ModifierType
    ) -> None:
        if keyval == Gdk.KEY_Escape:
            self.destroy()


def markup(text: str, **kwargs: Any) -> str:
    markup_string = ['<span']

    markup_string.extend(f'{key}="{value}"' for key, value in kwargs.items())
    markup_string.append(f'>{html.escape(text)}</span>')

    return ' '.join(markup_string)


def unmarkup(text: str) -> str:
    tree = ElementTree.fromstring(text)
    assert isinstance(tree.text, str)
    return tree.text


def sanitize_confirmation(value: List[str] | None) -> str:
    if not value:
        return _("Nothing")
    elif len(value) == 1:
        return value[0]
    else:
        return _("Various")


def sanitize_package_details(package_details: List[internals.Package]) -> List[internals.Package]:
    previous: Tuple[internals.Package, int, int] | None = None

    for package in package_details:
        for index, app in enumerate(package.apps):
            if not previous:
                previous = (package, index, app)
                continue

            if previous[2] != app:
                return package_details

    assert isinstance(previous, tuple)
    return [previous[0]]


def remove_letters(text: str) -> str:
    new_text = [char for char in text if char.isdigit()]
    return ''.join(new_text)


def fatal_error_dialog(
        exception: BaseException,
        stack: StackSummary | List[FrameType] | None = None,
        parent: Gtk.Window | None = None,
) -> None:
    log.critical("%s: %s", type(exception).__name__, str(exception))

    error_dialog = Gtk.AlertDialog()
    error_dialog.set_buttons([_("Ok")])
    error_dialog.set_message(f"{type(exception).__name__} > {str(exception)}")
    error_dialog.set_modal(True)

    if stack:
        log.critical("\n".join([str(frame) for frame in stack]))
        error_dialog.set_detail("\n".join([str(frame) for frame in stack]))

    def callback(*args: Any) -> None:
        application = Gtk.Application.get_default()

        if application:
            application.quit()

        core.safe_exit()

    error_dialog.choose(parent=parent, callback=callback)

    # main application can be not available (like on initialization process)
    if not Gtk.Application.get_default():
        async_gtk.run()


def safe_task_callback(task: asyncio.Task[Any]) -> None:
    if task.cancelled():
        coro = task.get_coro()
        assert inspect.iscoroutine(coro), "isn't coro?"
        log.debug(_("%s has been stopped due user request"), coro.__name__)
        return

    exception = task.exception()

    if exception and not isinstance(exception, KeyboardInterrupt):
        stack = task.get_stack()
        application = Gtk.Application.get_default()

        fatal_error_dialog(exception, stack, application.get_active_window())


def on_setting_state_set(item: _SectionItem, state: bool) -> None:
    config.new(item.section.get_name(), item.get_name(), state)


def on_setting_changed(item: _SectionItem) -> None:
    current_value = item.get_text()
    config.new(item.section.get_name(), item.get_name(), current_value)


def on_digit_only_setting_changed(item: _SectionItem) -> None:
    current_value = item.get_text()

    if current_value.isdigit():
        config.new(item.section.get_name(), item.get_name(), int(current_value))
    else:
        item.get_buffer().set_text(remove_letters(current_value), -1)


def on_dropdown_setting_changed(item: _SectionItem, _spec: Any, items: OrderedDict[str, str]) -> None:
    current_value = list(items)[item.get_selected()]
    config.new(item.section.get_name(), item.get_name(), current_value)
