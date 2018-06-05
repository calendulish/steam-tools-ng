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
from typing import Any, Callable, Dict, NamedTuple

from gi.repository import Gtk

from .. import i18n

log = logging.getLogger(__name__)
_ = i18n.get_translation


class Section(NamedTuple):
    frame: Gtk.Frame
    grid: Gtk.Grid


class Item(NamedTuple):
    label: Gtk.Label
    children: Gtk.Widget


def new_section(label_text: str) -> Section:
    frame = Gtk.Frame(label=label_text)
    frame.set_label_align(0.03, 0.5)

    grid = Gtk.Grid()
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


def new_error(text: str) -> Gtk.Frame:
    frame = Gtk.Frame(label=_("Error"))
    frame.set_label_align(0.03, 0.5)

    error_label = Gtk.Label(text)
    error_label.set_justify(Gtk.Justification.CENTER)
    error_label.set_vexpand(True)
    error_label.set_margin_top(10)
    error_label.set_margin_bottom(10)

    frame.add(error_label)

    return frame


def markup(text: str, **kwargs: Any) -> str:
    markup_string = ['<span']

    for key, value in kwargs.items():
        markup_string.append(f'{key}="{value}"')

    markup_string.append(f'>{text}</span>')

    return ' '.join(markup_string)


def get_column_len(model, iter_, column) -> int:
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


def match_column_childrens(model: Gtk.TreeModel, iter_: Gtk.TreeIter, item, column) -> None:
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
