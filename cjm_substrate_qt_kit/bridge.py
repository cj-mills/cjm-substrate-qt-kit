"""The Future -> Signal bridge (ruling 2bae2cc1 (2)): a concurrent Future
resolved on the session's loop thread lands on the Qt thread as a slot
call, through ONE queued signal — the paint thread never blocks on a read
(register rule P-23). Every app re-implemented this with a per-window
Signal + a done-callback; the shell owns one bridge and every async read
and job goes through it."""

import sys
import traceback
from concurrent.futures import Future
from typing import Callable, Dict, Optional, Tuple

from PySide6.QtCore import QObject, Signal


class FutureBridge(QObject):
    """watch(future, on_result, on_error) — the callbacks run on the bridge's
    thread (the Qt thread) whichever thread resolves the future. A future
    that is already done delivers synchronously (a direct connection on the
    same thread — the probes' already-resolved fakes keep working)."""

    _arrived = Signal(object)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._pending: Dict[int, Tuple[Future, Callable, Optional[Callable]]] = {}
        self._arrived.connect(self._deliver)

    def watch(self, future: Future, on_result: Callable,
              on_error: Optional[Callable[[BaseException], None]] = None) -> Future:
        self._pending[id(future)] = (future, on_result, on_error)
        future.add_done_callback(self._arrived.emit)
        return future

    def pending(self) -> int:
        return len(self._pending)

    def _deliver(self, future) -> None:
        entry = self._pending.pop(id(future), None)
        if entry is None:
            return
        _fut, on_result, on_error = entry
        try:
            result = future.result()
        except BaseException as e:  # noqa: BLE001 — a cancelled or failed read
            if on_error is not None:
                on_error(e)
            else:
                print("cjm-substrate-qt-kit: unhandled async failure:", file=sys.stderr)
                traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)
            return
        on_result(result)
