"""Keyboard-hints surface: the ?-overlay + contextual hint line (DEC 2a42c028).

The footer decomposition's discovery half: gesture reference leaves the
always-on strip for an on-demand overlay. The hint MODEL is declarative
data — [{verb, label, key, group}] — registry apps derive it from
KeymapRegistry.entries() and keyPressEvent-idiom apps declare it directly.
The overlay groups entries into titled sections, lays sections out in
1/2/3 responsive columns (the FastHTML-era shortcuts modal is the design
precedent), renders keys as key-cap chips through the live theme, and
carries the PIN gesture: pinned verbs project into the contextual hint
line (hint_line()), so the overlay is the hint-line customization
surface — and the seat the future remapping UI extends. It is a modal
frameless dialog so the owning window's bare-letter shortcuts cannot
fire underneath it."""

from typing import Callable, Dict, List, Optional, Tuple

from cjm_substrate_qt_kit.layout import afford
from cjm_substrate_qt_kit.theme import current_theme
from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import QDialog, QTextBrowser, QVBoxLayout, QWidget

Entry = Dict[str, str]

# Per-column content width the layouts are tuned around (key caps + label
# + pin glyph at ui-font sizes); window space buys columns up to 3.
_COL_WIDTH = 360


def group_entries(entries: List[Entry]) -> List[Tuple[str, List[Entry]]]:
    """[{verb,label,key,group}] -> [(group, entries)] in first-seen group
    order; an empty/missing group files under "General"."""
    sections: Dict[str, List[Entry]] = {}
    for entry in entries:
        sections.setdefault(entry.get("group") or "General", []).append(entry)
    return list(sections.items())


def hint_line(entries: List[Entry], pins: List[str], limit: int = 5) -> str:
    """Project the pinned verbs (in pin order, capped at limit) into the
    contextual hint line, always ending with the overlay's own discovery
    hint. Unknown pins are skipped, so a stale persisted pin never crashes
    the line."""
    by_verb = {e["verb"]: e for e in entries}
    parts = [f"{by_verb[v]['key']} {by_verb[v]['label']}"
             for v in pins if v in by_verb][:limit]
    parts.append("? keys")
    return " · ".join(parts)


def column_count(avail_width: int, section_count: int) -> int:
    """Responsive column count: what the CONTAINER width affords (layout
    R3 density-shift), capped by content (never more columns than
    sections) and by 3."""
    return afford(avail_width, _COL_WIDTH, min(section_count, 3))


def _keycaps(key: str, theme: dict) -> str:
    """Render a key sequence as key-cap chips ("Ctrl+Shift+K" -> three
    caps joined by +). Qt rich text styles spans with background only, so
    caps read as chips via background + padding NBSPs."""
    cap = ('<span style="background-color:{raised}; color:{content}; '
           'font-family:monospace;">&nbsp;{tok}&nbsp;</span>')
    toks = [cap.format(raised=theme["raised"], content=theme["content"], tok=t)
            for t in str(key).split("+")]
    return ('<span style="color:%s;">+</span>' % theme["content-dim"]).join(toks)


def render_hints_html(entries: List[Entry], pins: List[str], columns: int,
                      theme: Optional[dict] = None) -> str:
    """The overlay's document: sections distributed across columns in
    reading order (balanced by row count), each section a titled table of
    key caps + label + pin anchor. Pin anchors carry pin:<verb> hrefs; the
    footer names both toggles (? and Esc)."""
    t = theme if theme is not None else current_theme()
    sections = group_entries(entries)
    per_col = [[] for _ in range(max(1, columns))]
    total = sum(len(rows) for _, rows in sections) or 1
    target = total / max(1, columns)
    index, filled = 0, 0
    for section in sections:
        if index < columns - 1 and filled >= target * (index + 1):
            index += 1
        per_col[index].append(section)
        filled += len(section[1])
    dim, border = t["content-dim"], t["border"]
    columns_html = []
    for col in per_col:
        blocks = []
        for group, rows in col:
            body = "".join(
                '<tr><td style="white-space:nowrap;">%s</td>'
                '<td style="padding-left:14px; white-space:nowrap;">%s</td>'
                '<td style="padding-left:10px;"><a href="pin:%s" '
                'style="text-decoration:none; color:%s;">%s</a></td></tr>'
                % (_keycaps(row["key"], t), row["label"], row["verb"],
                   t["accent"] if row["verb"] in pins else dim,
                   "&#9679;" if row["verb"] in pins else "&#9675;")
                for row in rows)
            blocks.append(
                '<p style="color:%s;"><b>%s</b></p>'
                '<table cellspacing="0" cellpadding="2">%s</table>'
                % (dim, group, body))
        columns_html.append('<td style="vertical-align:top; '
                            'padding-right:26px;">%s</td>' % "".join(blocks))
    return (modal_header("Keyboard hints", t)
            + '<table cellspacing="0" cellpadding="0"><tr>%s</tr></table>'
            '<p style="color:%s;">&#9679; pinned to the hint line &nbsp;·&nbsp; '
            '? or Esc or &#10005; closes</p>'
            % ("".join(columns_html), dim))


