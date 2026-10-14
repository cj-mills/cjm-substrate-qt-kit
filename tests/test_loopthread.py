"""LoopThreadSession contract: submit/call resolve on the loop thread, the
on_close hook runs before the loop stops, close is idempotent."""

import asyncio
import threading
import time

from cjm_context_graph_primitives import timings
from cjm_context_graph_primitives.journal import read_journal
from cjm_substrate_qt_kit.loopthread import LoopThreadSession, op_write


class Probe(LoopThreadSession):
    thread_name = "probe-loop"

    def __init__(self):
        super().__init__(timeout=5.0)
        self.closed_on: str = ""

    async def where(self) -> str:
        return threading.current_thread().name

    async def on_close(self) -> None:
        await asyncio.sleep(0)
        self.closed_on = threading.current_thread().name


def test_submit_and_call_run_on_the_loop_thread():
    p = Probe()
    assert not p.running
    p.start()
    assert p.running
    assert p.call(p.where()) == "probe-loop"
    assert p.submit(p.where()).result(5) == "probe-loop"
    p.close()


def test_on_close_runs_on_loop_then_thread_stops():
    p = Probe()
    p.start()
    thread = p._thread
    p.close()
    assert p.closed_on == "probe-loop"
    assert not thread.is_alive()
    assert not p.running
    p.close()  # idempotent


class Measured(LoopThreadSession):
    """A session over a fake store: each `read` is one storage call the door would record."""

    thread_name = "measured-loop"
    app = "probe"
    polls = frozenset({"tick"})

    def __init__(self, db: str):
        super().__init__(timeout=5.0)
        self.db = db
        self.measured = 0

    async def on_open(self) -> None:
        await self.measure_into(self.db)

    async def measure_covariates(self):
        self.measured += 1
        return {"nodes": 7}

    async def read(self, rows: int = 1):
        timings.record_storage("query_nodes", 0.001, rows_out=rows)
        return rows

    async def boom(self):
        raise ValueError("no")

    async def tick(self):
        timings.record_storage("query_nodes", 0.001, rows_out=1)

    @op_write
    def write_twice(self):
        self.call(self.read(2))
        return self.call(self.read(3))


def _events(ledger):
    return [e for e in read_journal(str(ledger)) if e.get("kind") == "gesture"]


def test_each_gesture_is_one_event_in_the_db_ledger(tmp_path):
    """Design detail 4389a579: a bare submit is one gesture (named by its coroutine, queued
    from the submit), an op_write method one gesture however many submits it makes; the open
    and the close are gestures; each event carries the covariates measured beside it."""
    p = Measured(str(tmp_path / "g.db"))
    p.start()
    assert p.timings_path == str(tmp_path / "g.timings.jsonl") and p.measured == 1
    assert p.call(p.read(4)) == 4
    assert p.write_twice() == 3
    try:
        p.call(p.boom())
    except ValueError:
        pass
    p.close()
    evs = {e["verb"]: e for e in _events(p.timings_path)}
    assert set(evs) == {"probe:open", "probe:read", "probe:write_twice", "probe:boom",
                        "probe:close"}
    read = evs["probe:read"]
    assert read["outcome"] == "ok" and read["storage"]["query_nodes"]["rows_out"] == 4
    assert "queued" in read["phases"] and read["covariates"]["nodes"] == 7
    assert read["attrs"]["app"] == "probe"
    w = evs["probe:write_twice"]
    assert w["storage"]["query_nodes"] == {"calls": 2, "s": 0.002, "rows_out": 5}
    assert w["attrs"]["write"] is True
    assert evs["probe:boom"]["outcome"] == "ValueError"
    assert evs["probe:boom"]["attrs"]["error"] == "ValueError: no"  # the diagnosis rides along


def test_a_poll_folds_into_one_rolling_event(tmp_path):
    """Ticks of a poll fold into one run -- `tick` counts them and their work -- appended at
    close (or once its window is due), never one event per tick."""
    p = Measured(str(tmp_path / "g.db"))
    p.start()
    for _ in range(3):
        p.call(p.tick())
    assert not [e for e in _events(p.timings_path) if e["verb"] == "probe:tick"]
    p.close()
    (ev,) = [e for e in _events(p.timings_path) if e["verb"] == "probe:tick"]
    assert ev["phases"]["tick"]["calls"] == 3 and ev["storage"]["query_nodes"]["calls"] == 3
    assert ev["attrs"]["poll"] is True


def test_a_poll_due_appends_and_rolls(tmp_path):
    p = Measured(str(tmp_path / "g.db"))
    p.poll_flush_s = 0.0
    p.start()
    p.call(p.tick())
    p.call(p.tick())
    p.close()
    assert len([e for e in _events(p.timings_path) if e["verb"] == "probe:tick"]) == 2


def test_harness_ledger_and_no_ledger(tmp_path, monkeypatch):
    """CJM_TIMINGS_PATH (the scale harness) overrides the db's ledger; a session that never
    names its db records nothing."""
    monkeypatch.setenv("CJM_TIMINGS_PATH", str(tmp_path / "bench.timings.jsonl"))
    p = Measured(str(tmp_path / "g.db"))
    p.start()
    p.call(p.read())
    p.close()
    assert p.timings_path == str(tmp_path / "bench.timings.jsonl")
    assert len(_events(p.timings_path)) == 3
    q = Probe()
    q.start()
    q.call(q.where())
    q.close()
    assert q.timings_path is None


def test_covariates_refresh_off_the_gesture_path(tmp_path):
    """The refresh task runs on its own (no gesture armed) and stops at close."""
    p = Measured(str(tmp_path / "g.db"))
    p.covariates_every_s = 0.01
    p.start()
    deadline = time.time() + 5
    while p.measured < 3 and time.time() < deadline:
        time.sleep(0.01)
    assert p.measured >= 3
    p.close()
    n = p.measured
    time.sleep(0.05)
    assert p.measured == n
    assert [e["verb"] for e in _events(p.timings_path)] == ["probe:open", "probe:close"]
