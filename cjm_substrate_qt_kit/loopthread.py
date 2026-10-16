"""The loop-thread session base: a private asyncio loop behind a Qt shell.

Extracted from the third repetition of the pattern (GraphSession in
cjm-graph-workbench-qt, CapabilitySession in cjm-transcription-qt): async
subsystems — the projection lens layer, the capability stack — live on a
daemon loop thread; the Qt shell submits coroutines and resolves the returned
concurrent Futures through queued Signals, so the paint thread never blocks.
Qt-free on purpose: sessions test headless, and non-Qt callers (probes,
scripts) can drive them the same way.

The shell ruling (2bae2cc1 (2)) collapses the six per-app subclasses onto
this base's OPEN / WRITE / CLOSE pattern: start() spins the loop and runs
the on_open() hook ON it (open the graph, the capability stack); a write is
an `op_write` gesture -- ONE coroutine on the loop, run inside the app's unit
of work (a projection graph's `writes.write_window`: the journal family's
lock and heal, plan -> append -> apply per op; ruling d2d05e78), so a live
write is the replay's applier and the db never runs ahead of its journal;
close() runs on_close() and stops the thread. The base takes no journal
dependency of its own (it serves the layer's seats too). The Qt half — the
Future -> Signal bridge — is `bridge.FutureBridge`, owned by the shell."""

import asyncio
import contextvars
import functools
import inspect
import os
import threading
import time
from concurrent.futures import Future
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

try:  # the op clock (design 8f6f2343) — optional, like journaling itself
    from cjm_context_graph_primitives.journal import op_clocked, PROVENANCE_TS
except ImportError:  # no primitives: no journal, so no clock to carry
    op_clocked = PROVENANCE_TS = None
try:  # the instrument (design detail 4389a579) — optional the same way
    from cjm_context_graph_primitives import timings
except ImportError:  # no primitives: nothing measured
    timings = None
if timings is not None and not hasattr(timings, "append_event"):  # the seam's floor: primitives 0.0.21
    timings = None


