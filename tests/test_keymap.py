"""KeymapRegistry contract: labelled live QActions, declaration-order
discovery surface, runtime rebind."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication, QLineEdit, QMainWindow

from cjm_substrate_qt_kit.keymap import KeymapRegistry


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_add_mints_live_labelled_action(app):
    window = QMainWindow()
    keymap = KeymapRegistry(window)
    fired = []
    action = keymap.add("toggle-view", "Toggle edit/rendered view", "Ctrl+/",
                        lambda: fired.append(True))
    assert action in window.actions()
    assert action.text() == "Toggle edit/rendered view"
    assert action.shortcut() == QKeySequence("Ctrl+/")
    action.trigger()
    assert fired == [True]


def test_entries_is_the_discovery_surface(app):
    window = QMainWindow()
    keymap = KeymapRegistry(window)
    keymap.add("find", "Find in file", "Ctrl+F", lambda: None, group="File")
    keymap.add("save", "Save now", "Ctrl+S", lambda: None)
    assert keymap.entries() == [
        {"verb": "find", "label": "Find in file", "key": "Ctrl+F",
         "group": "File"},
        {"verb": "save", "label": "Save now", "key": "Ctrl+S", "group": ""},
    ]


def test_rebind_retunes_action_and_surface(app):
    window = QMainWindow()
    keymap = KeymapRegistry(window)
    keymap.add("find", "Find in file", "Ctrl+F", lambda: None)
    keymap.rebind("find", "Ctrl+Shift+F")
    assert keymap.action("find").shortcut() == QKeySequence("Ctrl+Shift+F")
    assert keymap.entries()[0]["key"] == "Ctrl+Shift+F"


def test_guard_text_entry_gates_character_verbs(app):
    # Adoption-rung guard (caa33c98): while focus sits in an editable text
    # field, bare/Shift-only character verbs and Escape/Return go quiet so
    # typing works; chords and function keys (find-next!) stay live.
    win = QMainWindow()
    km = KeymapRegistry(win)
    letter = km.add("back", "Back", "B", lambda: None)
    shifted = km.add("mint", "Mint", "Shift+S", lambda: None)
    esc = km.add("esc", "Escape back", "Escape", lambda: None)
    chord = km.add("find", "Find", "Ctrl+F", lambda: None)
    fkey = km.add("next", "Find next", "F3", lambda: None)
    km.guard_text_entry()
    app_ = QApplication.instance()
    field = QLineEdit()
    app_.focusChanged.emit(None, field)
    assert not letter.isEnabled() and not shifted.isEnabled() and not esc.isEnabled()
    assert chord.isEnabled() and fkey.isEnabled()
    readonly = QLineEdit()
    readonly.setReadOnly(True)
    app_.focusChanged.emit(field, readonly)
    assert letter.isEnabled() and shifted.isEnabled() and esc.isEnabled()
    del win  # owner teardown must detach the app-level connection…
    app_.focusChanged.emit(None, field)  # …so this cannot touch deleted actions
