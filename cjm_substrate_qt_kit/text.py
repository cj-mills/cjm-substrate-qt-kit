"""Text clamps for one-line surfaces — path-like strings keep their END.

A status readout, a header chip or a listing row budgets characters, and a
path's readable part is its tail (the filename), so clamping cuts the FRONT.
Pure Python, Qt-free.

`tail` was born in the tui-kit's viewport module beside the screen-line
windowing math (extracted from the transcription TUI's drive-2 ergonomics
batch, work items 1e5f8e5d -> aafce2c6); the Textual retirement (ruling
8b7351e4, work item 21145648) ported the one function the Qt apps still
used — the windowing math retired with the archive, native scrolling having
replaced it.
"""


def tail(
    s: str,      # The string to clamp (paths: the end is the readable part)
    width: int,  # Max characters INCLUDING the leading ellipsis
) -> str:  # s unchanged, or an ellipsis + its last width-1 characters
    """Clamp a string to width keeping its END.

    A filename's tail is what the operator reads, so clamping cuts the front
    (tail-ellipsis truncation cuts the wrong end for cwd headers and
    selected-source rows).
    """
    if width <= 0:
        return ""
    if len(s) <= width:
        return s
    if width == 1:
        return "…"
    return "…" + s[-(width - 1):]
