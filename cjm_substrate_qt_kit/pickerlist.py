"""Kit PickerList (work item 8d29f0f0): the native list PAGE the painted
pickers rebuild on.

The TUI-carryover pickers painted rows into a scroll-dead text pane — the
wheel moved the cursor but the view never followed, nothing was clickable,
and a list taller than the window meant growing the window. This widget is
shape (b) of that item: a real QListWidget under a rich-text row delegate,
so every consumer gets click-to-cursor, double-click activation, keyboard
cursor moves with ensure-visible scroll-follow, and native wheel/scrollbar
page scrolling for free.

Row vocabulary (caller-composed, paint-ready — the trainrun_rows pattern
widened to styled spans): each row is a dict
    {"kind": "item" | "header" | "note",
     "spans": [(text, style-words), ...],
     "key": Any}
"item" rows are pickable — the cursor walks exactly these, and "key" is
what a pick means (a source id, a manifest, a form field). "header" rows
are group headings (hub-collection grouping is the caller interleaving
them); "note" rows are annotations (empty-state hints, wrapped logs).
Neither is pickable or selectable.

The DETAIL pane under the list is the budget-reserved focused-row detail
region (the decomp TUI pattern the user ratified in 2e0928f2): the caller
repaints it from on_cursor — a cursor move re-renders the detail alone,
never the list (the ba21e0b8 full-clear-and-repaint class, avoided by
construction).

The widget owns NO keys (NoFocus, like every lane list — a focused
QListWidget keyboard-searches on letter presses): the window's key table
routes j/k/page moves to move()/set_cursor() and enter to activation."""

import html as _html
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QFontMetrics, QTextDocument
from PySide6.QtWidgets import (QAbstractItemView, QListWidget, QListWidgetItem, QStyle,
                               QStyledItemDelegate, QTextBrowser, QVBoxLayout, QWidget)

from .theme import current_theme, make_font, state_color

Span = Tuple[str, str]          # (text, style words: color word(s) + "bold")
Row = Dict[str, Any]            # {"kind", "spans", "key"}

_ROW_HTML = int(Qt.ItemDataRole.UserRole)


def spans_to_html(spans: Sequence[Span],          # One row's styled spans
                  theme: Optional[dict] = None,   # Live theme by default
                  ) -> str:  # One rich-text row fragment (whitespace-preserving)
    """Project style-worded spans into one QTextDocument-ready fragment.

    Style words route through the theme (legacy Rich words via WORD_ROLES —
    the style.apply_row_style mapping, kept span-granular here so a row can
    mix chips: a yellow mark count beside a green purpose chip). The row
    wraps in white-space:pre so the mono column alignment the span builders
    lean on survives HTML."""
    t = theme if theme is not None else current_theme()
    parts: List[str] = []
    for text, style in spans:
        words = str(style or "").split()
        css: List[str] = []
        for w in words:
            color = state_color(w, t)
            if color is not None:
                css.append("color:%s" % color.name())
                break                     # first color word wins, like a QBrush
        if "bold" in words:
            css.append("font-weight:bold")
        piece = _html.escape(str(text), quote=False)
        parts.append("<span style='%s'>%s</span>" % (";".join(css), piece)
                     if css else piece)
    body = "".join(parts) or "&nbsp;"
    return "<div style='white-space:pre'>%s</div>" % body


