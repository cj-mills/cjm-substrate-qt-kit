"""KeymapRegistry: the QAction layer from the toolbox verdict (DEC d55f1d0f).

Apps declare verbs — id, label, default key, handler — and the registry
mints labelled QActions on the owner window so the shortcuts are live
app-wide. The declarative table IS the discovery surface: entries()
enumerates every gesture (for menus and the future auto-generated
keybinding/config UI), and rebind() retunes a verb at runtime without
touching its handler."""

from typing import Callable, Dict, List

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence


class KeymapRegistry:
    """Declarative verb table -> live QActions on an owner widget."""

    def __init__(self, owner):
        self.owner = owner
        self._actions: Dict[str, QAction] = {}
        self._meta: Dict[str, dict] = {}

    def add(self, verb: str, label: str, key: str, fn: Callable[[], None],
            context: Qt.ShortcutContext = Qt.ShortcutContext.WindowShortcut) -> QAction:
        """Register one verb: a labelled QAction with its default binding,
        added to the owner so the shortcut fires window-wide."""
        action = QAction(label, self.owner)
        if key:
            action.setShortcut(QKeySequence(key))
        action.setShortcutContext(context)
        action.triggered.connect(lambda _checked=False: fn())
        self.owner.addAction(action)
        self._actions[verb] = action
        self._meta[verb] = {"verb": verb, "label": label, "key": key}
        return action

    def action(self, verb: str) -> QAction:
        return self._actions[verb]

    def rebind(self, verb: str, key: str) -> None:
        """Retune a verb's binding in place (the future keybinding UI's verb)."""
        self._actions[verb].setShortcut(QKeySequence(key))
        self._meta[verb]["key"] = key

    def entries(self) -> List[dict]:
        """The discovery surface: [{verb, label, key}] in declaration order."""
        return [dict(m) for m in self._meta.values()]
