"""LoopThreadSession contract: submit/call resolve on the loop thread, the
on_close hook runs before the loop stops, close is idempotent."""

import asyncio
import threading

from cjm_substrate_qt_kit.loopthread import LoopThreadSession


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
