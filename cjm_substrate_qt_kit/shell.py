"""The APP SHELL (ruling 2bae2cc1; the decorations ruling d1e3043e): every
Qt app in the lane is an instance of this one window.

    class MyWindow(AppShell):
        def __init__(self, session):
            super().__init__("my app", session=session, seat="myapp")
            self.add_stage("list", self.picker)
            self.keymap.add("open", "Open", "Return", self.open, group="Rows")
            self.add_session_verbs()                 # mint / title / retract
            self.finish_keys()                       # guard + hints + menus

The shell owns what every app re-implemented: the WINDOW FRAME (the
frameless, translucent host + the painted frame + the title bar —
`frame`), the stages (a QStackedWidget: one visible at a time), the
menubar DERIVED from the keymap (one menu per verb group, in declaration
order, plus the Theme menu built from the live design system — never a
hand-maintained mirror), the StatusStrip, the FindBar, the KeyHintsOverlay,
the JOB SEAT, the Future -> Signal bridge every async read and job goes
through (the paint thread never blocks: `read_async`), the kit dialogs
(`prompt_text`, `confirm`), and the SESSION verbs — key adoption at launch
(env, else the workspace pointer; an inherited key is never overwritten),
the ONE mint with confirm + boot prompt, title and retract. The keyboard
contract rides the keymap (numpad Enter answers wherever Return binds; the
text-entry guard gates bare-letter verbs off inside a field)."""

from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from PySide6.QtCore import Signal
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QApplication, QMenu, QMenuBar, QStackedWidget, QWidget

from . import sessionkey, systems
from .bridge import FutureBridge
from .findbar import FindBar
from .frame import FramedWindow, hint_system_scheme
from .jobs import Job, JobSeat
from .keyhints import KeyHintsOverlay
from .keymap import KeymapRegistry
from .modal import ask_text, confirm
from .statusstrip import StatusStrip
from .theme import current, on_change

BUSY_TEXT = "loading…"


def add_theme_menu(menubar: QMenuBar, window: "AppShell") -> QMenu:
    """The in-app theme switcher (item 812beb51): Design system + Mode radio
    groups from the live Theme's data, Next mode, and the Decorations
    fallback toggle — every choice persists through prefs. Rebuilt on the
    change signal (the mode list is the system's)."""
    menu = QMenu("Theme", menubar)
    menubar.addMenu(menu)
    t = current()
    systems_menu = QMenu("Design system", menu)
    menu.addMenu(systems_menu)
    group = QActionGroup(menu)
    for slug in systems.available():
        act = QAction(slug, menu, checkable=True)
        act.setChecked(t is not None and slug == t.system)
        act.triggered.connect(lambda _c=False, s=slug: window.set_system(s))
        group.addAction(act)
        systems_menu.addAction(act)
    modes_menu = QMenu("Mode", menu)
    menu.addMenu(modes_menu)
    mgroup = QActionGroup(menu)
    auto = QAction("auto (follow the OS)", menu, checkable=True)
    auto.setEnabled(t is not None and bool(t.tokens.get("scheme")))
    auto.setChecked(t is not None and t.requested == "auto")
    auto.triggered.connect(lambda _c=False: window.set_mode("auto"))
    mgroup.addAction(auto)
    modes_menu.addAction(auto)
    modes_menu.addSeparator()
    for m in (t.modes if t is not None else []):
        act = QAction(m, menu, checkable=True)
        act.setChecked(t.requested != "auto" and m == t.mode)
        act.triggered.connect(lambda _c=False, mm=m: window.set_mode(mm))
        mgroup.addAction(act)
        modes_menu.addAction(act)
    if window.keymap.has("theme-next"):
        menu.addAction(window.keymap.action("theme-next"))
    menu.addSeparator()
    deco = QMenu("Decorations", menu)
    menu.addMenu(deco)
    dgroup = QActionGroup(menu)
    for mode, label in (("client", "the shell's frame"), ("system", "the window manager's")):
        act = QAction(label, menu, checkable=True)
        act.setChecked(window.decorations == mode)
        act.triggered.connect(lambda _c=False, mm=mode: window.set_decorations(mm, persist=True))
        dgroup.addAction(act)
        deco.addAction(act)
    return menu


