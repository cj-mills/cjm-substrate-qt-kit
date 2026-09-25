"""Tests for the text clamps (the end-keeping tail) — ported with the
function from the tui-kit's viewport tests (work item 21145648)."""
from cjm_substrate_qt_kit.text import tail


def test_tail_clamps_keeping_the_end():
    # Paths clamp from the FRONT — the filename end is the readable part
    assert tail("/very/long/path/episode-042.mp3", 16) == "…episode-042.mp3"
    assert tail("short.mp3", 16) == "short.mp3"       # within width: unchanged
    assert tail("abcdef", 6) == "abcdef"              # exactly width: unchanged
    assert tail("abcdef", 5) == "…cdef"               # ellipsis counts against width
    assert tail("abcdef", 1) == "…"
    assert tail("abcdef", 0) == ""
