"""The lane's find-bar universal (the Ctrl-F half of signal c7955f25).

One horizontal bar — pattern field, match counter, prev/next/close — driving
incremental search over any QTextEdit-family pane (QPlainTextEdit / QTextEdit
/ QTextBrowser, duck-typed on find/setExtraSelections). Find-as-you-type
re-searches from where the bar opened, Enter steps next and Shift+Enter
previous, both wrap around, and every match paints as an extra selection
through the live theme. Esc closes and hands focus back to the pane, cursor
left on the current match. Apps wire open/next/previous to their own
KeymapRegistry verbs; the bar owns only its in-field keys."""

from typing import List, Optional

from cjm_substrate_qt_kit.theme import current_theme
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QTextCursor, QTextDocument
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QTextEdit, QToolButton, QWidget


class FindBar(QWidget):
    """Incremental find over an attached text pane."""

    def __init__(self, pane=None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.pane = pane
        self._origin: Optional[QTextCursor] = None
        self.field = QLineEdit(self)
        self.field.setPlaceholderText("find")
        self.field.textChanged.connect(self._on_typed)
        self.field.returnPressed.connect(self._on_return)
        self.count = QLabel("", self)
        self.count.setProperty("role", "content-dim")
        prev_btn = QToolButton(self)
        prev_btn.setText("↑")
        prev_btn.clicked.connect(self.previous)
        next_btn = QToolButton(self)
        next_btn.setText("↓")
        next_btn.clicked.connect(self.next)
        close_btn = QToolButton(self)
        close_btn.setText("✕")
        close_btn.clicked.connect(self.close_bar)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.addWidget(self.field, 1)
        layout.addWidget(self.count)
        layout.addWidget(prev_btn)
        layout.addWidget(next_btn)
        layout.addWidget(close_btn)
        self.hide()

    def attach(self, pane) -> None:
        """Point the bar at a (possibly different) pane; clears old paint."""
        if self.pane is not None and self.pane is not pane:
            self.pane.setExtraSelections([])
        self.pane = pane

    def open(self) -> None:
        """Show the bar, remember the pane's position as the search origin,
        seed the pattern from the pane's selection, focus the field."""
        if self.pane is None:
            return
        self._origin = QTextCursor(self.pane.textCursor())
        selected = self.pane.textCursor().selectedText()
        self.show()
        if selected and " " not in selected:
            self.field.setText(selected)
        self.field.selectAll()
        self.field.setFocus()

    def close_bar(self) -> None:
        """Hide, clear match paint, hand focus back to the pane."""
        self.hide()
        if self.pane is not None:
            self.pane.setExtraSelections([])
            self.pane.setFocus()

    def next(self) -> None:
        self._step(backward=False)

    def previous(self) -> None:
        self._step(backward=True)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close_bar()
            return
        super().keyPressEvent(event)

    def _on_return(self) -> None:
        from PySide6.QtWidgets import QApplication
        backward = bool(QApplication.keyboardModifiers()
                        & Qt.KeyboardModifier.ShiftModifier)
        self._step(backward=backward)

    def _on_typed(self, pattern: str) -> None:
        """Incremental: re-search forward from the opening origin so refining
        the pattern never walks away from where the user started."""
        if self.pane is None:
            return
        if self._origin is not None:
            cursor = QTextCursor(self._origin)
            cursor.clearSelection()
            self.pane.setTextCursor(cursor)
        self._step(backward=False, stay_on_origin=True)

    def _step(self, backward: bool, stay_on_origin: bool = False) -> None:
        """One find step with wrap-around, then repaint matches + counter."""
        pattern = self.field.text()
        matches = self._paint_matches(pattern)
        if not pattern or self.pane is None:
            self.count.setText("")
            return
        if not matches:
            self.count.setText("0/0")
            return
        flags = QTextDocument.FindFlag.FindBackward if backward else QTextDocument.FindFlag(0)
        found = self.pane.find(pattern, flags)
        if not found:
            wrap = QTextCursor(self.pane.document())
            wrap.movePosition(QTextCursor.MoveOperation.End if backward
                              else QTextCursor.MoveOperation.Start)
            self.pane.setTextCursor(wrap)
            found = self.pane.find(pattern, flags)
        current = self.pane.textCursor().selectionStart()
        index = next((i for i, pos in enumerate(matches) if pos == current), -1)
        self.count.setText(f"{index + 1}/{len(matches)}")

    def _paint_matches(self, pattern: str) -> List[int]:
        """Paint every match as an extra selection (theme-resolved accent
        wash); returns the match start positions for the counter."""
        if self.pane is None:
            return []
        if not pattern:
            self.pane.setExtraSelections([])
            return []
        theme = current_theme()
        wash = QColor(theme["accent"])
        wash.setAlpha(70)
        doc = self.pane.document()
        positions: List[int] = []
        selections = []
        cursor = QTextCursor(doc)
        while True:
            cursor = doc.find(pattern, cursor)
            if cursor.isNull():
                break
            positions.append(cursor.selectionStart())
            extra = QTextEdit.ExtraSelection()
            extra.cursor = QTextCursor(cursor)
            extra.format.setBackground(wash)
            selections.append(extra)
        self.pane.setExtraSelections(selections)


        return positions
