"""The lane's find-bar universal (the Ctrl-F half of signal c7955f25).

One horizontal bar — pattern field, match-option toggles, match counter,
prev/next/close — driving incremental search over any QTextEdit-family pane
(QPlainTextEdit / QTextEdit / QTextBrowser, duck-typed on
find/setExtraSelections). Find-as-you-type re-searches from where the bar
opened, Enter steps next and Shift+Enter previous, both wrap around, and
every match paints as an extra selection through the live theme — the
FOCUSED match visibly stronger than the rest (the 671e9b11 pt-5 call-out:
uniform paint hid which hit was current). The standard option trio — match
case (Aa), whole word (W), regex (.*) — folds into ONE QRegularExpression
(a literal pattern is escaped first), so stepping and painting share a
single search truth. Esc closes and hands focus back to the pane, cursor
left on the current match. Apps wire open/next/previous to their own
KeymapRegistry verbs; the bar owns only its in-field keys."""

from typing import List, Optional

from cjm_substrate_qt_kit.theme import current_theme
from PySide6.QtCore import QRegularExpression, Qt
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

        def option(text: str, tip: str) -> QToolButton:
            btn = QToolButton(self)
            btn.setText(text)
            btn.setToolTip(tip)
            btn.setCheckable(True)
            btn.toggled.connect(lambda _on: self._on_typed(self.field.text()))
            return btn

        self.case_btn = option("Aa", "Match case")
        self.word_btn = option("W", "Whole word")
        self.regex_btn = option(".*", "Regular expression")
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
        layout.addWidget(self.case_btn)
        layout.addWidget(self.word_btn)
        layout.addWidget(self.regex_btn)
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
        if selected and " " not in selected:
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
        the pattern (or flipping an option) never walks away from where the
        user started."""
        if self.pane is None:
            return
        if self._origin is not None:
            cursor = QTextCursor(self._origin)
            cursor.clearSelection()
            self.pane.setTextCursor(cursor)
        self._step(backward=False, stay_on_origin=True)

    def _expression(self) -> Optional[QRegularExpression]:
        """The three options folded into one expression: literal patterns are
        escaped, whole-word wraps in \\b, case rides the pattern option (and
        the find flag, belt-and-braces across Qt's find variants). None for
        an empty or invalid pattern."""
        pattern = self.field.text()
        if not pattern:
            return None
        if not self.regex_btn.isChecked():
            pattern = QRegularExpression.escape(pattern)
        if self.word_btn.isChecked():
            pattern = r"\b(?:" + pattern + r")\b"
        rx = QRegularExpression(pattern)
        if not self.case_btn.isChecked():
            rx.setPatternOptions(QRegularExpression.PatternOption.CaseInsensitiveOption)
        return rx if rx.isValid() else None

    def _step(self, backward: bool, stay_on_origin: bool = False) -> None:
        """One find step with wrap-around, then repaint matches + counter."""
        rx = self._expression()
        if rx is None or self.pane is None:
            if self.pane is not None:
                self.pane.setExtraSelections([])
            self.count.setText("regex?" if self.field.text() else "")
            return
        # QTextDocument.find takes case sensitivity from the FLAG, not the
        # pattern option — scan flags must match step flags or counts drift.
        scan_flags = QTextDocument.FindFlag(0)
        if self.case_btn.isChecked():
            scan_flags |= QTextDocument.FindFlag.FindCaseSensitively
        matches = self._match_positions(rx, scan_flags)
        if not matches:
            self._paint(rx, scan_flags, current=-1)
            self.count.setText("0/0")
            return
        flags = scan_flags | (QTextDocument.FindFlag.FindBackward if backward
                              else QTextDocument.FindFlag(0))
        found = self.pane.find(rx, flags)
        if not found:
            wrap = QTextCursor(self.pane.document())
            wrap.movePosition(QTextCursor.MoveOperation.End if backward
                              else QTextCursor.MoveOperation.Start)
            self.pane.setTextCursor(wrap)
            self.pane.find(rx, flags)
        current = self.pane.textCursor().selectionStart()
        index = next((i for i, pos in enumerate(matches) if pos == current), -1)
        self._paint(rx, scan_flags, current=current)
        self.count.setText(f"{index + 1}/{len(matches)}")

    def _match_positions(self, rx: QRegularExpression, flags) -> List[int]:
        """Every match start position in document order."""
        if self.pane is None:
            return []
        doc = self.pane.document()
        positions: List[int] = []
        cursor = QTextCursor(doc)
        while True:
            cursor = doc.find(rx, cursor, flags)
            if cursor.isNull():
                break
            if cursor.selectionStart() == cursor.selectionEnd():
                break  # zero-width regex match — bail rather than loop forever
            positions.append(cursor.selectionStart())
        return positions

    def _paint(self, rx: QRegularExpression, flags, current: int) -> None:
        """Paint every match as an extra selection: a theme-accent wash for
        the field, a solid accent block for the FOCUSED match — visually
        distinct at a glance (671e9b11 pt 5)."""
        if self.pane is None:
            return
        theme = current_theme()
        wash = QColor(theme["accent"])
        wash.setAlpha(60)
        focus = QColor(theme["accent"])
        focus.setAlpha(170)
        doc = self.pane.document()
        selections = []
        cursor = QTextCursor(doc)
        while True:
            cursor = doc.find(rx, cursor, flags)
            if cursor.isNull():
                break
            if cursor.selectionStart() == cursor.selectionEnd():
                break
            extra = QTextEdit.ExtraSelection()
            extra.cursor = QTextCursor(cursor)
            if cursor.selectionStart() == current:
                extra.format.setBackground(focus)
                extra.format.setForeground(QColor(theme["accent-content"]))
            else:
                extra.format.setBackground(wash)
            selections.append(extra)
        self.pane.setExtraSelections(selections)
