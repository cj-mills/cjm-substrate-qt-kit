"""The loop-thread session base: a private asyncio loop behind a Qt shell.

Extracted from the third repetition of the pattern (GraphSession in
cjm-graph-workbench-qt, CapabilitySession in cjm-transcription-qt): async
subsystems — the projection lens layer, the capability stack — live on a
daemon loop thread; the Qt shell submits coroutines and resolves the returned
concurrent Futures through queued Signals, so the paint thread never blocks.
Qt-free on purpose: sessions test headless, and non-Qt callers (probes,
scripts) can drive them the same way."""

import asyncio
import threading
from concurrent.futures import Future
from typing import Optional


class LoopThreadSession:
    """Owns one daemon asyncio loop thread; subclasses put their subsystem's
    verbs on top as submit()-wrapped coroutines.

    start() spins the loop (subclasses may extend it to open resources ON the
    loop); close() runs the on_close() coroutine hook, then stops the thread.
    submit() is the non-blocking bridge (Future -> queued Signal in a shell);
    call() blocks — teardown paths and headless tests."""

    thread_name = "loop-session"

    def __init__(self, timeout: float = 60.0):
        self.timeout = timeout
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

    def submit(self, coro) -> Future:
        """Schedule a coroutine on the loop thread; resolves there."""
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
