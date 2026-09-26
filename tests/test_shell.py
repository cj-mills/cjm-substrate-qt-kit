"""The app shell contract (ruling 2bae2cc1 + d1e3043e): stages, the menus
derived from the keymap, the hints model, async reads through the bridge
with the busy readout, jobs in the seat, and the session ritual verbs —
adoption at launch, the one mint, title, retract."""

import os
import time
from concurrent.futures import Future, ThreadPoolExecutor

import pytest
from PySide6.QtWidgets import QApplication, QLabel, QTextBrowser

from cjm_substrate_qt_kit import prefs, sessionkey as sk
from cjm_substrate_qt_kit.bridge import FutureBridge
from cjm_substrate_qt_kit.shell import AppShell


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv(prefs.PREFS_ENV, str(tmp_path / "theme.json"))
    monkeypatch.delenv(prefs.ENV_VAR, raising=False)
    monkeypatch.delenv(prefs.DECORATIONS_ENV, raising=False)
    monkeypatch.delenv(sk.ENV_VAR, raising=False)
    yield


class FakeSession:
    def __init__(self, journal_paths):
        self.journal_paths = journal_paths
        self.writes = []

    def register_session(self, key, **kw):
        kw["env_at_write"] = os.environ.get(sk.ENV_VAR)
        self.writes.append(("session", key, kw))
        return {"written": True, "key": key}

    def retract_session(self, key, **kw):
        self.writes.append(("retract", key, kw))
        return {"written": True}


def resolved(value) -> Future:
    fut = Future()
    fut.set_result(value)
    return fut


def wait_until(app, pred, timeout=3.0):
    deadline = time.time() + timeout
    while not pred():
        app.processEvents()
        if time.time() > deadline:
            raise AssertionError("timed out")
        time.sleep(0.01)


def shell(tmp_path, session=True):
    journals = [str(tmp_path / ".cjm" / "g.writes.jsonl")]
    s = FakeSession(journals) if session else None
    win = AppShell("the workbench", session=s, seat="workbench")
    return win, s


def test_stages_and_derived_menus(app, tmp_path):
    win, _ = shell(tmp_path)
    assert win.titlebar.title.text() == "the workbench"
    rows = win.add_stage("rows", QLabel("rows"))
    pane = win.add_stage("node", QTextBrowser())
    assert win.current_stage() == "rows"
    assert win.show_stage("node") is pane and win.current_stage() == "node"
    win.keymap.add("back", "Back", "B", lambda: None, group="Navigate")
    win.keymap.add("quit", "Quit", "Q", lambda: None, group="File")
    win.add_session_verbs(retract="X")
    win.finish_keys([{"verb": "rows-move", "label": "move", "key": "J/K", "group": "Rows"}])
    titles = [a.text() for a in win.menubar.actions()]
    assert titles == ["Navigate", "File", "Session", "View", "Theme"]
    session_menu = win.menubar.actions()[2].menu()
    assert [a.text() for a in session_menu.actions()] == [
        "Mint new session (start ritual)", "Title seated session (end ritual)",
        "Retract an empty session"]
    verbs = {e["verb"] for e in win.hints_overlay._entries}
    assert {"back", "quit", "keys", "find", "theme-next", "mint-session", "rows-move"} <= verbs
    theme_titles = [a.text() for a in win.theme_menu.actions() if a.text()]
    assert "Design system" in theme_titles and "Decorations" in theme_titles
    assert rows.parent() is not None


def test_read_async_busy_readout_and_error(app, tmp_path):
    win, _ = shell(tmp_path)
    got = []
    win.read_async(resolved({"ok": 1}), got.append)
    assert got == [{"ok": 1}]
    assert win.strip.readout.text() == ""                  # busy cleared once settled
    failed = Future()
    failed.set_exception(RuntimeError("graph down"))
    win.read_async(failed, got.append)
    assert "graph down" in win.strip.readout.text() and win.strip.readout.property("role") == "warn"
    # a future resolving on another thread lands on the Qt thread
    with ThreadPoolExecutor(1) as pool:
        win.read_async(pool.submit(lambda: 42), got.append, busy="pulling…")
        wait_until(app, lambda: 42 in got)
    assert win.bridge.pending() == 0
    win.call_async(lambda: "sync facade", got.append)
    wait_until(app, lambda: "sync facade" in got)
    win.close()


