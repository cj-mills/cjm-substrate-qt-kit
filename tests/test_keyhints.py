"""Keyhints contract: grouped model, responsive columns, pin round-trip,
hint-line projection, registry group flow-through."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication, QWidget

from cjm_substrate_qt_kit.keyhints import (KeyHintsOverlay, column_count,
                                           group_entries, hint_line,
                                           render_hints_html)
from cjm_substrate_qt_kit.keymap import KeymapRegistry

ENTRIES = [
    {"verb": "walk.next", "label": "next segment", "key": "J", "group": "Walk"},
    {"verb": "walk.prev", "label": "previous segment", "key": "K", "group": "Walk"},
    {"verb": "audio.replay", "label": "replay", "key": "R", "group": "Audio"},
    {"verb": "app.quit", "label": "quit", "key": "Q", "group": ""},
]


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_group_entries_first_seen_order_and_general_default():
    sections = group_entries(ENTRIES)
    assert [name for name, _ in sections] == ["Walk", "Audio", "General"]
    assert [e["verb"] for e in sections[0][1]] == ["walk.next", "walk.prev"]


def test_hint_line_projects_pins_in_order_and_skips_stale():
    line = hint_line(ENTRIES, ["audio.replay", "gone.verb", "walk.next"])
    assert line == "R replay · J next segment · ? keys"


def test_hint_line_empty_pins_still_names_the_overlay():
    assert hint_line(ENTRIES, []) == "? keys"


def test_column_count_width_affordance_and_section_cap():
    assert column_count(300, 5) == 1
    assert column_count(800, 5) == 2
    assert column_count(1400, 5) == 3
    assert column_count(1400, 2) == 2  # content cap
    assert column_count(3000, 9) == 3  # hard cap


def test_render_html_sections_keycaps_and_pin_glyphs():
    html = render_hints_html(ENTRIES, ["walk.next"], columns=2)
    assert "Walk" in html and "Audio" in html and "General" in html
    assert "pin:walk.next" in html and "pin:app.quit" in html
    assert "&#9679;" in html and "&#9675;" in html  # pinned + unpinned glyphs
    chord = render_hints_html(
        [{"verb": "v", "label": "chord", "key": "Ctrl+Shift+K", "group": "G"}],
        [], columns=1)
    assert chord.count("&nbsp;Ctrl&nbsp;") == 1 and "&nbsp;K&nbsp;" in chord


def test_overlay_toggle_and_pin_callback(app):
    owner = QWidget()
    owner.resize(1000, 800)
    seen = []
    overlay = KeyHintsOverlay(owner, ENTRIES, pins=["walk.next"],
                              on_pins_changed=seen.append)
    overlay.toggle()
    assert overlay.isVisible()
    overlay._on_anchor(QUrl("pin:audio.replay"))
    assert seen == [["walk.next", "audio.replay"]]
    overlay._on_anchor(QUrl("pin:walk.next"))
    assert seen[-1] == ["audio.replay"]
    overlay.toggle()
    assert not overlay.isVisible()


def test_registry_group_flows_to_entries(app):
    owner = QWidget()
    reg = KeymapRegistry(owner)
    reg.add("walk.next", "next", "J", lambda: None, group="Walk")
    reg.add("app.quit", "quit", "Q", lambda: None)
    entries = reg.entries()
    assert entries[0]["group"] == "Walk"
    assert entries[1]["group"] == ""
    sections = group_entries(entries)
    assert [name for name, _ in sections] == ["Walk", "General"]


def test_overlay_sizes_to_rendered_content(app):
    owner = QWidget()
    owner.resize(1000, 800)
    overlay = KeyHintsOverlay(owner, ENTRIES[:2])  # one small section
    overlay.open_overlay()
    # fixed column-width sizing left the panel mostly empty (drive verdict
    # 2026-08-25): the dialog now hugs the rendered document
    assert overlay.width() < 400
    assert overlay.height() < 450
    html = overlay.view.toHtml()
    overlay.close()
    assert "hints" in html.lower()
