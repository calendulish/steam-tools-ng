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

import logging
from typing import Any, Callable, Dict, List, NamedTuple, Tuple

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


class Status(Gtk.Frame):
    def __init__(self):
        super().__init__()
        self.connect('draw', self.__do_status_draw)

        self._grid = Gtk.Grid()
        self._grid.set_border_width(10)
        self.add(self._grid)

        self._label = Gtk.Label()
        self._grid.attach(self._label, 0, 0, 1, 1)

        self.info(_("Waiting"))

    @staticmethod
    def __do_status_draw(frame: Gtk.Frame, cairo_context: cairo.Context):
        allocation = frame.get_allocation()
        cairo_context.set_source_rgb(0.2, 0.2, 0.2)
        cairo_context.rectangle(0, 0, allocation.width, allocation.height)
        cairo_context.fill()

    def error(self, text) -> None:
        self._label.set_markup(markup(text, color='hotpink', face='monospace'))

    def info(self, text) -> None:
        self._label.set_markup(markup(text, color='cyan', face='monospace'))


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


def get_column_len(model: Gtk.TreeModel, iter_: Gtk.TreeIter, column: int) -> int:
    childrens = model.iter_n_children(iter_)
    column_len = 0

    for index in range(childrens):
        column_iter = model.iter_nth_child(iter_, index)

        if model.get_value(column_iter, column):
            column_len += 1
        else:
            log.debug(_("Ignoring value from column %s because value is empty"), index)

    return column_len


def match_rows(model: Gtk.TreeModel, item: Dict[str, Any]) -> None:
    total = len(item)
    exclusions = len(model) - total

    if exclusions > 0:
        for index in range(exclusions):
            exclusion_iter = model.get_iter(total + index)
            model.remove(exclusion_iter)


def match_column_childrens(model: Gtk.TreeModel, iter_: Gtk.TreeIter, item: List[str], column: int) -> None:
    total = len(item)
    exclusions = get_column_len(model, iter_, column) - total

    if exclusions > 0:
        for index in range(exclusions):
            exclusion_iter = model.iter_nth_child(iter_, total + index)

            if None in [
                model.get_value(exclusion_iter, 3),
                model.get_value(exclusion_iter, 5),
            ]:
                model.remove(exclusion_iter)
                total -= 1
            else:
                model.set_value(exclusion_iter, column, '')


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
