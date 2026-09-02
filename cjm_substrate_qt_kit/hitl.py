"""Kit HITL confirm chrome (work item 55bcc3c5, the payload-agnostic half of
the confirm component): a ProposalWorklist, a VerdictStrip and a
ProvenancePane, composed by HitlPanel.

Every agent-first lane has the same human-in-the-loop shape — a proposer
wrote rows over a source, the human walks them and confirms — and only the
PAYLOAD differs (an event span with audio, a filtering stratum over a
segment run, later a boundary edit). This module is the shape: the host
app owns the payload card (it needs the app's audio player and spine view)
and paints it into the worklist's detail slot through set_payload().

Item vocabulary (caller-composed, like PickerList rows): each worklist item
is a dict
    {"key": Any,                 # what a pick means (the proposal id)
     "tier": 1 | 2,              # 1 = batch-acceptable, 2 = audition (dim)
     "category": str,            # the proposed class / label
     "start": float | None,      # source seconds
     "end": float | None,
     "confidence": float | None,
     "quote": str,               # a few verbatim words (find-it-fast)
     "index": int | None,        # the host's navigation coordinate (spine index)
     "state": str}               # "pending" (default) | anything else = dim tag
The worklist owns NO keys (NoFocus, like every kit list): the host's key
table drives move()/set_cursor()/activate().

Verdicts are DERIVED numbers the host computes (a bench join); the strip
just paints them by role. Provenance is key/value pairs — set id, proposer,
pack digest, window, session actor — whatever the lane's manifest carries."""

import html as _html
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QTextBrowser, QVBoxLayout, QWidget

from .pickerlist import PickerList, Row, Span
from .theme import current_theme, make_font, state_color

Item = Dict[str, Any]

# Verdict roles: the bench's vocabulary painted through the theme's state channel.
VERDICT_ROLES: Dict[str, str] = {
    "accepted": "ok", "edited": "info", "relabeled": "meta",
    "rejected": "danger", "unaccepted": "warn", "unvisited": "dim", "missed": "warn",
}


def fmt_ts(seconds: Optional[float]) -> str:  # mm:ss.s, or --:-- when unknown
    """Source-seconds as mm:ss.s — the worklist's span column."""
    if seconds is None:
        return "--:--"
    m, s = divmod(max(0.0, float(seconds)), 60.0)
    return f"{int(m):02d}:{s:04.1f}"


def worklist_row(item: Item) -> Row:  # One paint-ready PickerList row
    """Project one item into a picker row: tier glyph (? / ??), the category
    chip (tier 1 cyan, tier 2 dim magenta — the walk-lane chip grammar), the
    span, the confidence, then the quote. A non-pending state dims the row
    and appends its tag (an accepted-elsewhere row a host may keep listed)."""
    tier = int(item.get("tier", 1) or 1)
    glyph = "??" if tier == 2 else "? "
    chip_style = "magenta" if tier == 2 else "cyan"
    state = str(item.get("state") or "pending")
    dim = state != "pending"
    conf = item.get("confidence")
    spans: List[Span] = [
        (glyph, "dim" if tier == 2 else "bold"),
        (f"{str(item.get('category') or '?'):<14.14} ", ("dim " if dim else "") + chip_style),
        (f"{fmt_ts(item.get('start'))}–{fmt_ts(item.get('end'))} ", "dim"),
        ((f"c={float(conf):.2f} " if isinstance(conf, (int, float)) else "     "), "dim"),
        (f"“{str(item.get('quote') or '')[:48]}”", "dim" if dim or tier == 2 else ""),
    ]
    if dim:
        spans.append((f"  [{state}]", "dim"))
    return {"kind": "item", "spans": spans, "key": item.get("key")}


class ProposalWorklist(QWidget):
    """The proposal list page: items above (a kit PickerList), the host's
    payload card below in the detail slot. set_items() rebuilds the rows
    (cursor positioned silently, the host owns it); set_payload() repaints
    the card alone — a cursor move never rebuilds the list."""

    def __init__(self, parent: Optional[QWidget] = None, *,
                 on_cursor: Optional[Callable[[int], None]] = None,
                 on_activate: Optional[Callable[[Any], None]] = None,
                 detail_budget_rows: int = 10,
                 detail_above: bool = True):   # payload card ABOVE the rows (glance-first)
        super().__init__(parent)
        self._items: List[Item] = []
        self.picker = PickerList(self, on_cursor=on_cursor, on_activate=on_activate,
                                 detail_budget_rows=detail_budget_rows,
                                 detail_above=detail_above)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.picker, 1)

    def set_items(self, items: Sequence[Item], cursor: Optional[int] = None,
                  header: Optional[str] = None,
                  empty_note: str = "(no pending proposals)") -> None:
        """Rebuild the listing from items (an optional header row above; an
        empty listing paints the note instead of nothing)."""
        self._items = list(items)
        rows: List[Row] = []
        if header:
            rows.append({"kind": "header", "spans": [(header, "bold")]})
        rows.extend(worklist_row(it) for it in self._items)
        if not self._items:
            rows.append({"kind": "note", "spans": [("  " + empty_note, "dim")]})
        self.picker.set_rows(rows, cursor=cursor)

    def items(self) -> List[Item]:
        return list(self._items)

    def current_item(self) -> Optional[Item]:
        """The cursor row's item (None on an empty listing)."""
        i = self.picker.cursor
        return self._items[i] if 0 <= i < len(self._items) else None

    @property
    def cursor(self) -> int:
        return self.picker.cursor

    def count(self) -> int:
        return self.picker.count()

    def current_key(self) -> Any:
        return self.picker.current_key()

    def set_cursor(self, i: int) -> None:
        self.picker.set_cursor(i)

    def move(self, delta: int) -> None:
        self.picker.move(delta)

    def activate(self) -> None:
        self.picker.activate()

    def set_payload(self, lines: Optional[Sequence[Sequence[Span]]]) -> None:
        """Paint the host's payload card (span lines) under the list."""
        self.picker.set_detail(lines)

    def plain_text(self) -> str:
        return self.picker.plain_text()

    def restyle(self) -> None:
        self.picker.restyle()


