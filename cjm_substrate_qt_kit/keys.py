"""The keybinding helper both shells grew independently — plus the shell's
keyboard contract (ruling 2bae2cc1): the numpad Enter key binds wherever
Return binds, so a Return verb answers both keys by construction (user
defect: Ctrl+Return in the scratchpad ignored the numpad Enter)."""

from typing import List

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut


def enter_twins(key: str) -> List[str]:
    """A key and its numpad twin: "Return" -> ["Return", "Enter"],
    "Ctrl+Return" -> ["Ctrl+Return", "Ctrl+Enter"]; any other key stands
    alone. Every binding path (KeymapRegistry.add, bind) goes through here."""
    toks = str(key).split("+")
    if toks and toks[-1] == "Return":
        return [key, "+".join(toks[:-1] + ["Enter"])]
    return [key]


def bind(owner, key: str, fn, parent=None, context=Qt.WindowShortcut) -> QShortcut:
    """One QShortcut: `key` on `parent` (default: the owner window) fires `fn`.

    Returns the shortcut so callers can retune context/enabled later; the
    default WindowShortcut context pairs with modal dialogs for text entry
    (single-letter bindings never fight a focused editor). A Return binding
    mints its numpad twin beside it (reachable as `.twin`)."""
    shortcut = None
    for k in enter_twins(key):
        s = QShortcut(QKeySequence(k), parent or owner)
        s.setContext(context)
        s.activated.connect(fn)
        if shortcut is None:
            shortcut = s
        else:
            shortcut.twin = s
    return shortcut