class LoopThreadSession:
    """Owns one daemon asyncio loop thread; subclasses put their subsystem's
    verbs on top as submit()-wrapped coroutines.

    start() spins the loop, then runs on_open() on it (subclasses open their
    resources there); close() runs the on_close() coroutine hook, then stops
    the thread. submit() is the non-blocking bridge (Future -> queued Signal
    in a shell); call() blocks — teardown paths and headless tests.

    THE GESTURE SEAM (design detail 4389a579, the instrument of work item
    85b0d368): every gesture is one measured run -- a bare submit is one, an
    `op_write` method or a `gesture()` block is one however many submits it
    makes -- whose storage calls (round trips, rows, bytes, seconds) the
    layer's storage door folds in; its event lands in the db's timings ledger
    once the subclass names the db (`measure_into`). A gesture named in
    `polls` folds into one rolling run, appended at most every
    `poll_flush_s`. The growth covariates are measured off the gesture path:
    at `measure_into`, then every `covariates_every_s` (`measure_covariates`
    is the subclass hook)."""

    thread_name = "loop-session"
    app: Optional[str] = None             # The gesture events' app name (default: thread_name)
    polls: frozenset = frozenset()        # Gesture names that are polls (timer-driven re-reads)
    poll_flush_s: float = 60.0            # A poll's rolling run is appended at most this often
    covariates_every_s: float = 600.0     # The covariates' refresh period once measured

    def __init__(self, timeout: float = 60.0,
                 journal_paths: Optional[Sequence[Union[str, Path]]] = None):
        self.timeout = timeout
        self.journal_paths: List[str] = [str(p) for p in (journal_paths or [])]
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self.timings_path: Optional[str] = None             # Where gesture events land (measure_into)
        self.covariates: Optional[Dict[str, Any]] = None    # The latest covariates, `at` stamped
        self._polls: Dict[str, List[Any]] = {}              # Poll name -> [rolling run, ticks in flight]
        self._polls_lock = threading.Lock()
        self._covariates_task: Optional[asyncio.Task] = None

    @property
    def running(self) -> bool:
        return self._loop is not None

    def start(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever,
                                        name=self.thread_name, daemon=True)
        self._thread.start()
        self.call(self.on_open(), gesture="open")

    async def on_open(self) -> None:
        """Subclass hook, run ON the loop right after it spins: open the
        subsystem (a graph, a capability stack) once per session."""

    def submit(self, coro, gesture: Optional[str] = None) -> Future:
        """Schedule a coroutine on the loop thread; resolves there. The caller's op clock
        window rides along (design 8f6f2343): a write submitted inside `op_write` runs in it.
        So does the caller's gesture (design detail 4389a579): inside one, the coroutine's
        storage calls fold into it; outside, this submit IS the gesture -- named `gesture`,
        else the coroutine's own name -- timed from this call."""
        if timings is not None:
            coro = self._measured(coro, gesture)
        ts = PROVENANCE_TS.get() if PROVENANCE_TS is not None else None
        if ts is not None:
            coro = _in_window(coro, ts)
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    def call(self, coro, gesture: Optional[str] = None):
        """Blocking submit (the sync facade)."""
        return self.submit(coro, gesture=gesture).result(self.timeout)

    async def on_close(self) -> None:
        """Subclass hook: release loop-side resources before the loop stops."""

    def close(self) -> None:
        if self._loop is None:
            return
        try:
            self.call(self._closing(), gesture="close")
        finally:
            self._loop.call_soon_threadsafe(self._loop.stop)
            if self._thread is not None:
                self._thread.join(timeout=5)
            self._loop = None
            self._thread = None
            self.flush_polls()

    async def _closing(self) -> None:
        if self._covariates_task is not None:
            self._covariates_task.cancel()
            self._covariates_task = None
        await self.on_close()

    # ---- the gesture seam (design detail 4389a579) ---------------------------

    def gesture_name(self, name: str) -> str:  # "<app>:<gesture>", the event's name
        return f"{self.app or self.thread_name}:{name}"

    def _new_run(self, name: str, **attrs):  # A gesture run, timed from now (never armed here)
        return timings.Run("gesture", self.gesture_name(name), app=self.app or self.thread_name,
                           **attrs)

    def _measured(self, coro, gesture: Optional[str]):  # The coroutine inside its gesture run
        carried = timings.CURRENT_RUN.get()
        if carried is not None:  # inside a gesture: its calls fold in, its owner ends it
            return _armed(coro, carried, time.perf_counter())
        name = gesture or coro_name(coro)
        if name in self.polls:
            run = self._poll_tick(name)
            return _armed(coro, run, time.perf_counter(),
                          lambda queued, work, outcome: self._tick_done(name, run, queued, work,
                                                                        outcome))
        run = self._new_run(name)

        def finish(queued: float, work: float, outcome: str) -> None:
            run.add("queued", queued)
            self._append(run, outcome)
        return _armed(coro, run, run.t0, finish)

    @contextmanager
    def gesture(self, name: str, **attrs):
        """Measure a block as ONE gesture: every submit inside it folds its storage calls in,
        and its event is appended when the block ends (whatever its outcome). Inside another
        gesture the block folds into that one. `op_write` methods are gestures this way."""
        if timings is None or timings.CURRENT_RUN.get() is not None:
            yield
            return
        run = self._new_run(name, **attrs)
        token = timings.CURRENT_RUN.set(run)
        outcome = "ok"
        try:
            yield
        except BaseException as e:
            outcome = type(e).__name__
            run.attrs["error"] = f"{outcome}: {e}"[:500]  # the diagnosis rides with the measurement
            raise
        finally:
            timings.CURRENT_RUN.reset(token)
            self._append(run, outcome)

    def _append(self, run, outcome: str) -> None:  # One gesture event into the ledger (fail-open)
        if self.timings_path:
            timings.append_event(self.timings_path, run.event(outcome=outcome,
                                                              covariates=self.covariates))

    def _poll_tick(self, name: str):  # The poll's rolling run, one more tick in flight
        with self._polls_lock:
            entry = self._polls.get(name)
            if entry is None:
                entry = self._polls[name] = [self._new_run(name, poll=True), 0]
            entry[1] += 1
            return entry[0]

    def _tick_done(self, name: str, run, queued: float, work: float, outcome: str) -> None:
        """Fold one finished tick (`tick` = its work, `queued` = its wait, `failed` counted);
        the rolling run is appended once its window is due and no tick is in flight."""
        run.add("queued", queued)
        run.add("tick", work, failed=outcome != "ok")
        with self._polls_lock:
            entry = self._polls.get(name)
            if entry is None or entry[0] is not run:
                return
            entry[1] -= 1
            if entry[1] > 0 or time.perf_counter() - run.t0 < self.poll_flush_s:
                return
            del self._polls[name]
        self._append(run, "ok")

    def flush_polls(self) -> None:
        """Append every poll's rolling run now (close does; a probe may)."""
        with self._polls_lock:
            entries, self._polls = list(self._polls.values()), {}
        for run, _inflight in entries:
            self._append(run, "ok")

    async def measure_into(self, db_path: str) -> None:
        """Run ON the loop once the db is known (on_open, or a later open step): gesture events
        land in its timings ledger (`<db stem>.timings.jsonl`, or CJM_TIMINGS_PATH when a
        harness names one); the covariates are measured now, then every
        `covariates_every_s` on a task of their own, never inside a gesture's run."""
        if timings is None:
            return
        self.timings_path = os.environ.get("CJM_TIMINGS_PATH") or timings.timings_path(db_path)
        await self._refresh_covariates()
        if self._covariates_task is None:
            self._covariates_task = asyncio.get_running_loop().create_task(
                self._covariates_every(), context=contextvars.Context())

    async def measure_covariates(self) -> Optional[Dict[str, Any]]:
        """Subclass hook: the growth covariates of the open graph (nodes, edges, db bytes,
        kinds; journals where the session's gestures read them). None = not measured."""
        return None

    async def _refresh_covariates(self) -> None:
        try:
            cov = await self.measure_covariates()
        except Exception as e:  # the instrument never breaks the session
            cov = {"error": f"{type(e).__name__}: {e}"}
        if cov is not None:
            self.covariates = {**cov, "at": time.time()}

    async def _covariates_every(self) -> None:
        while True:
            await asyncio.sleep(self.covariates_every_s)
            await self._refresh_covariates()


