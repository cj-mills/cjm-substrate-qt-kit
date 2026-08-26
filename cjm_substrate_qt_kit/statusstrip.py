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

from typing import Dict, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget


class StatusStrip(QWidget):
    """Two-row footer: chips + readout + transient above, hint line below
    (hints=False builds a single-row strip for apps that keep their hint
    line elsewhere)."""

    def __init__(self, parent: Optional[QWidget] = None, hints: bool = True):
        super().__init__(parent)
        self._chips: Dict[str, QLabel] = {}
        self._chips_box = QHBoxLayout()
        self._chips_box.setContentsMargins(0, 0, 0, 0)
        self._chips_box.setSpacing(12)
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
        self.transient = QLabel("", self)
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
        layout.addWidget(self.context)
        if hints:
            self.hints = QLabel("", self)
            self._set_role(self.hints, "content-dim")
            layout.addWidget(self.hints)

    def set_chip(self, name: str, text: str, role: Optional[str] = None) -> None:
        """Create or update a permanent chip; chips keep declaration order."""
        chip = self._chips.get(name)
        if chip is None:
            chip = QLabel("", self)
            self._chips[name] = chip
            self._chips_box.addWidget(chip)
        chip.setText(text)
        self._set_role(chip, role)
        self._reflow()

    def remove_chip(self, name: str) -> None:
        chip = self._chips.pop(name, None)
        if chip is not None:
            self._chips_box.removeWidget(chip)
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

    def _reflow(self) -> None:
        """Responsive readout drop (drive verdict 2026-08-25): when the
        chips can no longer share the row with the readout's full text, the
        readout moves to its OWN full-width row underneath — word-wrapped
        and left-aligned, nothing truncated. It returns inline (right-
        aligned, clipping as last resort) once space allows. This is the
        R3 reflow idea from the layout registries applied to one slot."""
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

    def _set_role(self, label: QLabel, role: Optional[str]) -> None:
        """Land a state-channel role (theme QSS colors it); re-polish so a
        role CHANGE repaints on an already-styled label."""
        label.setProperty("role", role or "")
        label.style().unpolish(label)
        label.style().polish(label)