class SpanRowDelegate(QStyledItemDelegate):
    """Paint one row's rich-text fragment (the _ROW_HTML data) through a
    QTextDocument — QListWidgetItem's plain text + single foreground loses
    the span chips the picker rows carry. Selection paints the theme's
    raised ground behind the fragment (the cursor row's visual)."""

    _SIZE_CACHE_MAX = 20000

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        # sizeHint is asked for EVERY row on a cursor move / scroll (Qt lays
        # the whole list out), and a QTextDocument per ask cost ~0.2 s a
        # frame on ~2800 rows (2026-09-02). The hint depends only on the
        # fragment + font, so it is memoized per (html, font key).
        self._sizes: Dict[Tuple[str, str], QSize] = {}

    def _doc(self, option, index) -> QTextDocument:
        doc = QTextDocument()
        doc.setDefaultFont(option.font)
        doc.setDocumentMargin(2.0)
        doc.setHtml(str(index.data(_ROW_HTML) or ""))
        return doc

    def paint(self, painter, option, index) -> None:
        doc = self._doc(option, index)
        painter.save()
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, QColor(current_theme()["raised"]))
        painter.translate(option.rect.topLeft())
        doc.drawContents(painter)
        painter.restore()

    def sizeHint(self, option, index) -> QSize:
        html = str(index.data(_ROW_HTML) or "")
        key = (html, option.font.key())
        size = self._sizes.get(key)
        if size is None:
            doc = self._doc(option, index)
            size = QSize(int(doc.idealWidth()) + 4, int(doc.size().height()))
            if len(self._sizes) >= self._SIZE_CACHE_MAX:
                self._sizes.clear()
            self._sizes[key] = size
        return size


