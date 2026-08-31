"""PickerList contract (work item 8d29f0f0): the pickable mapping skips
header/note rows, the cursor clamps and follows with ensure-visible,
click-to-cursor lands only on item rows (a header click restores the
selection), double-click activates through the cursor, set_rows positions
silently, and the detail pane hides when empty and caps at its budget."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from cjm_substrate_qt_kit.pickerlist import PickerList, spans_to_html
from cjm_substrate_qt_kit.theme import current_theme, state_color


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def rows():
    return [
        {"kind": "header", "spans": [("COLLECTION", "bold")]},
        {"kind": "item", "spans": [("  alpha", "")], "key": "a"},
        {"kind": "item", "spans": [("  beta  ", ""), ("2 marks", "yellow")],
         "key": "b"},
        {"kind": "note", "spans": [("  (a note)", "dim")]},
        {"kind": "item", "spans": [("  gamma <x>", "")], "key": "c"},
    ]


def test_spans_to_html_escapes_and_routes_theme_colors(app):
    t = current_theme()
    html = spans_to_html([("a <b> chip", "yellow bold"), ("plain", "")], t)
    assert "a &lt;b&gt; chip" in html
    assert state_color("yellow", t).name() in html
    assert "font-weight:bold" in html
    assert "white-space:pre" in html
    assert spans_to_html([], t).count("&nbsp;") == 1   # blank separator row


def test_pickable_mapping_and_cursor_clamp(app):
    moves = []
    p = PickerList(on_cursor=moves.append)
    p.set_rows(rows(), cursor=0)
    assert p.count() == 3
    assert p.current_key() == "a"
    p.move(1)
    p.move(1)
    assert p.current_key() == "c"
    p.move(5)                       # clamps at the last pickable row
    assert p.current_key() == "c"
    p.move(-99)
    assert p.current_key() == "a"
    assert moves == [1, 2, 0]       # only actual changes fire


def test_click_to_cursor_and_header_restore(app):
    moves = []
    p = PickerList(on_cursor=moves.append)
    p.set_rows(rows(), cursor=0)
    p._on_pressed(p.view.item(2))   # the "beta" row (pickable index 1)
    assert p.cursor == 1 and moves == [1]
    p._on_pressed(p.view.item(0))   # header click: cursor stays, selection restored
    assert p.cursor == 1 and moves == [1]
    assert p.view.currentRow() == 2


def test_double_click_and_activate_hand_over_the_key(app):
    picked = []
    p = PickerList(on_activate=picked.append)
    p.set_rows(rows(), cursor=0)
    p._on_double(p.view.item(4))    # the "gamma" row
    assert picked == ["c"]
    p.activate()                    # the window enter key's route
    assert picked == ["c", "c"]


def test_set_rows_positions_silently_and_reclamps(app):
    moves = []
    p = PickerList(on_cursor=moves.append)
    p.set_rows(rows(), cursor=2)
    assert p.cursor == 2 and moves == []
    p.set_rows(rows()[:2], cursor=2)   # only one pickable row remains
    assert p.cursor == 0 and p.current_key() == "a"
    assert moves == []


def test_detail_pane_hides_empty_and_caps_at_budget(app):
    p = PickerList(detail_budget_rows=2)
    p.set_rows(rows(), cursor=0)
    assert not p.detail.isVisibleTo(p)
    p.set_detail([[("one line", "dim")]])
    assert p.detail.isVisibleTo(p)
    one_line_h = p.detail.height()
    p.set_detail([[("l%d" % i, "")] for i in range(30)])
    assert p.detail.height() <= one_line_h * 4   # capped, not 30 rows tall
    p.set_detail(None)
    assert not p.detail.isVisibleTo(p)
