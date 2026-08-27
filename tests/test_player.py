"""SpanPlayer start-gap guard bookkeeping (the 039c9a62 wedge class): burst
requests inside the gap coalesce latest-wins, an explicit stop cancels the
coalesced request, and the whole-file convenience rides the same choke point.
No audio plays — the tests drive the request bookkeeping only (offscreen;
actual sink behavior is field-verified per the TUI/Qt paint-path craft)."""
import sys

import pytest
from PySide6.QtWidgets import QApplication

from cjm_substrate_qt_kit.player import SpanPlayer


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv[:1])
    yield app


def test_burst_coalesces_latest_wins(qapp):
    p = SpanPlayer()
    p.play_span("/tmp/a.wav", 0.0, 1.0)          # idle -> starts (goes pending on load)
    assert p._req is None
    p.play_span("/tmp/b.wav", 1.0, 2.0)          # inside the gap -> coalesces
    p.play_span("/tmp/c.wav", 2.0, 3.0)          # latest wins
    assert p._req == ("/tmp/c.wav", 2.0, 3.0, 1.0)
    assert p._req_timer.isActive()
    p.close()


def test_stop_cancels_coalesced_request(qapp):
    p = SpanPlayer()
    p.play_span("/tmp/a.wav", 0.0, 1.0)
    p.play_span("/tmp/b.wav", 1.0, 2.0)
    p.stop()
    assert p._req is None and not p._req_timer.isActive()
    assert p._end_ms is None
    p.close()


def test_whole_file_play_rides_the_guard(qapp):
    p = SpanPlayer()
    p.play("/tmp/a.wav")                          # SegmentPlayer surface
    assert p._end_ms is None                      # open span: natural end
    p.play("/tmp/b.wav", rate=1.5)                # burst -> coalesces
    assert p._req == ("/tmp/b.wav", 0.0, None, 1.5)
    p.close()


def test_degenerate_span_sounds_nothing(qapp):
    """Zero-span replay finding (2026-08-26): a start==end request at the
    player's ms resolution must never reach QMediaPlayer — handed over, the
    file ran on to its natural end (a whole aseg WAV). Idle or inside the
    start gap, the guard stops and returns without coalescing."""
    p = SpanPlayer()
    p.play_span("/tmp/a.wav", 506.8, 506.8)      # idle -> refused outright
    assert p._end_ms is None and p._req is None and not p._pending
    assert p._player.source().isEmpty()          # never handed to the backend
    p.play_span("/tmp/a.wav", 0.0, 1.0)          # idle -> starts (pending on load)
    p.play_span("/tmp/b.wav", 2.0, 2.0)          # degenerate inside the gap -> stop
    assert p._req is None and not p._req_timer.isActive() and not p._pending
    p.close()
