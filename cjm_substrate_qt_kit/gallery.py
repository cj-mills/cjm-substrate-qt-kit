"""The gallery SEED: every component class under any design system + mode
(ruling abb6360d — the gallery is the acceptance surface; this is the
handoff bundle's demo ported as the kit gallery's first form, the full
gallery is work item f12ed444).

    python -m cjm_substrate_qt_kit.gallery [--system classical|netrunner|<path>] [--mode <mode>]

Tabs: Controls / Data / Cards (the shared component classes), Kit (the kit's
own chrome — picker list, verdict strip, provenance, status strip — proving
restyle-on-signal), and a system's own page when its package defines
`gallery_page(theme)` (Netrunner's panels). The View menu switches system
and mode live; the choice persists through `prefs` when --persist is given."""

import argparse
import sys
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                               QGridLayout, QHBoxLayout, QLineEdit, QMainWindow, QProgressBar,
                               QRadioButton, QScrollArea, QSlider, QSpinBox, QTableWidget,
                               QTableWidgetItem, QTabWidget, QTextEdit, QTreeView, QVBoxLayout,
                               QWidget)

from . import systems
from .hitl import HitlPanel
from .statusstrip import StatusStrip
from .theme import apply_theme, on_change, Theme
from .widgets import button, Card, hr, Segmented, tag, text


def section(title: str, *rows) -> QWidget:
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(14)
    v.addWidget(text(title, "h4"))
    for r in rows:
        v.addWidget(r) if isinstance(r, QWidget) else v.addLayout(r)
    return w


def row(*ws, stretch=True) -> QHBoxLayout:
    h = QHBoxLayout()
    h.setSpacing(9)
    for w in ws:
        h.addWidget(w)
    if stretch:
        h.addStretch(1)
    return h


def field(label: str, w: QWidget) -> QVBoxLayout:
    v = QVBoxLayout()
    v.setSpacing(5)
    v.addWidget(text(label, "label"))
    v.addWidget(w)
    return v


