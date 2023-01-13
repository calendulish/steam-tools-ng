#!/usr/bin/env python
#
# Lara Maia <dev@lara.monster> 2015 ~ 2023
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
from collections import OrderedDict
from xml.etree import ElementTree

import asyncio
import functools
import html
import logging
import traceback
from gi.repository import Gtk, Gdk
from traceback import StackSummary
from types import FrameType
from typing import Any, Callable, List, Optional, Union, Type, Tuple

from stlib import internals
from . import async_gtk
from .. import i18n, config

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
        self._user_callback: Optional[Callable[..., Any]] = None
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
        self._user_callback: Optional[Callable[..., Any]] = None
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
        self.display = Gdk.Display.get_default()
        self._style_provider = Gtk.CssProvider()
        self._style_provider.load_from_data(
            b"label.warning { background-color: darkblue; color: white; }"
            b"label.critical {background-color: darkred; color: white; }"
        )
        self._style_context = self.get_style_context()
        self._style_context.add_provider_for_display(
            self.display,
            self._style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

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


class SimpleTextTree(Gtk.Grid):
    def __init__(
            self,
            *elements: str,
            overlay_scrolling: bool = True,
            resizable: bool = True,
            fixed_width: int = 0,
            model: Callable[..., Union[Gtk.TreeStore, Gtk.ListStore]] = Gtk.TreeStore,
    ) -> None:
        super().__init__()
        self._scrolled_window = Gtk.ScrolledWindow()
        self._scrolled_window.set_overlay_scrolling(overlay_scrolling)
        self.attach(self._scrolled_window, 0, 0, 1, 1)

        # noinspection PyUnusedLocal
        self._store = model(*[str for header in elements])
        self._view = Gtk.TreeView()
        self._view.set_model(self._store)
        self._view.set_hexpand(True)
        self._view.set_vexpand(True)
        self._scrolled_window.set_child(self._view)

        self._lock = False
        self._lock_label = Gtk.Label()
        self._lock_label.hide()
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

        renderer = Gtk.CellRendererText()

        for index, header in enumerate(elements):
            column = Gtk.TreeViewColumn(header, renderer, markup=index)
            column.set_resizable(resizable)

            if fixed_width:
                column.set_fixed_width(fixed_width)

            self._view.append_column(column)

    async def wait_available(self) -> None:
        while self.lock:
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
            self._lock_label.show()
            self._lock = True
        else:
            self.set_focusable(True)
            self.set_sensitive(True)
            self._lock_label.hide()
            self._lock = False

    @property
    def store(self) -> Union[Gtk.TreeStore, Gtk.ListStore]:
        return self._store

    @property
    def view(self) -> Gtk.TreeView:
        return self._view


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
        self.set_size_request(100, 60)

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
    def __init__(self, display_size: int, label_text: str) -> None:
        super().__init__()
        # noinspection PyUnusedLocal
        self._default_display_text = ' '.join(['_' for n in range(1, display_size)])
        self._gtk_settings = Gtk.Settings.get_default()

        self.set_label(label_text)
        self.set_label_align(0.03)

        self._grid = Gtk.Grid()
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
        if value is True:
            self._play_event.set()
        else:
            self._play_event.clear()

    @staticmethod
    def __sanitize_text(text: str, max_length: int) -> str:
        if len(text) >= max_length:
            return text[:max_length] + '...'

        return text

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
        if value is True:
            self._play_pause_button.show()
        else:
            self._play_pause_button.hide()

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


class Section(Gtk.Grid):
    def __init__(self, name: str, label: str) -> None:
        super().__init__()
        # for backward compatibility
        self.grid = self
        self.label = label

        self.set_name(name)
        self.set_row_spacing(10)
        self.set_column_spacing(10)
        self.set_margin_top(10)
        self.set_margin_bottom(10)

    # noinspection PyProtectedMember
    @staticmethod
    def __get_section_name(item: 'Item') -> str:
        assert isinstance(item._section_name, str)
        return item._section_name

    @staticmethod
    def __show(item: 'Item') -> None:
        item.label.show()
        super(item.__class__, item).show()

    @staticmethod
    def __hide(item: 'Item') -> None:
        item.label.hide()
        super(item.__class__, item).hide()

    def new_item(
            self,
            name: str,
            label: str,
            widget: Type[Gtk.Widget],
            *grid_position: int,
            items: Optional[OrderedDict[str, str]] = None,
    ) -> Gtk.Widget:
        bases = (widget,)

        body = {
            'label': Gtk.Label(),
            '_section_name': None,
            '__init__': lambda item_: super(item_.__class__, item_).__init__(),
            'get_section_name': self.__get_section_name,
            'show': self.__show,
            'hide': self.__hide,
        }

        section = self.get_name()
        option = name
        value: Union[str, bool, int]

        item = type('Item', bases, body)()
        assert isinstance(item, Gtk.Widget)

        item.set_hexpand(True)
        item.set_name(name)
        item._section_name = section

        item.label.set_name(name)
        item.label.set_text(label)
        item.label.set_halign(Gtk.Align.START)

        self.grid.attach(item.label, *grid_position, 1, 1)
        self.grid.attach_next_to(item, item.label, Gtk.PositionType.RIGHT, 1, 1)

        if name.startswith('_'):
            return item

        if isinstance(item, Gtk.ComboBoxText):
            assert isinstance(items, OrderedDict), "ComboBox needs items mapping"
            value = config.parser.get(section, option)

            for option_label in items.values():
                item.append_text(_(option_label))

            try:
                current_option = list(items).index(value)
            except ValueError:
                import sys

                error_message = _("Please, fix your config file. Accepted values for {} are:\n{}").format(
                    option,
                    ', '.join(items.keys()),
                )
                log.exception(error_message)
                traceback_info = sys.exc_info()[2]
                fatal_error_dialog(ValueError(error_message), traceback.extract_tb(traceback_info))
                # unset active item
                current_option = -1

            item.set_active(current_option)

        if isinstance(item, Gtk.CheckButton):
            value = config.parser.getboolean(section, option)
            item.set_active(value)

        if isinstance(item, Gtk.Entry):
            value = config.parser.get(section, option)

            if value:
                item.set_text(value)

        return item

    def stackup_section(self, stack: Gtk.Stack) -> None:
        name = self.get_name()
        stack.add_titled(self, name, self.label)


def markup(text: str, **kwargs: Any) -> str:
    markup_string = ['<span']

    for key, value in kwargs.items():
        markup_string.append(f'{key}="{value}"')

    markup_string.append(f'>{html.escape(text)}</span>')

    return ' '.join(markup_string)


def unmarkup(text: str) -> str:
    tree = ElementTree.fromstring(text)
    assert isinstance(tree.text, str)
    return tree.text


def copy_childrens(from_model: Gtk.TreeModel, to_model: Gtk.TreeModel, iter_: Gtk.TreeIter, column: int) -> None:
    childrens = from_model.iter_n_children(iter_)

    if childrens:
        for index in range(childrens):
            children_iter = from_model.iter_nth_child(iter_, index)
            value = from_model.get_value(children_iter, column)

            if value:
                to_model.append([value])
            else:
                log.debug(
                    _("Ignoring value from {} on column {} item {} because value is empty").format(
                        children_iter,
                        column,
                        index
                    )
                )
    else:
        value = from_model.get_value(iter_, column)
        to_model.append([value])


def sanitize_confirmation(value: Optional[List[str]]) -> str:
    if not value:
        result = _("Nothing")
    elif len(value) == 1:
        result = value[0]
    else:
        result = _("Various")

    return result


def sanitize_package_details(package_details: List[internals.Package]) -> List[internals.Package]:
    previous: Optional[Tuple[internals.Package, int, int]] = None

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
    new_text = []

    for char in text:
        if char.isdigit():
            new_text.append(char)

    return ''.join(new_text)


def fatal_error_dialog(
        exception: BaseException,
        stack: Optional[Union[StackSummary, List[FrameType]]] = None,
        transient: Optional[Gtk.Window] = None,
) -> None:
    log.critical("%s: %s", type(exception).__name__, str(exception))

    error_dialog = Gtk.MessageDialog()
    error_dialog.set_transient_for(transient)
    error_dialog.set_title(_("Fatal Error"))
    error_dialog.set_markup(f"{type(exception).__name__}: {str(exception)}")
    error_dialog.set_modal(True)

    message_area = error_dialog.get_message_area()
    secondary_text = Gtk.Label()
    message_area.append(secondary_text)

    if stack:
        log.critical("\n".join([str(frame) for frame in stack]))
        secondary_text.set_text("\n".join([str(frame) for frame in stack]))

    def callback(dialog: Any, _action: Any) -> None:
        loop = asyncio.get_event_loop()
        loop.stop()

        application = Gtk.Application.get_default()

        if application:
            application.quit()

    error_dialog.add_button(_('Ok'), Gtk.ResponseType.OK)
    error_dialog.connect("response", callback)

    error_dialog.show()

    # main application can be not available (like on initialization process)
    if not Gtk.Application.get_default():
        async_gtk.run()


def safe_task_callback(task: asyncio.Task[Any]) -> None:
    if task.cancelled():
        log.debug(_("%s has been stopped due user request"), task.get_coro())
        return

    exception = task.exception()

    if exception and not isinstance(exception, asyncio.CancelledError):
        stack = task.get_stack()
        application = Gtk.Application.get_default()

        fatal_error_dialog(exception, stack, application.get_active_window())
