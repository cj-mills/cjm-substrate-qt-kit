"""FindBar contract: incremental search from the opening origin, wrap-around
stepping in both directions, match paint + counter, close returns focus."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QPlainTextEdit

from cjm_substrate_qt_kit.findbar import FindBar

TEXT = "alpha beta\ngamma beta\ndelta beta end"


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def make(app):
    pane = QPlainTextEdit()
    pane.setPlainText(TEXT)
    bar = FindBar(pane)
    bar.open()
    return pane, bar


def test_typing_finds_first_match_from_origin_and_counts(app):
    pane, bar = make(app)
    bar.field.setText("beta")
    assert pane.textCursor().selectedText() == "beta"
    assert pane.textCursor().selectionStart() == TEXT.index("beta")
    assert bar.count.text() == "1/3"
    assert len(pane.extraSelections()) == 3


def test_next_steps_and_wraps(app):
    pane, bar = make(app)
    bar.field.setText("beta")
    bar.next()
    assert bar.count.text() == "2/3"
    bar.next()
    assert bar.count.text() == "3/3"
    bar.next()  # wraps back to the first match
    assert bar.count.text() == "1/3"


def test_previous_wraps_backward(app):
    pane, bar = make(app)
    bar.field.setText("beta")
    bar.previous()  # from match 1, backward wraps to the last
    assert bar.count.text() == "3/3"


def test_no_match_paints_nothing(app):
    pane, bar = make(app)
    bar.field.setText("zzz")
    assert bar.count.text() == "0/0"
    assert pane.extraSelections() == []


def test_close_clears_paint_and_hides(app):
    pane, bar = make(app)
    bar.field.setText("beta")
    bar.close_bar()
    assert bar.isHidden()
    assert pane.extraSelections() == []


def test_open_seeds_pattern_from_selection(app):
    pane = QPlainTextEdit()
    pane.setPlainText(TEXT)
    cursor = pane.textCursor()
    cursor.setPosition(TEXT.index("gamma"))
    cursor.movePosition(cursor.MoveOperation.EndOfWord, cursor.MoveMode.KeepAnchor)
    pane.setTextCursor(cursor)
    bar = FindBar(pane)
    bar.open()
    assert bar.field.text() == "gamma"
