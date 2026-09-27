"""The gallery SEED: every component class under any design system + mode
(ruling abb6360d — the gallery is the acceptance surface; this is the
handoff bundle's demo ported as the kit gallery's first form, the full
gallery is work item f12ed444). The gallery window is itself a SHELL
INSTANCE (ruling 2bae2cc1 / d1e3043e): its frame, title bar, menus (derived
from its keymap + the Theme menu), status strip and job seat are the
shell's — so the window IS the frame demo.

    python -m cjm_substrate_qt_kit.gallery [--system classical|netrunner|<path>] [--mode <mode>]
                                           [--decorations client|system]

Tabs: Controls / Data / Cards (the shared component classes), Kit (the kit's
own chrome — picker list, verdict strip, provenance, status strip — proving
restyle-on-signal), Shell (the modal frame, the prompts, the job seat, the
decorations toggle), and a system's own page when its package defines
`gallery_page(theme)` (Netrunner's panels). The Theme menu switches system,
mode and decorations live; every choice persists through `prefs`."""

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QGridLayout, QHBoxLayout,
                               QLineEdit, QProgressBar, QRadioButton, QScrollArea, QSlider,
                               QSpinBox, QTableWidget, QTableWidgetItem, QTabWidget, QTextEdit,
                               QToolBar, QTreeView, QVBoxLayout, QWidget)

from .hitl import HitlPanel
from .modal import Confirm
from .readingpane import ReadingPane
from .shell import AppShell
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


class Gallery(AppShell):
    def __init__(self, theme: Theme, decorations: Optional[str] = None):
        super().__init__("kit gallery", seat="gallery", decorations=decorations)
        self.theme = theme
        self.resize(1120, 780)
        self._pool: Optional[ThreadPoolExecutor] = None
        self.tabs = QTabWidget(self.frame)
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self._scroll(self._controls()), "Controls")
        self.tabs.addTab(self._scroll(self._data()), "Data")
        self.tabs.addTab(self._scroll(self._cards()), "Cards")
        self.tabs.addTab(self._scroll(self._kit()), "Kit")
        self.tabs.addTab(self._scroll(self._shell()), "Shell")
        self._system_tab: Optional[int] = None
        self.add_stage("gallery", self.tabs)
        self._chrome()
        on_change(self._on_theme)
        self._on_theme(theme)

    # chrome
    def _chrome(self):
        add = self.keymap.add
        self.acts = {}
        for verb, label, key, icon in (("new", "New", "Ctrl+N", "file-text"),
                                       ("open", "Open…", "Ctrl+O", "folder-open"),
                                       ("save", "Save", "Ctrl+S", "save")):
            self.acts[verb] = (add(verb, label, key, lambda v=verb: self.strip.set_readout(f"{v}: a demo verb"),
                                   group="File"), icon)
        add("quit", "Quit", "Ctrl+Q", self.close, group="File")
        add("dialog", "Open a dialog", "Ctrl+D", self._dialog, group="Shell")
        add("prompt", "Ask for text", "Ctrl+T", self._prompt, group="Shell")
        add("job", "Run a 3 s job", "Ctrl+J", self._job, group="Shell")
        add("decorations", "Toggle decorations", "Ctrl+Shift+D", self._toggle_decorations, group="Shell")
        self.finish_keys()
        tb = QToolBar("Main", self.frame)
        tb.setMovable(False)
        for verb in ("new", "open", "save"):
            tb.addAction(self.acts[verb][0])
        tb.addSeparator()
        self.mode_act = QAction("Mode", self, triggered=self.next_mode)
        tb.addAction(self.mode_act)
        self.frame.chrome.addWidget(tb)

    def _on_theme(self, t: Theme):
        self.setWindowTitle(f"{t.vars['name']} · {t.mode} — kit gallery")
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
        self.strip.set_chip("decorations", self.decorations)
        self.strip.set_hints("Ctrl+D dialog · Ctrl+T prompt · Ctrl+J job · Ctrl+Shift+M mode · ? keys")

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
        self.reading = ReadingPane()
        self.reading.setMinimumHeight(300)
        self.reading.setMarkdown(
            "# The reading pane\n\nMarkdown under the live system: headings in the heading face, "
            "`code` in the mono slot, [a link](graph://gallery) in accent — tab cycles links, "
            "enter opens.\n\n## A second level\n\n```\nfenced code keeps the mono slot\n```\n")
        v.addWidget(section("Reading pane (re-parsed on every switch)", self.reading))
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
        demo_strip = StatusStrip()
        demo_strip.set_chip("source", "Show 62 · 4466 segments")
        demo_strip.set_readout("accepted 3 proposals", role="ok")
        demo_strip.set_hints("j/k move · enter accept · ? keys")
        v.addWidget(section("Status strip (a second instance; the window's own is below)", demo_strip))
        v.addStretch(1)
        return page

    def _shell(self) -> QWidget:
        """The shell surfaces (rulings 2bae2cc1 + d1e3043e): the window is the
        frame demo; the buttons open the kit modal frame's dialogs, put a job
        in the seat and flip the decorations fallback."""
        page = QWidget()
        v = QVBoxLayout(page)
        v.setSpacing(28)
        v.addWidget(text("Shell", "h2"))
        v.addWidget(text("This window is the frame: drag the title bar, double-click it to maximize, "
                         "grab an edge to resize. The menus derive from the keymap; the Theme menu "
                         "switches system, mode and decorations live.", "dialog-body"))
        v.addWidget(section("Modal frame",
                            row(button("Open dialog", "primary", ), button("Ask for text"),
                                button("Keyboard hints", "ghost"))))
        btns = page.findChildren(type(button("")))
        btns[-3].clicked.connect(self._dialog)
        btns[-2].clicked.connect(self._prompt)
        btns[-1].clicked.connect(self.hints_overlay.toggle)
        job_btn = button("Run a 3 s job", "primary")
        job_btn.clicked.connect(self._job)
        v.addWidget(section("Job seat", row(job_btn)))
        deco_btn = button("Toggle decorations (shell frame ↔ window manager)")
        deco_btn.clicked.connect(self._toggle_decorations)
        v.addWidget(section("Decorations fallback", row(deco_btn)))
        v.addStretch(1)
        return page

    # shell verbs
    def _dialog(self):
        d = Confirm(self, "Unsubscribe",
                    "Leave the list? You will stop receiving the weekly letter. Past issues stay in the archive.",
                    ok="Unsubscribe", cancel="Cancel")
        d.exec_centered()
        self.strip.set_readout("unsubscribed" if d.answer() else "kept the subscription")

    def _prompt(self):
        text_ = self.prompt_text("Search", "literal term:", placeholder="a needle")
        self.strip.set_readout(f"searched for {text_!r}" if text_ else "search cancelled")

    def _job(self):
        if self._pool is None:
            self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="gallery-job")
        self.run_job("demo job", self._pool.submit(time.sleep, 3.0), done_text="demo job landed")

    def _toggle_decorations(self):
        self.set_decorations("system" if self.client_decorations else "client", persist=True)
        self.strip.set_chip("decorations", self.decorations)


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
    ap.add_argument("--decorations", default=None, choices=("client", "system"),
                    help="the shell's frame (client, default) or the window manager's (system)")
    ap.add_argument("--persist", action="store_true", help="write the launch choice to the prefs file")
    a = ap.parse_args(argv)
    app = QApplication.instance() or QApplication(sys.argv[:1])
    theme = apply_theme(app, a.system, a.mode, persist=a.persist)
    win = Gallery(theme, decorations=a.decorations)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