async def _in_window(coro, ts: float):  # The coroutine's result
    """Run a submitted coroutine inside the caller's op clock window (the loop thread's task
    does not inherit the submitting thread's context)."""
    token = PROVENANCE_TS.set(ts)
    try:
        return await coro
    finally:
        PROVENANCE_TS.reset(token)


def coro_name(coro) -> str:  # The gesture name a submitted coroutine carries by default
    """A coroutine's own code name, leading underscores stripped (`_node` -> `node`): the
    default name of the gesture a bare submit begins (design detail 4389a579). A session
    that wraps the coroutine it submits (a serializing lock) names the inner one."""
    code = getattr(coro, "cr_code", None)
    return (code.co_name if code is not None else type(coro).__name__).lstrip("_") or "gesture"


async def _armed(coro, run, submitted: float, finish=None):  # The coroutine's result
    """Run a submitted coroutine inside a measured gesture (design detail 4389a579): the run is
    armed on the loop task, so every storage call the coroutine makes folds into it. `finish`
    -- given when the submit began the run -- takes the queue wait (submit to start), the
    work's seconds and the outcome; a carried run is ended by whoever began it."""
    started = time.perf_counter()
    token = timings.CURRENT_RUN.set(run)
    outcome = "ok"
    try:
        return await coro
    except BaseException as e:
        outcome = type(e).__name__
        run.attrs["error"] = f"{outcome}: {e}"[:500]  # the diagnosis rides with the measurement
        raise
    finally:
        timings.CURRENT_RUN.reset(token)
        if finish is not None:
            finish(started - submitted, time.perf_counter() - started, outcome)


def op_write(fn):
    """One session write gesture = ONE op clock window (design 8f6f2343, amendment efd659a1's
    grain for apps): every op the gesture plans, appends and applies carries the same time, so
    the live db equals its rebuild. A write gesture is ONE coroutine method (ruling d2d05e78 (1)):
    the unit of work's lock and write observer are context-scoped, so a gesture split across
    submits would be several units. Wraps sync methods (the window rides into the loop coroutine
    through `submit`) and coroutine methods (the window opens on the loop);
    a pass-through when cjm-context-graph-primitives is absent (no journal, no clock). The
    kit's name for primitives' `op_clocked`. The same grain is ONE measured gesture (design
    detail 4389a579): every submit the method makes folds into it, the journal appends
    included."""
    clocked = op_clocked(fn) if op_clocked is not None else fn
    if timings is None:
        return clocked
    if inspect.iscoroutinefunction(fn):
        @functools.wraps(fn)
        async def gesture_async(self, *args, **kwargs):
            if not isinstance(self, LoopThreadSession):
                return await clocked(self, *args, **kwargs)
            with self.gesture(fn.__name__, write=True):
                return await clocked(self, *args, **kwargs)
        return gesture_async

    @functools.wraps(fn)
    def gesture_sync(self, *args, **kwargs):
        if not isinstance(self, LoopThreadSession):
            return clocked(self, *args, **kwargs)
        with self.gesture(fn.__name__, write=True):
            return clocked(self, *args, **kwargs)
    return gesture_sync
