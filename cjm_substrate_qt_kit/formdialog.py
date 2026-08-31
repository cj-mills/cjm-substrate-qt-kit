"""Kit FormShell (work item d55292f9): the frameless modal FORM chrome —
a FIXED header (modal_header: title left, mouse close right) and a FIXED
footer (rich-text hints) around a scrollable clickable-row body, plus the
transient QLineEdit editor row.

The defect this retires (user walkthrough 2026-08-27): the finetune form
was one NoFocus QTextBrowser — its header and keyboard-hints footer lived
INSIDE the scrolled document (the hints vanished near the top of a long
form), rows were plain text (no mouse selection of a config slot), and
keyboard row moves never scrolled the view. Here the body is a kit
PickerList, so rows are native: click-to-cursor, double-click activation,
ensure-visible keyboard follow, wheel/scrollbar scrolling — and the chrome
never scrolls away. The focused row's description belongs in the body's
detail pane (always visible, under the rows, above the footer).

Division of labor: the shell owns chrome, sizing (the keyhints recipe:
size to the rendered rows, capped by the owner), the esc ladder (an open
editor closes first — a modal IS a step), and the header's close anchor.
The SUBCLASS owns keys (the dialog has focus — a focused QListWidget would
keyboard-search on letter presses) and what rows/cursor/activation mean."""

from typing import Any, Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QLineEdit, QTextBrowser, QVBoxLayout

from .keyhints import is_close_anchor, modal_header
from .pickerlist import PickerList
from .theme import current_theme


class FormShell(QDialog):
    """Frameless modal shell: head (QTextBrowser, fixed) / body (PickerList,
    scrolls) / editor (QLineEdit, transient) / foot (QLabel, fixed).

    set_header()/set_footer() repaint the chrome; open_sized() sizes to the
    rendered rows and opens centered over the owner; open_editor()/
    close_editor() run the transient typed-input row; reject() walks the
    esc ladder (editor first). body.plain_text() is the probe seam."""

    def __init__(self, parent, *,
                 on_cursor: Optional[Callable[[int], None]] = None,
                 on_activate: Optional[Callable[[Any], None]] = None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint)
        self.setModal(True)
        self.head = QTextBrowser(self)
        self.head.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.head.setOpenLinks(False)
        self.head.anchorClicked.connect(self._on_anchor)
        self.head.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.head.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.body = PickerList(self, on_cursor=on_cursor,
                               on_activate=on_activate)
        self.editor = QLineEdit(self)
        self.editor.setVisible(False)
        self.foot = QLabel(self)
        self.foot.setTextFormat(Qt.TextFormat.RichText)
        self.foot.setWordWrap(True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(1, 1, 1, 1)
        lay.setSpacing(0)
        lay.addWidget(self.head)
        lay.addWidget(self.body, 1)
        lay.addWidget(self.editor)
        lay.addWidget(self.foot)

    # ---- chrome ----------------------------------------------------------

    def set_header(self, title_html: str) -> None:
        """Repaint the fixed header (modal_header grammar: the mouse close
        rides every title) and re-theme the chrome around it. `title_html`
        is a rich-text fragment — callers escape user-derived content."""
        t = current_theme()
        chrome = ("background: %s; border: 1px solid %s; padding: 6px;"
                  % (t["surface"], t["border"]))
        self.head.setStyleSheet("QTextBrowser { %s }" % chrome)
        self.foot.setStyleSheet("QLabel { %s color: %s; }"
                                % (chrome, t["content-dim"]))
        self.head.setHtml("<div style='color:%s'>%s</div>"
                          % (t["content"], modal_header(title_html, t)))
        self.body.restyle()

    def set_footer(self, html: str) -> None:
        """Repaint the fixed footer — hints, and whatever transient note or
        error the subclass surfaces there (it never scrolls away)."""
        self.foot.setText(html)

    def _on_anchor(self, url) -> None:
        """The header's mouse close (140a7b3c); other anchors route on."""
        if is_close_anchor(url):
            self.reject()

    # ---- the transient editor row ----------------------------------------

    def open_editor(self, text: str) -> None:
        self.editor.setText(text)
        self.editor.setVisible(True)
        self.editor.setFocus()

    def close_editor(self) -> None:
        self.editor.setVisible(False)
        self.setFocus()

    def reject(self) -> None:
        """Esc: an open editor closes first (a modal IS a step — the
        action_back ladder's rule, applied inward)."""
        if self.editor.isVisible():
            self.close_editor()
            return
        super().reject()

    # ---- sizing (the keyhints recipe over native rows) -------------------

    def open_sized(self, min_width: int = 560) -> None:
        """Size to the rendered content — head document + body rows +
        detail + foot — capped by the owner, then open centered with the
        dialog holding focus (the subclass owns the keys)."""
        owner = self.parentWidget()
        avail_w = (owner.width() - 64) if owner is not None else 960
        avail_h = (owner.height() - 64) if owner is not None else 640
        width = min(avail_w,
                    max(self.body.view.sizeHintForColumn(0) + 48, min_width))
        doc = self.head.document()
        doc.setTextWidth(width - 24)
        head_h = int(doc.size().height()) + 12
        self.head.setFixedHeight(head_h)
        rows_h = sum(self.body.view.sizeHintForRow(i)
                     for i in range(self.body.view.count()))
        detail_h = (self.body.detail.height()
                    if self.body.detail.isVisibleTo(self.body) else 0)
        foot_h = self.foot.sizeHint().height()
        height = min(avail_h, head_h + rows_h + detail_h + foot_h + 30)
        self.resize(width, height)
        if owner is not None:
            center = owner.mapToGlobal(owner.rect().center())
            self.move(center.x() - self.width() // 2,
                      center.y() - self.height() // 2)
        self.open()
        self.setFocus()