class PickerList(QWidget):
    """The kit list page: native list above, budget-reserved detail below.

    set_rows() rebuilds the listing (cursor positioned silently — the
    caller owns cursor state); move()/set_cursor() are the keyboard seam
    (clamped, ensure-visible, on_cursor fires on change); a click on a
    pickable row moves the cursor through the same seam, a double-click
    (or the window's enter key calling activate()) hands the row's key to
    on_activate. set_detail() repaints the detail pane alone."""

    def __init__(self, parent: Optional[QWidget] = None, *,
                 on_cursor: Optional[Callable[[int], None]] = None,
                 on_activate: Optional[Callable[[Any], None]] = None,
                 detail_budget_rows: int = 6,
                 detail_above: bool = False):   # detail pane ABOVE the list (glance-first)
        super().__init__(parent)
        self._on_cursor = on_cursor
        self._on_activate = on_activate
        self._detail_budget = max(1, int(detail_budget_rows))
        self.detail_above = bool(detail_above)
        self._pickable: List[int] = []   # pickable index -> view row
        self._keys: List[Any] = []       # pickable index -> row key
        self._plain: List[str] = []      # every row's flat text (probe seam)
        self._cursor = 0
        self.view = QListWidget(self)
        self.view.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.view.setFont(make_font(kind="mono"))
        self.view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.view.setItemDelegate(SpanRowDelegate(self.view))
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.view.itemPressed.connect(self._on_pressed)
        self.view.itemDoubleClicked.connect(self._on_double)
        self.detail = QTextBrowser(self)
        self.detail.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.detail.setFont(make_font(kind="mono"))
        self.detail.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.detail.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.detail.setVisible(False)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        if self.detail_above:
            # The focused row's detail sits ABOVE the listing (user ruling
            # 2026-09-02: the "Why:" reasoning is what the eye checks first).
            lay.addWidget(self.detail)
            lay.addWidget(self.view, 1)
        else:
            lay.addWidget(self.view, 1)
            lay.addWidget(self.detail)
        self.restyle()

    # ---- rows ------------------------------------------------------------

    def set_rows(self, rows: Sequence[Row],
                 cursor: Optional[int] = None) -> None:
        """Rebuild the listing. `cursor` positions the pickable cursor
        (clamped) without firing on_cursor — the caller is handing us the
        position it already holds, not learning a new one."""
        self.view.clear()
        self._pickable, self._keys, self._plain = [], [], []
        t = current_theme()
        for r in rows:
            self._plain.append("".join(tx for tx, _ in (r.get("spans") or [])))
            item = QListWidgetItem()
            item.setData(_ROW_HTML, spans_to_html(r.get("spans") or [], t))
            if (r.get("kind") or "item") == "item":
                self._pickable.append(self.view.count())
                self._keys.append(r.get("key"))
            else:
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)   # visible, unpickable
            self.view.addItem(item)
        self._set_cursor(self._cursor if cursor is None else int(cursor),
                         notify=False)

    def set_rows_cursor(self, cursor: int) -> None:
        """Position the cursor the way set_rows() does — silently, no
        on_cursor — without rebuilding the rows (the unchanged-listing
        fast path a caller takes when only its cursor moved)."""
        self._set_cursor(int(cursor), notify=False)

    @property
    def cursor(self) -> int:
        """The pickable-row cursor (an index into the item rows only)."""
        return self._cursor

    def count(self) -> int:
        """How many PICKABLE rows the listing holds."""
        return len(self._pickable)

    def current_key(self) -> Any:
        """The cursor row's key (None on an empty listing)."""
        return (self._keys[self._cursor]
                if 0 <= self._cursor < len(self._keys) else None)

    def plain_text(self) -> str:
        """Every row's flat text, one line each — the offscreen probe/test
        seam (the rich content lives in the delegate's HTML)."""
        return "\n".join(self._plain)

    # ---- cursor ----------------------------------------------------------

    def _set_cursor(self, i: int, *, notify: bool) -> None:
        if not self._pickable:
            self._cursor = 0
            self.view.setCurrentRow(-1)
            return
        i = max(0, min(len(self._pickable) - 1, int(i)))
        changed = (i != self._cursor)
        self._cursor = i
        row = self._pickable[i]
        if self.view.currentRow() != row:
            self.view.setCurrentRow(row)
        item = self.view.item(row)
        if item is not None:
            self.view.scrollToItem(item)   # EnsureVisible — the scroll-follow
        if changed and notify and self._on_cursor is not None:
            self._on_cursor(i)

    def set_cursor(self, i: int) -> None:
        """Move the cursor to pickable row i (clamped, ensure-visible;
        on_cursor fires when the position actually changed)."""
        self._set_cursor(i, notify=True)

    def move(self, delta: int) -> None:
        """Step the cursor (the window key table's j/k/page seam)."""
        self._set_cursor(self._cursor + delta, notify=True)

    def activate(self) -> None:
        """Hand the cursor row's key to on_activate (the enter key's dual
        of a double-click)."""
        if self._on_activate is not None and self._pickable:
            self._on_activate(self.current_key())

    # ---- mouse -----------------------------------------------------------

    def _pickable_index(self, item: Optional[QListWidgetItem]) -> Optional[int]:
        if item is None:
            return None
        row = self.view.row(item)
        try:
            return self._pickable.index(row)
        except ValueError:
            return None

    def _on_pressed(self, item) -> None:
        """Click-to-cursor: a pickable row takes the cursor; a click on a
        header/note row restores the selection to the cursor row (the
        native press may have cleared it)."""
        i = self._pickable_index(item)
        if i is None:
            if self._pickable:
                self.view.setCurrentRow(self._pickable[self._cursor])
            return
        self._set_cursor(i, notify=True)

    def _on_double(self, item) -> None:
        i = self._pickable_index(item)
        if i is None:
            return
        self._set_cursor(i, notify=True)
        self.activate()

    # ---- detail ----------------------------------------------------------

    def set_detail(self, lines: Optional[Sequence[Sequence[Span]]]) -> None:
        """Repaint the budget-reserved detail pane: span lines (or nothing,
        which hides it). Height fits the content, capped at the budget —
        the list keeps the rest of the page."""
        if not lines:
            self.detail.setVisible(False)
            return
        t = current_theme()
        body = "".join(spans_to_html(ln, t) for ln in lines)
        self.detail.setHtml("<div style='color:%s'>%s</div>"
                            % (t["content"], body))
        fm = QFontMetrics(self.detail.font())
        cap = fm.lineSpacing() * self._detail_budget + 10
        doc = self.detail.document()
        doc.setTextWidth(-1)
        self.detail.setFixedHeight(min(cap, int(doc.size().height()) + 10))
        self.detail.setVisible(True)

    # ---- chrome ----------------------------------------------------------

    def restyle(self) -> None:
        """Re-apply the live theme's chrome (call on theme swap)."""
        t = current_theme()
        chrome = ("background: %s; border: 1px solid %s; color: %s;"
                  % (t["surface"], t["border"], t["content"]))
        self.view.setStyleSheet("QListWidget { %s }" % chrome)
        self.detail.setStyleSheet("QTextBrowser { %s }" % chrome)
        self.view.setFont(make_font(kind="mono"))
        self.detail.setFont(make_font(kind="mono"))
