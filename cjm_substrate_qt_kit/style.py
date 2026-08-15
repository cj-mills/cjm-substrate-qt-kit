"""Row-style vocabulary for the lane's list widgets.

Spine row dicts carry Rich-ish style words ("green", "dim", "bold", …); the
shells map them onto QListWidgetItems. Theme-neutral hexes readable on light
and dark — the same palette both shells shipped with before extraction."""

from typing import Optional

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QListWidgetItem

STYLE_COLORS = {"red": "#c74a3c", "yellow": "#b9770e", "cyan": "#2b8a9d",
                "magenta": "#9b59b6", "green": "#3f9d55", "blue": "#4a6fb5",
                "dim": "#8a9299"}


def apply_row_style(item: QListWidgetItem, style: Optional[str]) -> None:
    """Map a row's style words onto a list item (color words + bold)."""
    parts = str(style or "").split()
    for word in parts:
        if word in STYLE_COLORS:
            item.setForeground(QColor(STYLE_COLORS[word]))
    if "bold" in parts:
        font = item.font()
        font.setBold(True)
        item.setFont(font)
