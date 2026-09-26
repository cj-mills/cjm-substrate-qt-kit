"""Row-style vocabulary for the lane's list widgets.

Spine row dicts carry style words — state roles ("ok", "dim", "bold", …) or,
until the spines migrate (06d729ab), the legacy Rich words ("green"); the
shells map them onto QListWidgetItems. Colors resolve through the live theme
(word -> state role -> var; see theme.state_color) — the pre-theme
STYLE_COLORS hex map retired with the kit charter (ruling 8b7351e4)."""

from typing import Optional

from cjm_substrate_qt_kit.theme import state_color
from PySide6.QtWidgets import QListWidgetItem


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
