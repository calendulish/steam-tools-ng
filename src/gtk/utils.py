#!/usr/bin/env python
#
# Lara Maia <dev@lara.click> 2015 ~ 2018
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
import logging
from typing import Any, Callable, List, NamedTuple, Tuple

import cairo
from gi.repository import Gtk
from stlib import webapi

from .. import i18n

log = logging.getLogger(__name__)
_ = i18n.get_translation


class Section(NamedTuple):
    frame: Gtk.Frame
    grid: Gtk.Grid


class Item(NamedTuple):
    label: Gtk.Label
    children: Gtk.Widget


class SimpleTextTree(Gtk.ScrolledWindow):
    def __init__(
            self,
            elements: Tuple[str, ...],
            overlay_scrolling: bool = True,
            resizable: bool = True,
            fixed_width: int = 0,
            model: Callable[..., Gtk.TreeModel] = Gtk.TreeStore,
    ) -> None:
        super().__init__()
        self._store = model(*[str for number in range(len(elements))])
        renderer = Gtk.CellRendererText()
        self._view = Gtk.TreeView(model=self._store)
        self.add(self._view)

        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_overlay_scrolling(overlay_scrolling)

        for index, header in enumerate(elements):
            column = Gtk.TreeViewColumn(header, renderer, text=index)
            column.set_resizable(resizable)

            if fixed_width:
                column.set_fixed_width(fixed_width)

            self._view.append_column(column)


class SimpleStatus(Gtk.Frame):
    def __init__(self) -> None:
        super().__init__()
        self.connect('draw', self.__do_status_draw)

        self._grid = Gtk.Grid()
        self._grid.set_border_width(10)
        self.add(self._grid)

        self._label = Gtk.Label()
        self._grid.attach(self._label, 0, 0, 1, 1)

        self.info(_("Waiting"))

    @staticmethod
    def __do_status_draw(frame: Gtk.Frame, cairo_context: cairo.Context) -> None:
        allocation = frame.get_allocation()
        cairo_context.set_source_rgb(0.2, 0.2, 0.2)
        cairo_context.rectangle(0, 0, allocation.width, allocation.height)
        cairo_context.fill()

    def error(self, text: str) -> None:
        self._label.set_markup(markup(text, color='hotpink', face='monospace'))

    def info(self, text: str) -> None:
        self._label.set_markup(markup(text, color='cyan', face='monospace'))


class Status(Gtk.Frame):
    def __init__(self, current_text_size: int, label_text: str) -> None:
        super().__init__()
        self.gtk_settings = Gtk.Settings.get_default()

        self.set_label(label_text)
        self.set_label_align(0.02, 0.5)

        self._grid = Gtk.Grid()
        self._grid.set_border_width(5)
        self._grid.set_row_spacing(5)
        self.add(self._grid)

        self._current = Gtk.Label()
        self._current.set_markup(
            markup(' '.join(['_' for n in range(1, current_text_size)]), font_size='large', font_weight='bold'),
        )
        self._current.set_selectable(True)
        self._current.set_hexpand(True)
        self._grid.attach(self._current, 0, 0, 1, 1)

        self._status = Gtk.Label()
        self._status.set_markup(markup(_("Loading..."), color='green', font_size='small'))
        self._grid.attach(self._status, 0, 1, 1, 1)

        self._level_bar = Gtk.LevelBar()
        self._grid.attach(self._level_bar, 0, 2, 1, 1)

    def set_current(self, text: str) -> None:
        self._current.set_markup(markup(text, font_size='large', font_weight='bold'))

    def set_info(self, text: str) -> None:
        if self.gtk_settings.props.gtk_application_prefer_dark_theme:
            color = 'lightgreen'
        else:
            color = 'green'

        self._status.set_markup(markup(text, color=color, font_size='small'))

    def set_error(self, text: str) -> None:
        if self.gtk_settings.props.gtk_application_prefer_dark_theme:
            color = 'hotpink'
        else:
            color = 'red'

        self._status.set_markup(markup(text, color=color, font_size='small'))

    def set_level(self, value: int, max_value: int) -> None:
        self._level_bar.set_value(value)
        self._level_bar.set_max_value(max_value)


def new_section(name: str, label_text: str) -> Section:
    frame = Gtk.Frame(label=label_text)
    frame.set_label_align(0.03, 0.5)
    frame.set_name(name)

    grid = Gtk.Grid()
    grid.set_name(name)
    grid.set_row_spacing(10)
    grid.set_column_spacing(10)
    grid.set_border_width(10)
    frame.add(grid)

    return Section(frame, grid)


def new_item(
        name: str,
        label_text: str,
        section: Section,
        children: Callable[..., Gtk.Widget],
        *grid_position: int
) -> Item:
    label = Gtk.Label(label_text)
    label.set_name(name)
    label.set_halign(Gtk.Align.START)
    section.grid.attach(label, *grid_position, 1, 1)

    children_widget = children()
    children_widget.set_hexpand(True)
    children_widget.set_name(name)
    section.grid.attach_next_to(children_widget, label, Gtk.PositionType.RIGHT, 1, 1)

    return Item(label, children_widget)


def markup(text: str, **kwargs: Any) -> str:
    markup_string = ['<span']

    for key, value in kwargs.items():
        markup_string.append(f'{key}="{value}"')

    markup_string.append(f'>{text}</span>')

    return ' '.join(markup_string)


def copy_childrens(from_model: Gtk.TreeStore, to_model: Gtk.ListStore, iter_: Gtk.TreeIter, column: int) -> None:
    childrens = from_model.iter_n_children(iter_)

    if childrens:
        for index in range(childrens):
            children_iter = from_model.iter_nth_child(iter_, index)
            value = from_model.get_value(children_iter, column)

            if value:
                to_model.append([value])
            else:
                log.debug(
                    _("Ignoring value from %s on column %s item %s because value is empty"),
                    children_iter,
                    column,
                    index
                )
    else:
        value = from_model.get_value(iter_, column)
        to_model.append([value])


def safe_confirmation_get(confirmation_: webapi.Confirmation, attribute: str) -> Tuple[str, List[str]]:
    value = getattr(confirmation_, attribute)

    if len(value) == 0:
        result = _("Nothing")
    elif len(value) == 1:
        result = value[0]
    else:
        result = _("Various")

    return result, value


def safe_callback(widget: Gtk.Widget, callback: Callable[..., Any], *data: List[Any]) -> None:
    widget.destroy()

    if asyncio.iscoroutinefunction(callback):
        asyncio.ensure_future(callback(*data))
    else:
        callback(*data)


def remove_letters(text: str) -> str:
    new_text = []

    for char in text:
        if char.isdigit():
            new_text.append(char)

    return ''.join(new_text)