class AppShell(FramedWindow):
    session_minted = Signal(str)      # a fresh key adopted (apps open its feed)
    session_titled = Signal(str, str)  # (key, title)

    def __init__(self, title: str = "", *, session: Any = None, seat: str = "app",
                 journal_paths: Optional[Sequence[str]] = None,
                 decorations: Optional[str] = None, hints: bool = True,
                 parent: Optional[QWidget] = None):
        super().__init__(parent, decorations=decorations)
        self.session = session
        self.seat = seat
        self.journal_paths: List[str] = [str(p) for p in (
            journal_paths if journal_paths is not None
            else (getattr(session, "journal_paths", None) or []))]
        self.bridge = FutureBridge(self)
        self.keymap = KeymapRegistry(self)
        self.stack = QStackedWidget(self.frame)
        self._stages: Dict[str, QWidget] = {}
        self.findbar = FindBar(parent=self.frame)
        self.jobs = JobSeat(self.frame)
        self.strip = StatusStrip(self.frame, hints=hints)
        self.menubar = QMenuBar(self.frame)
        self.frame.chrome.addWidget(self.menubar)
        self.frame.body.addWidget(self.stack, 1)
        self.frame.foot.addWidget(self.findbar)
        self.frame.foot.addWidget(self.jobs)
        self.frame.foot.addWidget(self.strip)
        self.hints_overlay = KeyHintsOverlay(self)
        self.theme_menu: Optional[QMenu] = None
        self.menus: Dict[str, QMenu] = {}
        self._busy = 0
        self._pool: Optional[ThreadPoolExecutor] = None
        self._extra_entries: List[dict] = []
        self.jobs.job_done.connect(self._on_job_done)
        self.setWindowTitle(title)
        self.session_key, self.session_key_source = sessionkey.adopt(self.journal_paths)
        on_change(self._on_theme_shell)

    # ---- stages ------------------------------------------------------------

    def add_stage(self, name: str, widget: QWidget) -> QWidget:
        """Register a stage (one visible at a time); the first added shows."""
        self._stages[name] = widget
        self.stack.addWidget(widget)
        return widget

    def show_stage(self, name: str, focus: bool = True) -> QWidget:
        w = self._stages[name]
        self.stack.setCurrentWidget(w)
        if focus:
            w.setFocus()
        return w

    def stage(self, name: str) -> QWidget:
        return self._stages[name]

    def current_stage(self) -> Optional[str]:
        w = self.stack.currentWidget()
        for name, widget in self._stages.items():
            if widget is w:
                return name
        return None

    # ---- keys + menus --------------------------------------------------------

    def add_session_verbs(self, *, mint: Optional[str] = "Shift+S", title: Optional[str] = "T",
                          retract: Optional[str] = None, group: str = "Session") -> None:
        """The session ritual as shell verbs, at the app's chosen keys (None
        skips a verb). Retract takes the key from `retract_target()`, which
        an app overrides to name the focused session row."""
        if self.session is None:
            return
        if mint:
            self.keymap.add("mint-session", "Mint new session (start ritual)", mint,
                            self.mint_session, group=group)
        if title:
            self.keymap.add("title-session", "Title seated session (end ritual)", title,
                            self.title_session, group=group)
        if retract:
            self.keymap.add("retract-session", "Retract an empty session", retract,
                            lambda: self.retract_session(self.retract_target()), group=group)

    def _chrome_verbs(self) -> None:
        add = self.keymap.add
        if not self.keymap.has("find"):
            add("find", "Find in reading view", "Ctrl+F", self.open_find, group="View")
            add("find-next", "Find next", "F3", self.findbar.next, group="View")
            add("find-previous", "Find previous", "Shift+F3", self.findbar.previous, group="View")
        if not self.keymap.has("theme-next"):
            add("theme-next", "Next theme mode", "Ctrl+Shift+M", self.next_mode, group="View")
        if not self.keymap.has("keys"):
            add("keys", "Keyboard hints", "?", self.hints_overlay.toggle, group="View")

    def finish_keys(self, extra_entries: Iterable[dict] = ()) -> None:
        """After the app's verbs: the shell's own View verbs, the text-entry
        guard, the hints overlay's model (registry entries + the app's
        widget-scoped rows declared as data), and the derived menus."""
        self._chrome_verbs()
        self.keymap.guard_text_entry()
        self._extra_entries = list(extra_entries)
        self.hints_overlay.set_entries(self.keymap.entries() + self._extra_entries)
        self.build_menus()

    def build_menus(self) -> None:
        """One menu per keymap group in declaration order (ungrouped verbs
        under General), then the Theme menu from the live design system.
        The menus are held on the shell (`menus`) — a QMenu the bar minted
        and nobody references is collected from under its action."""
        for old in self.menus.values():
            old.deleteLater()
        self.menus = {}
        self.menubar.clear()
        entries = self.keymap.entries()
        for group in self.keymap.groups():
            menu = QMenu(group or "General", self.menubar)
            for e in entries:
                if e["group"] == group:
                    menu.addAction(self.keymap.action(e["verb"]))
            self.menubar.addMenu(menu)
            self.menus[group or "General"] = menu
        self.theme_menu = add_theme_menu(self.menubar, self)
        self.menus["Theme"] = self.theme_menu

    # ---- reading + find ------------------------------------------------------

    def reading_pane(self) -> Optional[QWidget]:
        """The pane Find applies to: the focused searchable widget, else the
        current stage when it is one."""
        app = QApplication.instance()
        for w in ((app.focusWidget() if app else None), self.stack.currentWidget()):
            if w is not None and hasattr(w, "find") and hasattr(w, "setExtraSelections"):
                return w
        return None

    def open_find(self) -> None:
        pane = self.reading_pane()
        if pane is None:
            self.strip.show_transient("find works in reading views")
            return
        self.findbar.attach(pane)
        self.findbar.open()

    # ---- theme ---------------------------------------------------------------

    def next_mode(self) -> None:
        t = current()
        if t is not None:
            t.toggle(persist=True)

    def set_mode(self, mode: str) -> None:
        t = current()
        if t is not None:
            t.set_mode(mode, persist=True)

    def set_system(self, slug: str) -> None:
        t = current()
        if t is not None:
            t.set_system(slug, persist=True)

    def _on_theme_shell(self, theme) -> None:
        if self.theme_menu is not None:
            self.build_menus()
        if not self.client_decorations:
            app = QApplication.instance()
            if app is not None:
                hint_system_scheme(app, theme)

    # ---- async reads + jobs --------------------------------------------------

    def read_async(self, future: Future, on_result: Callable[[Any], None], *,
                   on_error: Optional[Callable[[BaseException], None]] = None,
                   busy: Optional[str] = BUSY_TEXT) -> Future:
        """A read off the paint thread: the future (from `session.submit`)
        lands through the bridge; the strip shows `busy` on the readout
        while any read is in flight; a failure paints on the readout (warn)
        unless `on_error` takes it."""
        self._busy += 1
        if busy:
            self.strip.set_readout(busy)

        def done(result) -> None:
            self._settle(busy)
            on_result(result)

        def failed(e: BaseException) -> None:
            self._settle(busy)
            if on_error is not None:
                on_error(e)
            else:
                self.strip.set_readout(f"⚠ {e}", role="warn")

        return self.bridge.watch(future, done, failed)

    def _settle(self, busy: Optional[str]) -> None:
        self._busy = max(0, self._busy - 1)
        if self._busy == 0 and busy and self.strip.readout.text() == busy:
            self.strip.clear_readout()

    def call_async(self, fn: Callable[[], Any], on_result: Callable[[Any], None], **kw) -> Future:
        """A blocking callable (a session's sync facade) run on a worker
        thread, delivered like read_async — for sessions without an async
        variant of a verb."""
        if self._pool is None:
            self._pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="shell-call")
        return self.read_async(self._pool.submit(fn), on_result, **kw)

    def run_job(self, label: str, future: Future,
                on_done: Optional[Callable[[Any], None]] = None,
                on_error: Optional[Callable[[BaseException], None]] = None, *,
                on_cancel: Optional[Callable[[], None]] = None,
                done_text: Optional[str] = None) -> Job:
        """Long-running work in the JOB SEAT: a row while the future runs,
        the outcome on the readout when it lands."""
        job = self.jobs.start(label, on_cancel=on_cancel)

        def done(result) -> None:
            job.finish(done_text)
            if on_done is not None:
                on_done(result)

        def failed(e: BaseException) -> None:
            job.fail(f"⚠ {label}: {e}")
            if on_error is not None:
                on_error(e)

        self.bridge.watch(future, done, failed)
        return job

    def _on_job_done(self, _label: str, text: str, role: str) -> None:
        if text:
            self.strip.set_readout(text, role=role or None)

    # ---- dialogs -------------------------------------------------------------

    def prompt_text(self, title: str, label: str = "", default: str = "",
                    placeholder: str = "") -> Optional[str]:
        return ask_text(self, title, label, default, placeholder)

    def confirm(self, title: str, question: str, ok: str = "OK", cancel: str = "Cancel",
                danger: bool = False) -> bool:
        return confirm(self, title, question, ok, cancel, danger)

    # ---- the session ritual --------------------------------------------------

    def active_session_key(self) -> Optional[str]:
        return sessionkey.active_key(self.journal_paths)

    def mint_session(self, confirm: bool = True) -> Optional[str]:
        """The start ritual as one verb: refuse a repeat, confirm, mint +
        register + point + adopt (sessionkey.mint), the boot prompt on the
        clipboard, the readout — then `session_minted` for the app."""
        if self.session is None:
            self.strip.set_readout("no session — nothing to mint", role="warn")
            return None
        active = self.active_session_key()
        if active and sessionkey.is_repeat(active):
            self.strip.set_readout(f"session {active} just minted — repeat ignored")
            return None
        key = sessionkey.new_key()
        if confirm and not self.confirm(
                "Mint new session",
                f"Mint session {key} and adopt it as the live sitting?\n\n"
                f"The .cjm/current-session pointer moves and the boot prompt "
                f"lands on the clipboard.", ok="Mint"):
            return None
        res = sessionkey.mint(self.session, self.journal_paths)
        if res.get("error"):
            self.strip.set_readout(f"⚠ session write failed: {res['error']}", role="warn")
            return None
        key = res["key"]
        self.session_key, self.session_key_source = key, "mint"
        clip = QApplication.clipboard() if QApplication.instance() else None
        if clip is not None:
            clip.setText(sessionkey.boot_prompt(self.seat))
        self.strip.set_readout(
            f"session {key} minted + adopted — boot prompt on clipboard"
            + ("" if res.get("pointer") else " · ⚠ no journal: pointer NOT written"))
        self.session_minted.emit(key)
        return key

    def title_session(self, key: Optional[str] = None) -> Optional[str]:
        """The end ritual: name a session (an ordinary re-register; a later
        title never clobbers started_at)."""
        key = key or self.session_key or self.active_session_key()
        if self.session is None or not key:
            self.strip.set_readout("no seated session to title", role="warn")
            return None
        text = self.prompt_text("Session title", f"title for {key}:")
        if not text or not text.strip():
            return None
        try:
            res = self.session.register_session(str(key), title=text.strip())
        except Exception as e:  # keep the seat up
            self.strip.set_readout(f"⚠ title write failed: {e}", role="warn")
            return None
        if isinstance(res, dict) and res.get("error"):
            self.strip.set_readout(f"⚠ {res['error']}", role="warn")
            return None
        self.strip.set_readout(f"titled: {text.strip()}")
        self.session_titled.emit(str(key), text.strip())
        return text.strip()

    def retract_target(self) -> Optional[str]:
        """The session an app's retract verb aims at (override to name the
        focused row); the seated key by default is REFUSED below."""
        return None

    def retract_session(self, key: Optional[str], confirm: bool = True) -> bool:
        """Retract an EMPTY double-minted session: the active key refuses,
        the data layer refuses any session with journaled ops (only true
        empty mints pass), confirm, then the journaled retraction."""
        if self.session is None or not key:
            self.strip.set_readout("retract: no session row focused", role="warn")
            return False
        if key == self.active_session_key():
            self.strip.set_readout(f"⚠ {key} is the ACTIVE session — not retracting", role="warn")
            return False
        if confirm and not self.confirm("Retract session", f"Retract empty session {key}?",
                                        ok="Retract", danger=True):
            return False
        try:
            res = self.session.retract_session(str(key))
        except Exception as e:
            res = {"error": str(e)}
        if isinstance(res, dict) and res.get("error"):
            self.strip.set_readout(f"⚠ {res['error']}", role="warn")
            return False
        self.strip.set_readout(f"session {key} retracted")
        return True

    # ---- teardown ------------------------------------------------------------

    def closeEvent(self, event) -> None:
        if self._pool is not None:
            self._pool.shutdown(wait=False)
        super().closeEvent(event)
