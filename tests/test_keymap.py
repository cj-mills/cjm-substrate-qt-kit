"""KeymapRegistry contract: labelled live QActions, declaration-order
discovery surface, runtime rebind."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication, QMainWindow

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
    keymap.add("find", "Find in file", "Ctrl+F", lambda: None)
    keymap.add("save", "Save now", "Ctrl+S", lambda: None)
    assert keymap.entries() == [
        {"verb": "find", "label": "Find in file", "key": "Ctrl+F"},
        {"verb": "save", "label": "Save now", "key": "Ctrl+S"},
    ]


def test_rebind_retunes_action_and_surface(app):
    window = QMainWindow()
    keymap = KeymapRegistry(window)
    keymap.add("find", "Find in file", "Ctrl+F", lambda: None)
    keymap.rebind("find", "Ctrl+Shift+F")
    assert keymap.action("find").shortcut() == QKeySequence("Ctrl+Shift+F")
    assert keymap.entries()[0]["key"] == "Ctrl+Shift+F"