class VerdictStrip(QLabel):
    """The derived-verdict status strip: one line per tier, each verdict
    painted by role (accepted ok · edited info · relabeled meta · rejected
    danger · unaccepted/missed warn · unvisited dim), plus the lane
    watermark and any extra text the host appends."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.setFont(make_font(kind="mono"))
        self._plain = ""
        self.restyle()

    def set_verdicts(self, tier1: Optional[Dict[str, int]],
                     tier2: Optional[Dict[str, int]] = None,
                     watermark: Optional[str] = None,
                     extra: str = "") -> None:
        """Paint the counts. A tier whose counts are all zero is left out;
        watermark is a preformatted text ("299.7s" / "none")."""
        t = current_theme()
        parts_html: List[str] = []
        parts_plain: List[str] = []
        for label, counts in (("tier-1", tier1), ("tier-2", tier2)):
            if not counts or not any(int(v or 0) for v in counts.values()):
                continue
            cells_html = []
            cells_plain = []
            for k, v in counts.items():
                color = state_color(VERDICT_ROLES.get(k, "content"), t)
                cells_plain.append(f"{k} {v}")
                cells_html.append(
                    "<span style='color:%s'>%s %s</span>"
                    % (color.name() if color is not None else t["content"],
                       _html.escape(str(k)), int(v or 0)))
            parts_plain.append(f"{label}: " + " · ".join(cells_plain))
            parts_html.append(f"{label}: " + " · ".join(cells_html))
        if watermark is not None:
            parts_plain.append(f"watermark {watermark}")
            parts_html.append("watermark <span style='color:%s'>%s</span>"
                              % (t["meta"], _html.escape(str(watermark))))
        if extra:
            parts_plain.append(extra)
            parts_html.append(_html.escape(extra))
        self._plain = "  |  ".join(parts_plain)
        self.setText("<span style='color:%s'>%s</span>"
                     % (t["content-dim"], "  |  ".join(parts_html) or "&nbsp;"))

    def plain_text(self) -> str:
        return self._plain

    def restyle(self) -> None:
        t = current_theme()
        self.setStyleSheet("QLabel { background: %s; border: 1px solid %s; padding: 2px 4px; }"
                           % (t["surface"], t["border"]))
        self.setFont(make_font(kind="mono"))


class ProvenancePane(QTextBrowser):
    """Key/value provenance — a two-column table of whatever the lane's
    manifest carries (set id, proposer kind:name, model, pack digest, window,
    session actor). Values are escaped; keys paint dim."""

    def __init__(self, parent: Optional[QWidget] = None, *, budget_rows: int = 6):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFont(make_font(kind="mono"))
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._budget = max(1, int(budget_rows))
        self._entries: List[Tuple[str, str]] = []
        self.restyle()
        self.set_entries([])

    def set_entries(self, entries: Sequence[Tuple[str, Any]]) -> None:
        self._entries = [(str(k), "" if v is None else str(v)) for k, v in entries]
        t = current_theme()
        if not self._entries:
            self.setHtml("<span style='color:%s'>(no provenance)</span>" % t["content-dim"])
        else:
            rows = "".join(
                "<tr><td style='color:%s;padding-right:8px'>%s</td><td style='color:%s'>%s</td></tr>"
                % (t["content-dim"], _html.escape(k), t["content"], _html.escape(v))
                for k, v in self._entries)
            self.setHtml("<table cellspacing='0' cellpadding='0'>%s</table>" % rows)
        fm = self.fontMetrics()
        self.setFixedHeight(fm.lineSpacing() * min(self._budget, max(1, len(self._entries))) + 10)

    def entries(self) -> List[Tuple[str, str]]:
        return list(self._entries)

    def plain_text(self) -> str:
        return "\n".join(f"{k}: {v}" for k, v in self._entries)

    def restyle(self) -> None:
        t = current_theme()
        self.setStyleSheet("QTextBrowser { background: %s; border: 1px solid %s; color: %s; }"
                           % (t["surface"], t["border"], t["content"]))
        self.setFont(make_font(kind="mono"))


class HitlPanel(QWidget):
    """The composed confirm panel: worklist (stretch) over the verdict strip
    over the provenance pane. Hosts toggle it per lane and paint through the
    three members; it owns no keys and no domain logic."""

    def __init__(self, parent: Optional[QWidget] = None, *,
                 on_cursor: Optional[Callable[[int], None]] = None,
                 on_activate: Optional[Callable[[Any], None]] = None,
                 detail_budget_rows: int = 10,
                 provenance_rows: int = 6,
                 detail_above: bool = True):
        super().__init__(parent)
        self.worklist = ProposalWorklist(self, on_cursor=on_cursor, on_activate=on_activate,
                                         detail_budget_rows=detail_budget_rows,
                                         detail_above=detail_above)
        self.verdicts = VerdictStrip(self)
        self.provenance = ProvenancePane(self, budget_rows=provenance_rows)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        lay.addWidget(self.worklist, 1)
        lay.addWidget(self.verdicts)
        lay.addWidget(self.provenance)

    def restyle(self) -> None:
        self.worklist.restyle()
        self.verdicts.restyle()
        self.provenance.restyle()
