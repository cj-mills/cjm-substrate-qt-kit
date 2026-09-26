"""The reading pane: a QTextBrowser with the keyboard reading contract the
workbench grew (drive finds 2026-08-14) — link cycling from the TEXT cursor,
Return activation, j/k scrolling, and the SEAT (scroll + cursor selection)
saved and restored across repaints. QTextBrowser's native tab cycling keeps a
private focus cursor that cannot be seeded, so a jump could never carry it;
here tab / shift+tab select the next / previous anchor from the text cursor
(which jumps, back and reload all steer) and enter activates the selected
one through the ONE `activated` route a click also takes."""

from typing import List, Optional, Tuple

from PySide6.QtCore import QEvent, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QTextBrowser, QWidget

from .keys import bind

Seat = Tuple[int, int, int]      # (scroll, cursor anchor, cursor position)


class ReadingPane(QTextBrowser):
    activated = Signal(QUrl)     # a link opened by click OR tab + enter

    def __init__(self, parent: Optional[QWidget] = None, *,
                 scroll_keys: Tuple[str, str] = ("J", "K"), scroll_lines: int = 3):
        super().__init__(parent)
        self.setOpenLinks(False)
        self.setTabChangesFocus(False)     # tab stays ours: links, not widgets
        self.document().setDocumentMargin(16)
        self.anchorClicked.connect(self.activated.emit)
        self._scroll_lines = scroll_lines
        if scroll_keys:
            down, up = scroll_keys
            bind(self, down, lambda: self.scroll_lines(self._scroll_lines), self,
                 Qt.ShortcutContext.WidgetShortcut)
            bind(self, up, lambda: self.scroll_lines(-self._scroll_lines), self,
                 Qt.ShortcutContext.WidgetShortcut)

    # ---- keys --------------------------------------------------------------

    def event(self, event) -> bool:
        """Tab / Backtab are claimed in event(): QWidget routes them to focus
        navigation before keyPressEvent ever sees them."""
        if event.type() == QEvent.Type.KeyPress and event.key() in (Qt.Key.Key_Tab,
                                                                     Qt.Key.Key_Backtab):
            self.cycle_link(1 if event.key() == Qt.Key.Key_Tab else -1)
            event.accept()
            return True
        return super().event(event)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self.activate_link():
            return
        super().keyPressEvent(event)

    def scroll_lines(self, lines: int) -> None:
        bar = self.verticalScrollBar()
        bar.setValue(bar.value() + lines * bar.singleStep())

    # ---- the seat ------------------------------------------------------------

    def seat(self) -> Seat:
        """(scroll, cursor anchor, cursor position): tab link-cycling runs
        off the text cursor, so the whole selection is part of the seat —
        back re-lights the exact link you left."""
        cur = self.textCursor()
        return (self.verticalScrollBar().value(), cur.anchor(), cur.position())

    def restore_seat(self, seat, deferred: bool = True) -> None:
        """Put the seat back after a repaint. DEFERRED by default: setMarkdown's
        layout lands on the NEXT event-loop pass, and the not-yet-grown scroll
        range would clamp the value to the top. Immediate for an in-page pop
        (the document is unchanged)."""
        if deferred:
            QTimer.singleShot(0, lambda: self._restore(seat))
        else:
            self._restore(seat)

    def _restore(self, seat) -> None:
        if isinstance(seat, tuple):
            scroll, anchor, pos = seat
            limit = self.document().characterCount() - 1
            cursor = self.textCursor()
            cursor.setPosition(min(anchor, limit))
            cursor.setPosition(min(pos, limit), QTextCursor.MoveMode.KeepAnchor)
            self.setTextCursor(cursor)
        else:
            scroll = int(seat)
        self.verticalScrollBar().setValue(scroll)

    # ---- links ---------------------------------------------------------------

    def anchor_spans(self) -> List[Tuple[int, int, str]]:
        """(start, end, href) for every link in document order; contiguous
        fragments of one anchor merge into a single span."""
        spans: List[Tuple[int, int, str]] = []
        block = self.document().begin()
        while block.isValid():
            it = block.begin()
            while not it.atEnd():
                frag = it.fragment()
                fmt = frag.charFormat()
                href = fmt.anchorHref() if fmt.isAnchor() else ""
                if href:
                    start, end = frag.position(), frag.position() + frag.length()
                    if spans and spans[-1][2] == href and spans[-1][1] == start:
                        spans[-1] = (spans[-1][0], end, href)
                    else:
                        spans.append((start, end, href))
                it += 1
            block = block.next()
        return spans

    def cycle_link(self, delta: int) -> None:
        """Select the next / previous link from the text cursor (wrapping);
        the SELECTION is the visible focus indicator and the seat follows."""
        spans = self.anchor_spans()
        if not spans:
            return
        cur = self.textCursor()
        lo = min(cur.anchor(), cur.position())
        hi = max(cur.anchor(), cur.position())
        if delta > 0:
            nxt = next((s for s in spans if s[0] >= hi and (s[0], s[1]) != (lo, hi)), spans[0])
        else:
            nxt = next((s for s in reversed(spans) if s[1] <= lo and (s[0], s[1]) != (lo, hi)),
                       spans[-1])
        cur.setPosition(nxt[0])
        cur.setPosition(nxt[1], QTextCursor.MoveMode.KeepAnchor)
        self.setTextCursor(cur)
        self.ensureCursorVisible()

    def focused_href(self) -> Optional[str]:
        """The tab-selected link's href, if a link is selected."""
        cur = self.textCursor()
        if not cur.hasSelection():
            return None
        probe = self.textCursor()
        probe.setPosition(cur.selectionStart() + 1)   # format of the char AT start
        fmt = probe.charFormat()
        return fmt.anchorHref() if fmt.isAnchor() and fmt.anchorHref() else None

    def activate_link(self) -> bool:
        """Open the tab-selected link (enter); False when none is selected."""
        href = self.focused_href()
        if not href:
            return False
        self.activated.emit(QUrl(href))
        return True

    def scroll_to_block(self, text: str, after_prefix: Optional[str] = None) -> bool:
        """Scroll so the first block whose text EQUALS `text` (after a block
        starting with `after_prefix`, when given) sits at the viewport top;
        the keyboard cursor travels with the jump so tab cycles that group's
        links next. Block-exact matching: a title that merely CONTAINS the
        word can never false-match."""
        doc = self.document()
        block = doc.begin()
        armed = after_prefix is None
        while block.isValid():
            if not armed:
                armed = block.text().startswith(after_prefix)
            elif block.text() == text:
                self.setTextCursor(QTextCursor(block))
                bar = self.verticalScrollBar()
                bar.setValue(bar.value() + self.cursorRect(QTextCursor(block)).top())
                return True
            block = block.next()
        return False
