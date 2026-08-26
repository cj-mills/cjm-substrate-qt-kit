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
from PySide6.QtWidgets import QApplication, QLineEdit, QPlainTextEdit, QTextEdit


class KeymapRegistry:
    """Declarative verb table -> live QActions on an owner widget."""

    def __init__(self, owner):
        self.owner = owner
        self._actions: Dict[str, QAction] = {}
        self._meta: Dict[str, dict] = {}

    def add(self, verb: str, label: str, key: str, fn: Callable[[], None],
            context: Qt.ShortcutContext = Qt.ShortcutContext.WindowShortcut,
            group: str = "") -> QAction:
        """Register one verb: a labelled QAction with its default binding,
        added to the owner so the shortcut fires window-wide. group names
        the verb's section in discovery surfaces (the keyhints overlay)."""
        action = QAction(label, self.owner)
        if key:
            action.setShortcut(QKeySequence(key))
        action.setShortcutContext(context)
        action.triggered.connect(lambda _checked=False: fn())
        self.owner.addAction(action)
        self._actions[verb] = action
        self._meta[verb] = {"verb": verb, "label": label, "key": key,
                            "group": group}
        return action

    def action(self, verb: str) -> QAction:
        return self._actions[verb]

    def rebind(self, verb: str, key: str) -> None:
        """Retune a verb's binding in place (the future keybinding UI's verb)."""
        self._actions[verb].setShortcut(QKeySequence(key))
        self._meta[verb]["key"] = key

    def entries(self) -> List[dict]:
        """The discovery surface: [{verb, label, key, group}] in declaration
        order — menus, the keyhints overlay, and the future remapping UI all
        read from here."""
        return [dict(m) for m in self._meta.values()]

    def guard_text_entry(self) -> None:
        """Gate character-producing verbs off while focus sits in a text-entry
        widget (adoption rung caa33c98: a bare-letter window shortcut would
        otherwise swallow that letter typed into e.g. the FindBar field).

        A verb is guarded when its key would land in the field: a bare or
        Shift-only single character ("B", "/", "Shift+S" — Shift alone still
        types), plus Escape/Return (the field and e.g. the FindBar consume
        those themselves). Chords (Ctrl/Alt/Meta) and function keys (F3) stay
        live — find-next while typing a pattern is the point. Editable
        QLineEdit/QTextEdit/QPlainTextEdit count as text entry; read-only
        panes do not."""
        app = QApplication.instance()
        if app is None:
            return

        def _guarded(key: str) -> bool:
            toks = str(key).split("+")
            if any(t in ("Ctrl", "Alt", "Meta") for t in toks):
                return False
            return len(toks[-1]) == 1 or toks[-1] in ("Escape", "Return", "Enter")

        guarded = [self._actions[v] for v, m in self._meta.items()
                   if m["key"] and _guarded(str(m["key"]))]

        def on_focus(_old, new) -> None:
            entry = (isinstance(new, (QLineEdit, QPlainTextEdit, QTextEdit))
                     and not new.isReadOnly())
            for action in guarded:
                action.setEnabled(not entry)

        app.focusChanged.connect(on_focus)

        def _detach(*_a) -> None:
            # The app-level connection must not outlive the owner: firing on a
            # torn-down window's QActions raises on deleted C++ objects.
            try:
                app.focusChanged.disconnect(on_focus)
            except RuntimeError:
                pass

        self.owner.destroyed.connect(_detach)
