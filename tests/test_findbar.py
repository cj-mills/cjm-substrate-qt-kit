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


def test_match_case_option_narrows(app):
    pane, bar = make(app)
    pane.setPlainText("Beta beta BETA")
    bar.field.setText("beta")
    assert bar.count.text() == "1/3"       # case-insensitive default
    bar.case_btn.setChecked(True)
    assert bar.count.text() == "1/1"       # exact-case only

def test_whole_word_option_excludes_substrings(app):
    pane, bar = make(app)
    pane.setPlainText("beta betamax beta")
    bar.field.setText("beta")
    assert bar.count.text() == "1/3"
    bar.word_btn.setChecked(True)
    assert bar.count.text() == "1/2"       # betamax drops out


def test_regex_option_and_invalid_pattern(app):
    pane, bar = make(app)
    pane.setPlainText("cat cot cut")
    bar.regex_btn.setChecked(True)
    bar.field.setText("c[ao]t")
    assert bar.count.text() == "1/2"
    bar.field.setText("c[")                # invalid — flagged, never raises
    assert bar.count.text() == "regex?"
    assert pane.extraSelections() == []


def test_literal_default_escapes_regex_metacharacters(app):
    pane, bar = make(app)
    pane.setPlainText("a.c abc")
    bar.field.setText("a.c")
    assert bar.count.text() == "1/1"       # literal dot, not any-char


def test_focused_match_paints_distinct(app):
    pane, bar = make(app)
    bar.field.setText("beta")
    selections = pane.extraSelections()
    focused = [s for s in selections
               if s.format.background().color().alpha() > 100]
    assert len(focused) == 1               # exactly one strong block — the current hit
    assert focused[0].cursor.selectionStart() == pane.textCursor().selectionStart()


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
