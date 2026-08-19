"""Row-style vocabulary for the lane's list widgets.

Spine row dicts carry Rich-ish style words ("green", "dim", "bold", …); the
shells map them onto QListWidgetItems. Colors resolve through the live theme
(word -> semantic role -> token; see theme.WORD_ROLES); STYLE_COLORS keeps
the pre-theme neutral hexes only as a legacy export."""

from typing import Optional

from cjm_substrate_qt_kit.theme import state_color
from PySide6.QtWidgets import QListWidgetItem

STYLE_COLORS = {"red": "#c74a3c", "yellow": "#b9770e", "cyan": "#2b8a9d",
                "magenta": "#9b59b6", "green": "#3f9d55", "blue": "#4a6fb5",
                "dim": "#8a9299"}


def apply_row_style(item: QListWidgetItem, style: Optional[str]) -> None:
    """Map a row's style words onto a list item (color words + bold)."""
    parts = str(style or "").split()
    for word in parts:
        color = state_color(word)
        if color is not None:
            item.setForeground(color)
    if "bold" in parts:
        font = item.font()
        font.setBold(True)
        item.setFont(font)
