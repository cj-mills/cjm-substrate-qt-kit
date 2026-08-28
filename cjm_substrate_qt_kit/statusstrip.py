"""StatusStrip: the footer's slot model (DEC 2a42c028).

The footer decomposition's always-on half, replacing the QStatusBar
message channel the apps inherited from the Textual era. Three message
classes, split by lifetime: permanent identity/position CHIPS (never
evicted by anything), one PERSISTENT READOUT slot (the last action's
result, persisting until superseded — replay span feedback's home), and
one TRANSIENT slot that expires on its own timer (launch notices and
kin). A second row carries the contextual HINT LINE (pinned verbs +
"? keys", fed by keyhints.hint_line). The strip is a plain widget — it
never touches QStatusBar, so menu-hover QStatusTipEvents cannot evict
anything (the workbench hint-loss root cause)."""

import re
from typing import Dict, List, Optional

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget


class StatusStrip(QWidget):
    """Two-row footer: chips + readout + transient above, hint line below
    (hints=False builds a single-row strip for apps that keep their hint
    line elsewhere).

    Every label is mouse-SELECTABLE (copy a segment position or session id
    straight out of the footer — walkthrough call-out 04519af8; keyboard
    focus never lands on a label, so the owner's bare-letter keys keep
    working). The chip row is RESPONSIVE (call-out e26add76): an overlong
    plain-text chip ELIDES to chip_max_width with its full text in the
    tooltip, and chips that no longer fit the row FLOW onto further rows
    underneath, so the strip's minimum width is its widest chip — never
    the sum of the row, which used to pin the whole window's minimum."""

    def __init__(self, parent: Optional[QWidget] = None, hints: bool = True,
                 chip_max_width: int = 320):
        super().__init__(parent)
        self._chips: Dict[str, QLabel] = {}
        self._chip_text: Dict[str, str] = {}   # full text behind an elided chip
        self._chip_max_width = chip_max_width
        self._chips_box = QHBoxLayout()
        self._chips_box.setContentsMargins(0, 0, 0, 0)
        self._chips_box.setSpacing(12)
        # Chip rows: row 0 is _chips_box (sharing the readout row); rows
        # 1.. are minted on demand by the flow and sit between the readout
        # row and the readout's overflow row.
        self._chip_rows: List[QHBoxLayout] = [self._chips_box]
        self._chip_layout: List[List[str]] = [[]]
        self.readout = QLabel("", self)
        # The readout right-aligns in the LEFTOVER space and clips when the
        # chips crowd it (Ignored policy: it never forces the window wider,
        # and an 18px gap keeps it visually apart from the last chip —
        # drive verdict 2026-08-25).
        self.readout.setAlignment(Qt.AlignmentFlag.AlignRight
                                  | Qt.AlignmentFlag.AlignVCenter)
        policy = self.readout.sizePolicy()
        policy.setHorizontalPolicy(QSizePolicy.Policy.Ignored)
        self.readout.setSizePolicy(policy)
        self._selectable(self.readout)
        self.transient = QLabel("", self)
        self._selectable(self.transient)
        self.hints: Optional[QLabel] = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._expire)
        self._readout_inline = True
        self._row = QHBoxLayout()
        self._row.setContentsMargins(0, 0, 0, 0)
        self._row.addLayout(self._chips_box)
        self._row.addSpacing(18)
        self._row.addWidget(self.readout, 1)
        self._row.addSpacing(12)
        self._row.addWidget(self.transient)
        # The readout's overflow row: empty until _reflow drops the readout
        # under the chips (drive verdict 2026-08-25 — reflow over truncation).
        self._readout_row = QHBoxLayout()
        self._readout_row.setContentsMargins(0, 0, 0, 0)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(1)
        layout.addLayout(self._row)
        layout.addLayout(self._readout_row)
        self.context = QLabel("", self)
        self.context.setWordWrap(True)
        self.context.setVisible(False)
        # Context renders as RICH TEXT so pickable tokens can wear the
        # overlay's key-cap grammar (keyhints.keycaps); callers escape any
        # user-derived content themselves.
        self.context.setTextFormat(Qt.TextFormat.RichText)
        self._selectable(self.context)
        layout.addWidget(self.context)
        if hints:
            self.hints = QLabel("", self)
            self._set_role(self.hints, "content-dim")
            self._selectable(self.hints)
            layout.addWidget(self.hints)

    def set_chip(self, name: str, text: str, role: Optional[str] = None) -> None:
        """Create or update a permanent chip; chips keep declaration order.
        Plain text wider than chip_max_width elides (full text in the
        tooltip and chip_text); rich-text chips paint as given."""
        chip = self._chips.get(name)
        if chip is None:
            chip = QLabel("", self)
            self._selectable(chip)
            self._chips[name] = chip
            self._chips_box.addWidget(chip)
        self._chip_text[name] = text
        shown = self._elide(chip, text)
        chip.setText(shown)
        chip.setToolTip(text if shown != text else "")
        self._set_role(chip, role)
        self._reflow()

    def chip_text(self, name: str) -> str:
        """A chip's FULL text (what an elided chip stands for)."""
        return self._chip_text.get(name, "")

    def chip_rows(self) -> List[List[str]]:
        """The current flow: chip names per row (row 0 shares the readout
        row) — the inspectable form of the responsive chip layout."""
        return [list(names) for names in self._chip_layout]

    def remove_chip(self, name: str) -> None:
        chip = self._chips.pop(name, None)
        self._chip_text.pop(name, None)
        if chip is not None:
            for row in self._chip_rows:
                row.removeWidget(chip)
            chip.deleteLater()
            self._reflow()

    def set_chips(self, chips) -> None:
        """Reconcile the chip row to exactly this [(name, text)] list (an
        optional third element is the role). A changed name set rebuilds the
        row so chip ORDER always follows the list — lane switches must not
        leave stale chips or append their extras after the tail chips."""
        names = [c[0] for c in chips]
        if names != list(self._chips):
            for name in list(self._chips):
                self.remove_chip(name)
        for chip in chips:
            self.set_chip(chip[0], chip[1], chip[2] if len(chip) > 2 else None)

    def set_readout(self, text: str, role: Optional[str] = None) -> None:
        """The persistent-readout class: stays until the next readout
        supersedes it (or clear_readout)."""
        self.readout.setText(text)
        self._set_role(self.readout, role)
        self._reflow()

    def clear_readout(self) -> None:
        self.readout.setText("")
        self._reflow()

    def set_context(self, text: str, role: Optional[str] = None) -> None:
        """The mode-scoped CONTEXT slot (drive verdict 2026-08-25): a
        full-width, word-wrapped row of its own for variable-length helper
        DATA — pick menus, vocabularies — that the shared readout row
        cannot show. Hidden entirely when empty; the owner derives and
        re-sets it per frame like the chips."""
        self.context.setText(text)
        self.context.setVisible(bool(text))
        self._set_role(self.context, role)

    def clear_context(self) -> None:
        self.set_context("")

    def show_transient(self, text: str, msecs: int = 4000,
                       role: Optional[str] = None) -> None:
        """The transient class: expires on its own timer, never touching
        chips or readout. A new transient restarts the clock."""
        self.transient.setText(text)
        self._set_role(self.transient, role)
        self._timer.start(msecs)
        self._reflow()

    def set_hints(self, text: str) -> None:
        """The contextual hint line (no-op on a hints=False strip)."""
        if self.hints is not None:
            self.hints.setText(text)

    def _expire(self) -> None:
        self.transient.setText("")
        self._reflow()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._reflow()

    def minimumSizeHint(self) -> QSize:
        """The strip's minimum WIDTH is its widest chip (bounded by the
        elision), not the chip row's sum: the layout's own minimum would
        pin the window at the full single-row width and the flow could
        never engage (call-out e26add76). Height stays the layout's — it
        already counts the flowed rows."""
        base = super().minimumSizeHint()
        widest = max((c.sizeHint().width() for c in self._chips.values()),
                     default=0)
        if not widest:
            return base
        return QSize(min(base.width(), widest + 12), base.height())

    def _reflow(self) -> None:
        """Responsive layout, two moves (drive verdict 2026-08-25 + call-out
        e26add76): chips that no longer fit the row FLOW onto rows of their
        own underneath (declaration order, greedy fill), and when the
        chips can no longer share the row with the readout's full text, the
        readout moves to its OWN full-width row — word-wrapped and left-
        aligned, nothing truncated. Both return once space allows. This is
        the R3 reflow idea from the layout registries applied to the
        footer."""
        self._flow_chips()
        fm = self.readout.fontMetrics()
        needed = fm.horizontalAdvance(self.readout.text())
        chips = sum(c.sizeHint().width() for c in self._chips.values())
        chips += self._chips_box.spacing() * max(0, len(self._chips) - 1)
        transient = self.transient.sizeHint().width()
        leftover = (self.width() - 12 - chips - 18
                    - (transient + 12 if transient else 0))
        inline = not self.readout.text() or needed <= leftover
        if inline == self._readout_inline:
            return
        self._readout_inline = inline
        if inline:
            self._readout_row.removeWidget(self.readout)
            self._row.insertWidget(2, self.readout, 1)
            self.readout.setWordWrap(False)
            self.readout.setAlignment(Qt.AlignmentFlag.AlignRight
                                      | Qt.AlignmentFlag.AlignVCenter)
        else:
            self._row.removeWidget(self.readout)
            self._readout_row.addWidget(self.readout, 1)
            self.readout.setWordWrap(True)
            self.readout.setAlignment(Qt.AlignmentFlag.AlignLeft
                                      | Qt.AlignmentFlag.AlignVCenter)

    def _flow_chips(self) -> None:
        """Distribute the chips over rows for the current width: a chip
        joins the row while it fits, else opens the next row (a chip wider
        than the strip still gets a row of its own). Re-parents widgets
        only when the assignment actually changes."""
        avail = max(1, self.width() - 12)
        spacing = self._chips_box.spacing()
        wanted: List[List[str]] = [[]]
        used = 0
        for name, chip in self._chips.items():
            width = chip.sizeHint().width()
            need = width if not wanted[-1] else used + spacing + width
            if wanted[-1] and need > avail:
                wanted.append([name])
                used = width
            else:
                wanted[-1].append(name)
                used = need
        if wanted == self._chip_layout:
            return
        for row in self._chip_rows:
            for chip in self._chips.values():
                row.removeWidget(chip)
        for index, names in enumerate(wanted):
            row = self._chip_row(index)
            for name in names:
                if index == 0:
                    row.addWidget(self._chips[name])
                else:               # keep the trailing stretch last
                    row.insertWidget(row.count() - 1, self._chips[name])
        self._chip_layout = wanted
        self.updateGeometry()

    def _chip_row(self, index: int) -> QHBoxLayout:
        """Row `index` of the chip flow, minted on first use (left-packed
        by a trailing stretch) and inserted under the readout row."""
        while len(self._chip_rows) <= index:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(self._chips_box.spacing())
            row.addStretch(1)
            self.layout().insertLayout(len(self._chip_rows), row)
            self._chip_rows.append(row)
        return self._chip_rows[index]

    def _elide(self, chip: QLabel, text: str) -> str:
        """Plain text past chip_max_width elides right; rich text (the
        apps' colored span chips) is never cut — a tag split would
        corrupt it."""
        if self._chip_max_width <= 0 or re.search(r"<[A-Za-z/!]", text):
            return text
        fm = chip.fontMetrics()
        if fm.horizontalAdvance(text) <= self._chip_max_width:
            return text
        return fm.elidedText(text, Qt.TextElideMode.ElideRight,
                             self._chip_max_width)

    def _selectable(self, label: QLabel) -> None:
        """Mouse selection on, keyboard focus off: the flags alone would
        give the label ClickFocus, and a focused label would sit between
        the owner window and its key table."""
        label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def _set_role(self, label: QLabel, role: Optional[str]) -> None:
        """Land a state-channel role (theme QSS colors it); re-polish so a
        role CHANGE repaints on an already-styled label."""
        label.setProperty("role", role or "")
        label.style().unpolish(label)
        label.style().polish(label)
