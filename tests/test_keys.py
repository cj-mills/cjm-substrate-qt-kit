"""The keyboard contract (ruling 2bae2cc1): the numpad Enter key binds
wherever Return binds — through the registry and through bind()."""

from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QWidget

from cjm_substrate_qt_kit.keymap import KeymapRegistry
from cjm_substrate_qt_kit.keys import bind, enter_twins


def test_enter_twins_only_for_return_bindings():
    assert enter_twins("Return") == ["Return", "Enter"]
    assert enter_twins("Ctrl+Return") == ["Ctrl+Return", "Ctrl+Enter"]
    assert enter_twins("Shift+S") == ["Shift+S"]
    assert enter_twins("F3") == ["F3"]


def test_registry_return_verb_answers_numpad_enter(app):
    owner = QWidget()
    reg = KeymapRegistry(owner)
    reg.add("open", "Open", "Ctrl+Return", lambda: None, group="Rows")
    keys = [s.toString() for s in reg.action("open").shortcuts()]
    assert keys == ["Ctrl+Return", "Ctrl+Enter"]
    assert reg.entries()[0]["key"] == "Ctrl+Return"      # the surface shows the declared key
    reg.rebind("open", "Return")
    assert [s.toString() for s in reg.action("open").shortcuts()] == ["Return", "Enter"]
    reg.add("quit", "Quit", "Q", lambda: None)
    assert [s.toString() for s in reg.action("quit").shortcuts()] == ["Q"]
    assert reg.groups() == ["Rows", ""]


def test_bind_mints_the_numpad_twin(app):
    owner = QWidget()
    fired = []
    s = bind(owner, "Return", lambda: fired.append(1))
    assert s.key() == QKeySequence("Return")
    assert s.twin.key() == QKeySequence("Enter")
    plain = bind(owner, "J", lambda: None)
    assert not hasattr(plain, "twin")
