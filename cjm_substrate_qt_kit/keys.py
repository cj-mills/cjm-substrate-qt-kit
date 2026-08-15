"""The keybinding helper both shells grew independently."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut


def bind(owner, key: str, fn, parent=None, context=Qt.WindowShortcut) -> QShortcut:
    """One QShortcut: `key` on `parent` (default: the owner window) fires `fn`.

    Returns the shortcut so callers can retune context/enabled later; the
    default WindowShortcut context pairs with modal dialogs for text entry
    (single-letter bindings never fight a focused editor)."""
    shortcut = QShortcut(QKeySequence(key), parent or owner)
    shortcut.setContext(context)
    shortcut.activated.connect(fn)
    return shortcut