def test_bridge_delivers_once_per_future(app):
    bridge = FutureBridge()
    seen = []
    fut = resolved(1)
    bridge.watch(fut, seen.append)
    bridge._deliver(fut)                                    # a stray second delivery is ignored
    assert seen == [1] and bridge.pending() == 0


def test_run_job_rows_and_readout(app, tmp_path):
    win, _ = shell(tmp_path)
    done = []
    fut = Future()
    job = win.run_job("finetune", fut, on_done=done.append, done_text="finetune landed")
    assert win.jobs.count() == 1 and job.label_text == "finetune"
    fut.set_result("model.pt")
    assert done == ["model.pt"] and win.jobs.count() == 0
    assert win.strip.readout.text() == "finetune landed" and win.strip.readout.property("role") == "ok"
    bad = Future()
    win.run_job("export", bad)
    bad.set_exception(ValueError("disk full"))
    assert "disk full" in win.strip.readout.text() and win.strip.readout.property("role") == "danger"


def test_mint_adopts_points_and_puts_the_prompt_on_the_clipboard(app, tmp_path):
    win, session = shell(tmp_path)
    assert (win.session_key, win.session_key_source) == (None, "none")
    minted = []
    win.session_minted.connect(minted.append)
    key = win.mint_session(confirm=False)
    assert key and minted == [key]
    verb, wkey, kw = session.writes[0]
    assert verb == "session" and wkey == key and kw["started_at"]
    assert kw["env_at_write"] == key                        # adopted BEFORE the write
    assert os.environ[sk.ENV_VAR] == key and win.session_key == key
    assert (tmp_path / ".cjm" / "current-session").read_text() == key
    assert QApplication.clipboard().text().endswith("New session minted in-workbench.")
    assert "boot prompt on clipboard" in win.strip.readout.text()
    # a second press inside the repeat window is refused
    assert win.mint_session(confirm=False) is None
    assert "repeat ignored" in win.strip.readout.text()


def test_launch_adopts_the_pointer_but_never_the_inherited_env(app, tmp_path, monkeypatch):
    journals = [str(tmp_path / ".cjm" / "g.writes.jsonl")]
    sk.write_pointer(sk.pointer_path(journals), "2026-09-25_19-12-44")
    win = AppShell("x", session=FakeSession(journals))
    assert (win.session_key, win.session_key_source) == ("2026-09-25_19-12-44", "pointer")
    monkeypatch.setenv(sk.ENV_VAR, "inherited")
    win2 = AppShell("x", session=FakeSession(journals))
    assert (win2.session_key, win2.session_key_source) == ("inherited", "env")


def test_title_and_retract_verbs(app, tmp_path, monkeypatch):
    win, session = shell(tmp_path)
    monkeypatch.setattr(win, "prompt_text", lambda *a, **k: "  the sitting  ")
    titled = []
    win.session_titled.connect(lambda k, t: titled.append((k, t)))
    assert win.title_session() is None                      # unseated
    assert "no seated session" in win.strip.readout.text()
    monkeypatch.setenv(sk.ENV_VAR, "2026-09-25_19-12-44")
    assert win.title_session() == "the sitting"
    assert session.writes[-1] == ("session", "2026-09-25_19-12-44", {"title": "the sitting",
                                                                      "env_at_write": "2026-09-25_19-12-44"})
    assert titled == [("2026-09-25_19-12-44", "the sitting")]
    assert win.retract_session("2026-09-25_19-12-44", confirm=False) is False   # the ACTIVE key
    assert "ACTIVE" in win.strip.readout.text()
    assert win.retract_session("2026-09-25_10-00-00", confirm=False) is True
    assert session.writes[-1][:2] == ("retract", "2026-09-25_10-00-00")


def test_shell_without_a_session_stays_up(app, tmp_path):
    win, _ = shell(tmp_path, session=False)
    win.add_session_verbs()
    win.finish_keys()
    assert not win.keymap.has("mint-session")
    assert win.mint_session(confirm=False) is None
    assert "nothing to mint" in win.strip.readout.text()


def test_find_needs_a_reading_pane(app, tmp_path):
    win, _ = shell(tmp_path)
    win.add_stage("rows", QLabel("rows"))
    win.open_find()
    assert not win.findbar.isVisible()
    pane = win.add_stage("node", QTextBrowser())
    pane.setPlainText("some text to find")
    win.show_stage("node")
    win.open_find()
    assert win.findbar.pane is pane and win.findbar.isVisibleTo(win)
    win.findbar.close_bar()