class Gallery(QMainWindow):
    def __init__(self, theme: Theme, persist: bool = False):
        super().__init__()
        self.theme = theme
        self.persist = persist
        self.resize(1120, 780)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self._scroll(self._controls()), "Controls")
        self.tabs.addTab(self._scroll(self._data()), "Data")
        self.tabs.addTab(self._scroll(self._cards()), "Cards")
        self.tabs.addTab(self._scroll(self._kit()), "Kit")
        self._system_tab: Optional[int] = None
        self.setCentralWidget(self.tabs)
        self._menus()
        on_change(self._on_theme)
        self._on_theme(theme)

    # chrome
    def _menus(self):
        mb = self.menuBar()
        f = mb.addMenu("&File")
        self.acts = {}
        for name, icon in [("New", "file-text"), ("Open…", "folder-open"), ("Save", "save")]:
            self.acts[name] = (f.addAction(name), icon)
        f.addSeparator()
        f.addAction("Quit", self.close)
        v = mb.addMenu("&View")
        self.system_menu = v.addMenu("Design system")
        self.system_group = QActionGroup(self)
        for slug in systems.available():
            act = QAction(slug, self, checkable=True)
            act.triggered.connect(lambda _c=False, s=slug: self.theme.set_system(s, persist=self.persist))
            self.system_group.addAction(act)
            self.system_menu.addAction(act)
        self.mode_menu = v.addMenu("Mode")
        v.addAction("Next mode", self.theme.toggle)
        mb.addMenu("&Help").addAction("About", self._dialog)
        tb = self.addToolBar("Main")
        tb.setMovable(False)
        for name in ("New", "Open…", "Save"):
            tb.addAction(self.acts[name][0])
        tb.addSeparator()
        self.mode_act = QAction("Mode", self, triggered=self.theme.toggle)
        tb.addAction(self.mode_act)

    def _rebuild_mode_menu(self, t: Theme):
        self.mode_menu.clear()
        group = QActionGroup(self)
        auto = QAction("auto (follow the OS)", self, checkable=True)
        auto.setEnabled(bool(t.tokens.get("scheme")))
        auto.setChecked(t.requested == "auto")
        auto.triggered.connect(lambda _c=False: self.theme.set_mode("auto", persist=self.persist))
        group.addAction(auto)
        self.mode_menu.addAction(auto)
        self.mode_menu.addSeparator()
        for m in t.modes:
            act = QAction(m, self, checkable=True)
            act.setChecked(t.requested != "auto" and m == t.mode)
            act.triggered.connect(lambda _c=False, mm=m: self.theme.set_mode(mm, persist=self.persist))
            group.addAction(act)
            self.mode_menu.addAction(act)

    def _on_theme(self, t: Theme):
        self.setWindowTitle(f"{t.vars['name']} · {t.mode} — kit gallery")
        for act in self.system_group.actions():
            act.setChecked(act.text() == t.system)
        self._rebuild_mode_menu(t)
        for act, icon in self.acts.values():
            act.setIcon(t.icon(icon))
        self.mode_act.setIcon(t.icon("sun" if t.mode == "dark" else "moon"))
        self.search_btn.setIcon(t.icon("search", "accent"))
        # the system's own page (Netrunner's panels), swapped per system
        if self._system_tab is not None:
            self.tabs.removeTab(self._system_tab)
            self._system_tab = None
        page = _system_page(t)
        if page is not None:
            self._system_tab = self.tabs.addTab(self._scroll(page), t.vars["name"])
        self.strip.set_chip("system", f"{t.system}:{t.mode}")

    def _scroll(self, w: QWidget) -> QScrollArea:
        s = QScrollArea()
        s.setWidgetResizable(True)
        s.setFrameShape(QScrollArea.Shape.NoFrame)
        w.layout().setContentsMargins(37, 28, 37, 37)
        s.setWidget(w)
        return s

    # pages
    def _controls(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setSpacing(28)
        v.addWidget(text("Controls", "h2"))
        dis = button("Disabled", "primary")
        dis.setEnabled(False)
        self.search_btn = button("", "icon")
        v.addWidget(section("Buttons",
                            row(button("Subscribe", "primary"), button("Secondary"), button("Read more", "ghost"),
                                self.search_btn, dis),
                            row(tag("Essay"), tag("Archive", "neutral"), tag("New", "outline"))))
        v.addWidget(hr())
        combo = QComboBox()
        combo.addItems(["Monthly", "Quarterly", "Annual"])
        spin = QSpinBox()
        spin.setRange(1, 99)
        spin.setValue(12)
        email = QLineEdit(placeholderText="you@example.com")
        notes = QTextEdit(placeholderText="A note for the editor")
        notes.setFixedHeight(90)
        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(14)
        grid.addLayout(field("Email", email), 0, 0)
        grid.addLayout(field("Frequency", combo), 0, 1)
        grid.addLayout(field("Issues", spin), 0, 2)
        grid.addLayout(field("Notes", notes), 1, 0, 1, 3)
        v.addWidget(section("Fields", grid))
        cb2 = QCheckBox("Partial")
        cb2.setTristate(True)
        cb2.setCheckState(Qt.CheckState.PartiallyChecked)
        r1, r2 = QRadioButton("Print"), QRadioButton("Digital")
        r1.setChecked(True)
        v.addWidget(section("Choices",
                            row(QCheckBox("Weekly digest", checked=True), cb2, r1, r2),
                            row(Segmented(["Day", "Week", "Month"], 1))))
        v.addWidget(hr())
        sl = QSlider(Qt.Orientation.Horizontal, value=40)
        pb = QProgressBar(value=62, textVisible=False)
        sl.valueChanged.connect(pb.setValue)
        v.addWidget(section("Range", sl, pb))
        states = QHBoxLayout()
        for role in ("danger", "warn", "ok", "info", "meta", "note", "dim"):
            lb = text(role, role, False)
            states.addWidget(lb)
        states.addStretch(1)
        v.addWidget(section("State channel (role property)", states))
        v.addStretch(1)
        return page

    def _data(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setSpacing(28)
        v.addWidget(text("Data", "h2"))
        rows = [("Meditations", "Marcus Aurelius", "180"), ("The Prince", "Machiavelli", "1532"),
                ("Essays", "Montaigne", "1580"), ("Leviathan", "Hobbes", "1651"), ("Ethics", "Spinoza", "1677")]
        t = QTableWidget(len(rows), 3)
        t.setHorizontalHeaderLabels(["TITLE", "AUTHOR", "YEAR"])
        t.verticalHeader().hide()
        t.setShowGrid(False)
        t.horizontalHeader().setStretchLastSection(True)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        for r, vals in enumerate(rows):
            for c, val in enumerate(vals):
                it = QTableWidgetItem(val)
                if c == 2:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                t.setItem(r, c, it)
        t.setColumnWidth(0, 260)
        t.setColumnWidth(1, 260)
        t.setMinimumHeight(260)
        v.addWidget(section("Table", t))
        m = QStandardItemModel()
        m.setHorizontalHeaderLabels(["SECTION"])
        for part, chs in [("Book I", ["Of the Gods", "Of Fortune"]), ("Book II", ["Of Virtue"])]:
            p = QStandardItem(part)
            for c in chs:
                p.appendRow(QStandardItem(c))
            m.appendRow(p)
        tree = QTreeView()
        tree.setModel(m)
        tree.expandAll()
        tree.setMinimumHeight(200)
        v.addWidget(section("Tree", tree))
        v.addStretch(1)
        return page

    def _cards(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setSpacing(28)
        v.addWidget(text("Cards", "h2"))
        g = QGridLayout()
        g.setSpacing(18)
        specs = [("Essay", "On the shortness of life", None), ("Letter", "To a young poet", "sm"),
                 ("Review", "The art of the footnote", "md"), ("Archive", "Marginalia, 1790–1820", "lg")]
        for i, (k, ttl, elev) in enumerate(specs):
            g.addWidget(Card(k, ttl, "Hairlines carry the structure; the page stays quiet and the type does the work.",
                             f"Elevation: {elev or 'none'}", elevation=elev, theme=self.theme), i // 2, i % 2)
        v.addLayout(g)
        open_btn = button("Open dialog", "primary")
        open_btn.clicked.connect(self._dialog)
        v.addLayout(row(open_btn))
        v.addStretch(1)
        return page

    def _kit(self) -> QWidget:
        """The kit's own chrome under the live theme — the restyle-on-signal
        proof: switch system or mode and every painter here follows."""
        page = QWidget()
        v = QVBoxLayout(page)
        v.setSpacing(28)
        v.addWidget(text("Kit chrome", "h2"))
        self.hitl = HitlPanel()
        self.hitl.setMinimumHeight(360)
        items = [{"key": i, "tier": 1 + (i % 2), "category": ["filler", "aside", "quote"][i % 3],
                  "start": 12.0 * i, "end": 12.0 * i + 4.5, "confidence": 0.5 + 0.1 * (i % 5),
                  "quote": "so what we are going to do here is", "index": i,
                  "state": "pending" if i % 4 else "accepted"} for i in range(9)]
        self.hitl.worklist.set_items(items, cursor=0, header="PROPOSALS — gallery spine")
        self.hitl.worklist.set_payload([[("Why: ", "bold"), ("a filler run of 4.5 s", "warn")],
                                        [("Speaker 2 · ", "dim"), ("segment 3", "meta")]])
        self.hitl.verdicts.set_verdicts({"accepted": 9, "edited": 2, "rejected": 1, "unvisited": 3},
                                        {"accepted": 1, "unaccepted": 2}, watermark="935.0s",
                                        extra="22 live strata")
        self.hitl.provenance.set_entries([("set", "ps-2026-09-25"), ("proposer", "model:qwen3"),
                                          ("window", "0–3600 s")])
        v.addWidget(section("HITL panel (picker list · verdict strip · provenance)", self.hitl))
        self.strip = StatusStrip()
        self.strip.set_chip("source", "Show 62 · 4466 segments")
        self.strip.set_readout("accepted 3 proposals", role="ok")
        self.strip.set_hints("j/k move · enter accept · ? keys")
        v.addWidget(section("Status strip", self.strip))
        v.addStretch(1)
        return page

    def _dialog(self):
        d = QDialog(self)
        d.setWindowTitle("Unsubscribe")
        d.setMinimumWidth(440)
        lay = QVBoxLayout(d)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(14)
        lay.addWidget(text("Leave the list?", "h4"))
        lay.addWidget(text("You will stop receiving the weekly letter. Past issues stay in the archive.", "dialog-body"))
        bb = QDialogButtonBox()
        bb.addButton(button("Cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        bb.addButton(button("Unsubscribe", "primary"), QDialogButtonBox.ButtonRole.AcceptRole)
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        lay.addWidget(bb)
        d.exec()


def _system_page(theme: Theme) -> Optional[QWidget]:
    """A vendored system's own gallery page, when its package defines one."""
    import importlib
    try:
        mod = importlib.import_module(f"cjm_substrate_qt_kit.systems.{theme.system}.widgets")
    except ModuleNotFoundError:
        return None
    hook = getattr(mod, "gallery_page", None)
    return hook(theme) if hook else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m cjm_substrate_qt_kit.gallery")
    ap.add_argument("--system", default=None, help="a vendored slug or a tokens.json path")
    ap.add_argument("--mode", default=None, help="a mode of the system, or auto")
    ap.add_argument("--persist", action="store_true", help="write the choice to the prefs file")
    a = ap.parse_args(argv)
    app = QApplication.instance() or QApplication(sys.argv[:1])
    theme = apply_theme(app, a.system, a.mode, persist=a.persist)
    win = Gallery(theme, persist=a.persist)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
