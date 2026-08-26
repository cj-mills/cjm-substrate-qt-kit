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
