"""The loop-thread session base: a private asyncio loop behind a Qt shell.

Extracted from the third repetition of the pattern (GraphSession in
cjm-graph-workbench-qt, CapabilitySession in cjm-transcription-qt): async
subsystems — the projection lens layer, the capability stack — live on a
daemon loop thread; the Qt shell submits coroutines and resolves the returned
concurrent Futures through queued Signals, so the paint thread never blocks.
Qt-free on purpose: sessions test headless, and non-Qt callers (probes,
scripts) can drive them the same way.

The shell ruling (2bae2cc1 (2)) collapses the six per-app subclasses onto
this base's OPEN / JOURNAL / CLOSE pattern: start() spins the loop and runs
the on_open() hook ON it (open the graph, the capability stack); journal()
mirrors a landed write into the writes journal in cg-write's exact arg
shape (the db is a projection — an unjournaled write is lost on the next
rebuild); close() runs on_close() and stops the thread. The Qt half — the
Future -> Signal bridge — is `bridge.FutureBridge`, owned by the shell."""

import asyncio
import threading
from concurrent.futures import Future
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

try:  # the op clock (design 8f6f2343) — optional, like journaling itself
    from cjm_context_graph_primitives.journal import op_clocked, PROVENANCE_TS
except ImportError:  # no primitives: no journal, so no clock to carry
    op_clocked = PROVENANCE_TS = None


class LoopThreadSession:
    """Owns one daemon asyncio loop thread; subclasses put their subsystem's
    verbs on top as submit()-wrapped coroutines.

    start() spins the loop, then runs on_open() on it (subclasses open their
    resources there); close() runs the on_close() coroutine hook, then stops
    the thread. submit() is the non-blocking bridge (Future -> queued Signal
    in a shell); call() blocks — teardown paths and headless tests."""

    thread_name = "loop-session"

    def __init__(self, timeout: float = 60.0,
                 journal_paths: Optional[Sequence[Union[str, Path]]] = None):
        self.timeout = timeout
        self.journal_paths: List[str] = [str(p) for p in (journal_paths or [])]
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None

    @property
    def running(self) -> bool:
        return self._loop is not None

    def start(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever,
                                        name=self.thread_name, daemon=True)
        self._thread.start()
        self.call(self.on_open())

    async def on_open(self) -> None:
        """Subclass hook, run ON the loop right after it spins: open the
        subsystem (a graph, a capability stack) once per session."""

    def journal(self, verb: str, args: Dict[str, Any]) -> Optional[str]:
        """Mirror a LANDED write into the writes journal (journal_paths[0])
        with the exact arg shape cg-write's CLI records — replay / rebuild
        treat app writes and cg-writes identically. Returns the journal path
        written, None when the session has no journal."""
        if not self.journal_paths:
            return None
        try:
            from cjm_context_graph_primitives.journal import append_write
        except ImportError as e:
            raise RuntimeError("cjm-context-graph-primitives is required to journal "
                               "graph writes from a session") from e
        append_write(self.journal_paths[0], verb, args)
        return self.journal_paths[0]

    def submit(self, coro) -> Future:
        """Schedule a coroutine on the loop thread; resolves there. The caller's op clock
        window rides along (design 8f6f2343): a write submitted inside `op_write` runs in it."""
        ts = PROVENANCE_TS.get() if PROVENANCE_TS is not None else None
        if ts is not None:
            coro = _in_window(coro, ts)
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    def call(self, coro):
        """Blocking submit (the sync facade)."""
        return self.submit(coro).result(self.timeout)

    async def on_close(self) -> None:
        """Subclass hook: release loop-side resources before the loop stops."""

    def close(self) -> None:
        if self._loop is None:
            return
        try:
            self.call(self.on_close())
        finally:
            self._loop.call_soon_threadsafe(self._loop.stop)
            if self._thread is not None:
                self._thread.join(timeout=5)
            self._loop = None
            self._thread = None


async def _in_window(coro, ts: float):  # The coroutine's result
    """Run a submitted coroutine inside the caller's op clock window (the loop thread's task
    does not inherit the submitting thread's context)."""
    token = PROVENANCE_TS.set(ts)
    try:
        return await coro
    finally:
        PROVENANCE_TS.reset(token)


def op_write(fn):
    """One session write gesture = ONE op clock window (design 8f6f2343, amendment efd659a1's
    grain for apps): the db write the method submits and the journal op it mirrors carry the
    same time, so the live db equals its rebuild. Wraps sync methods (the window rides into the
    loop coroutine through `submit`) and coroutine methods (the window opens on the loop);
    a pass-through when cjm-context-graph-primitives is absent (no journal, no clock). The
    kit's name for primitives' `op_clocked`."""
    return op_clocked(fn) if op_clocked is not None else fn
