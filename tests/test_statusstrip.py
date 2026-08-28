"""StatusStrip contract: the three message classes keep their lifetimes —
chips never evicted, readout persists until superseded, transient expires
on its own timer — and the hint line rides row two."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from cjm_substrate_qt_kit.statusstrip import StatusStrip


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_chips_create_update_remove_keep_order(app):
    strip = StatusStrip()
    strip.set_chip("source", "chris-wright")
    strip.set_chip("segment", "2272/2273")
    strip.set_chip("source", "learning-game")  # update, not duplicate
    assert list(strip._chips) == ["source", "segment"]
    assert strip._chips["source"].text() == "learning-game"
    strip.remove_chip("segment")
    assert list(strip._chips) == ["source"]


def test_readout_persists_until_superseded(app):
    strip = StatusStrip()
    strip.set_readout("▶ 3794.98s · span 3792.97–3795.75s")
    strip.show_transient("saved", msecs=60000)
    strip._expire()
    assert strip.readout.text() == "▶ 3794.98s · span 3792.97–3795.75s"
    strip.set_readout("▶ 12.1s · span 10.0–12.0s")
    assert "3794" not in strip.readout.text()
    strip.clear_readout()
    assert strip.readout.text() == ""


def test_transient_expires_and_touches_nothing_else(app):
    strip = StatusStrip()
    strip.set_chip("gate", "✔3796.8s")
    strip.set_readout("readout")
    strip.show_transient("launched decomp (pid 4242)", msecs=60000)
    assert strip.transient.text() == "launched decomp (pid 4242)"
    assert strip._timer.isActive()
    strip._expire()
    assert strip.transient.text() == ""
    assert strip._chips["gate"].text() == "✔3796.8s"
    assert strip.readout.text() == "readout"


def test_role_lands_and_changes(app):
    strip = StatusStrip()
    strip.set_readout("stalled", role="warn")
    assert strip.readout.property("role") == "warn"
    strip.set_readout("ok again")
    assert strip.readout.property("role") == ""


def test_hint_line_row_and_hints_false(app):
    strip = StatusStrip()
    strip.set_hints("J next · R replay · ? keys")
    assert strip.hints.text() == "J next · R replay · ? keys"
    bare = StatusStrip(hints=False)
    assert bare.hints is None
    bare.set_hints("ignored")  # no-op, no crash


def test_context_slot_wordwraps_and_hides_when_empty(app):
    strip = StatusStrip()
    assert strip.context.isHidden()          # empty = no row at all
    assert strip.context.wordWrap()          # full-width, variable-length data
    strip.set_readout("readout")
    strip.set_context("mark: class-or-# · 1:suspect 2:unclear 3:overlap")
    assert not strip.context.isHidden()
    assert strip.readout.text() == "readout"  # context never rides the readout
    strip.clear_context()
    assert strip.context.isHidden()


def test_readout_reflows_to_own_row_when_crowded(app):
    strip = StatusStrip()
    strip.resize(1200, 60)
    strip.set_chip("lane", "[WALK]")
    strip.set_readout("■ played 7799.50–7802.67s")
    strip._reflow()
    assert strip._readout_inline          # plenty of room: shares the row
    strip.resize(300, 60)
    strip.set_chips([("lane", "[ASSIGN]"), ("source", "How I use LLMs"),
                     ("segment", "segment 4765/4806"), ("gate", "✔7871.2s")])
    strip._reflow()
    assert not strip._readout_inline      # crowded: own full-width row
    assert strip.readout.wordWrap()       # nothing truncated down there
    strip.resize(1600, 60)
    strip._reflow()
    assert strip._readout_inline          # space back: inline again
    assert not strip.readout.wordWrap()


def test_labels_select_by_mouse_without_taking_focus(app):
    """Selectable text (walkthrough call-out 04519af8): every strip label
    selects by mouse drag so identifiers copy out of the footer — and none
    of them takes keyboard focus (the flags alone would grant ClickFocus
    and put a label between the owner window and its key table)."""
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    strip = StatusStrip()
    strip.resize(800, 60)
    strip.set_chip("session", "session abcdef12")
    strip.set_readout("■ played 7799.50–7802.67s")
    strip.show()
    chip = strip._chips["session"]
    for label in (chip, strip.readout, strip.transient, strip.context,
                  strip.hints):
        assert label.textInteractionFlags() & Qt.TextSelectableByMouse
        assert label.focusPolicy() == Qt.NoFocus
    QTest.mousePress(chip, Qt.LeftButton, Qt.NoModifier, QPoint(1, 6))
    QTest.mouseMove(chip, QPoint(chip.width() - 2, 6))
    QTest.mouseRelease(chip, Qt.LeftButton, Qt.NoModifier,
                       QPoint(chip.width() - 2, 6))
    assert chip.hasSelectedText()
    assert "session" in chip.selectedText()
    strip.close()


def test_long_plain_chip_elides_with_full_text_in_tooltip(app):
    """Footer minimum-width, move (a) (call-out e26add76): a plain-text chip
    wider than chip_max_width elides right, the full text rides the
    tooltip + chip_text, a short chip is untouched, and a RICH-TEXT chip
    (the apps' colored spans) is never cut."""
    title = ("2026-05-23_How we're going to power the AI data center "
             "buildout Energy Sec. Chris Wright & Scott Nolan")
    strip = StatusStrip(chip_max_width=200)
    strip.set_chip("source", title)
    chip = strip._chips["source"]
    assert chip.text() != title and chip.text().endswith("…")
    assert chip.sizeHint().width() <= 200 + 4
    assert chip.toolTip() == title
    assert strip.chip_text("source") == title
    strip.set_chip("source", "How I use LLMs")
    assert chip.text() == "How I use LLMs" and chip.toolTip() == ""
    rich = "<span style='color:#3f9d55'> journal→cjm-capability-graph-sqlite-with-a-very-long-name </span>"
    strip.set_chip("journal", rich)
    assert strip._chips["journal"].text() == rich
    assert StatusStrip(chip_max_width=0)._elide(chip, title) == title


def test_chip_row_flows_and_minimum_is_the_widest_chip(app):
    """Footer minimum-width, move (b) (call-out e26add76): chips that no
    longer fit the row flow onto rows underneath in declaration order and
    return to one row when space allows; the strip's minimum width is its
    widest chip, not the row's sum — so the window can narrow at all."""
    strip = StatusStrip()
    chips = [("lane", "[PROPOSE]"), ("source", "How I use LLMs"),
             ("segment", "segment 4765/4806"),
             ("proposals", "proposals 12 pending · tier2 40 hidden"),
             ("set", "set 1a2b3c4d"), ("model", "model 9f8e7d6c")]
    strip.resize(1400, 60)
    strip.set_chips(chips)
    assert strip.chip_rows() == [[n for n, _ in chips]]   # one row, in order
    row_sum = sum(c.sizeHint().width() for c in strip._chips.values())
    widest = max(c.sizeHint().width() for c in strip._chips.values())
    assert strip.minimumSizeHint().width() <= widest + 12 < row_sum
    strip.resize(320, 60)
    strip._reflow()
    rows = strip.chip_rows()
    assert len(rows) > 1
    assert [n for r in rows for n in r] == [n for n, _ in chips]   # order kept
    avail = 320 - 12
    for names in rows:
        width = sum(strip._chips[n].sizeHint().width() for n in names)
        width += 12 * (len(names) - 1)
        assert width <= avail or len(names) == 1
    extra = strip._chip_rows[1]
    assert extra.count() == len(rows[1]) + 1        # chips + trailing stretch
    assert extra.itemAt(extra.count() - 1).spacerItem() is not None
    strip.remove_chip("proposals")
    assert "proposals" not in [n for r in strip.chip_rows() for n in r]
    strip.resize(1400, 60)
    strip._reflow()
    assert len(strip.chip_rows()) == 1
    assert all(r.count() == 1 for r in strip._chip_rows[1:])   # stretch only