class KeyHintsOverlay(QDialog):
    """?-toggled keyboard-hints overlay. Modal + frameless, centered over
    the owner window, sized to the afforded column count at open time.
    Clicking a row's pin glyph toggles that verb into the hint line and
    reports the new pin set through on_pins_changed (the app persists it —
    the kit holds no store)."""

    def __init__(self, parent: QWidget, entries: Optional[List[Entry]] = None,
                 pins: Optional[List[str]] = None,
                 on_pins_changed: Optional[Callable[[List[str]], None]] = None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint)
        self.setModal(True)
        self._entries: List[Entry] = list(entries or [])
        self.pins: List[str] = list(pins or [])
        self._on_pins_changed = on_pins_changed
        self.view = QTextBrowser(self)
        self.view.setOpenLinks(False)
        self.view.anchorClicked.connect(self._on_anchor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.addWidget(self.view)

    def set_entries(self, entries: List[Entry]) -> None:
        """Swap the hint model (lane changes re-point the overlay); a
        visible overlay re-renders in place."""
        self._entries = list(entries)
        if self.isVisible():
            self._render()

    def toggle(self) -> None:
        if self.isVisible():
            self.close()
        else:
            self.open_overlay()

    def open_overlay(self) -> None:
        """Render at the afforded column count, then size the dialog to the
        RENDERED document — fixed column-width sizing left the panel mostly
        empty (drive verdict 2026-08-25) — center over the owner, and show
        modally (QDialog.open — non-blocking, but the owner's shortcuts stay
        inert underneath)."""
        owner = self.parentWidget()
        avail_w = (owner.width() - 64) if owner is not None else 1000
        avail_h = (owner.height() - 64) if owner is not None else 640
        self._render()
        doc = self.view.document()
        doc.setTextWidth(-1)
        width = min(avail_w, int(doc.idealWidth()) + 44)
        doc.setTextWidth(width - 30)
        height = min(avail_h, int(doc.size().height()) + 32)
        self.resize(width, height)
        if owner is not None:
            center = owner.mapToGlobal(owner.rect().center())
            self.move(center.x() - self.width() // 2,
                      center.y() - self.height() // 2)
        self.open()
        self.view.setFocus()

    def _render(self) -> None:
        owner = self.parentWidget()
        avail = (owner.width() - 64) if owner is not None else self.width()
        cols = column_count(avail, len(group_entries(self._entries)))
        theme = current_theme()
        self.view.setStyleSheet(
            "QTextBrowser { background: %s; border: 1px solid %s; "
            "padding: 12px; }" % (theme["surface"], theme["border"]))
        self.view.setHtml(render_hints_html(self._entries, self.pins, cols,
                                            theme))

    def _toggle_pin(self, verb: str) -> None:
        """Flip a verb's pinned state, keeping pin order stable, and report
        the new set to the app."""
        if verb in self.pins:
            self.pins.remove(verb)
        else:
            self.pins.append(verb)
        if self._on_pins_changed is not None:
            self._on_pins_changed(list(self.pins))
        if self.isVisible():
            self._render()

    def _on_anchor(self, url: QUrl) -> None:
        if is_close_anchor(url):      # the header's mouse close (140a7b3c)
            self.close()
            return
        target = url.toString()
        if target.startswith("pin:"):
            self._toggle_pin(target[len("pin:"):])

    def keyPressEvent(self, event) -> None:
        # Esc closes via QDialog natively; ? closes because it opened.
        if event.text() == "?":
            self.close()
            return
        super().keyPressEvent(event)


def keycaps(key: str, theme: Optional[dict] = None) -> str:
    """Public key-cap renderer — the overlay's chip grammar for OTHER
    rich-text surfaces (e.g. a StatusStrip context row rendering pickable
    tokens as caps). Live theme by default."""
    return _keycaps(key, theme if theme is not None else current_theme())


def modal_header(title_html: str, theme: Optional[dict] = None) -> str:
    """A kit modal's title row: the title at left, the mouse CLOSE
    affordance at right — an anchor carrying the close href, so every
    QTextBrowser-painted modal (the ?-overlay, the finetune form, the
    FormDialog shell) closes by click through the same anchorClicked route
    as its other links (the dialog tests the url with is_close_anchor).
    Walkthrough call-out 140a7b3c: frameless modals had keyboard-only
    dismissal. `title_html` is a rich-text fragment — callers escape any
    user-derived content themselves."""
    t = theme if theme is not None else current_theme()
    return ('<table width="100%%" cellspacing="0" cellpadding="0"><tr>'
            '<td><h3 style="margin:0;">%s</h3></td>'
            '<td align="right" style="vertical-align:top;">'
            '<a href="close:" title="close" style="text-decoration:none; '
            'color:%s;">&nbsp;&#10005;&nbsp;</a></td></tr></table>'
            % (title_html, t["content-dim"]))


def is_close_anchor(url: QUrl) -> bool:
    """True for the close affordance modal_header paints — the dialog's
    anchorClicked slot closes on it and routes everything else on."""
    return url.toString() == "close:"
