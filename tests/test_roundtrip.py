"""The switch-equals-launch invariant (finding b7e68f56): a design-system
switch lands exactly what a fresh launch under the target lands, and a round
trip restores the start pixel-for-pixel — over every gallery page (the
reading pane included) in both directions; plus the two mechanisms that
broke it: the reading pane's parse-time styling and the two font channels."""

import pytest
from PySide6.QtGui import QTextCursor

from cjm_substrate_qt_kit import roundtrip
from cjm_substrate_qt_kit.gallery import Gallery
from cjm_substrate_qt_kit.pickerlist import PickerList
from cjm_substrate_qt_kit.readingpane import ReadingPane
from cjm_substrate_qt_kit.theme import apply_theme, current, current_theme, font_family

MD = "# Head\n\nbody `code` [link](graph://x)\n\n```\nblock\n```\n"


@pytest.fixture
def classical_after(app):
    """Every test here swaps systems; leave the live theme on Classical."""
    yield
    apply_theme(app, "classical", "auto")


@pytest.mark.parametrize("a,b", [("classical", "netrunner"), ("netrunner", "classical")])
def test_gallery_switch_equals_launch(app, classical_after, a, b):
    diffs = roundtrip.check_switch(lambda: Gallery(current()), a, b,
                                   pages=lambda w: roundtrip.tabs_of(w.tabs), size=(1120, 780))
    assert diffs == [], "\n".join(map(str, diffs))


def _format_at(pane, needle):
    """The char format of the first character of `needle` in the pane."""
    cur = QTextCursor(pane.document())
    cur.setPosition(pane.document().toPlainText().index(needle) + 1)
    return cur.charFormat()


def test_reading_pane_lands_the_system_and_follows_a_switch(app, classical_after):
    th = apply_theme(app, "classical", "auto")
    p = ReadingPane()
    p.resize(500, 300)
    p.setMarkdown(MD)
    p.show()
    p.cycle_link(1)
    for system in ("classical", "netrunner", "classical"):
        th.set_system(system)
        roundtrip.settle()
        v = current_theme()
        assert _format_at(p, "Head").fontFamilies() == [font_family(v, "heading")]
        assert _format_at(p, "code").fontFamilies() == [font_family(v, "mono")]
        assert _format_at(p, "block").fontFamilies() == [font_family(v, "mono")]
        assert _format_at(p, "link").foreground().color().name() == th.color("accent").name()
        assert p.textCursor().selectedText() == "link"      # the seat survives the re-parse
    p.close()


def test_font_role_lands_at_launch_and_after_a_switch(app, classical_after):
    th = apply_theme(app, "classical", "auto")
    p = PickerList()
    p.show()
    roundtrip.settle()
    for system in ("classical", "netrunner", "classical"):
        th.set_system(system)
        roundtrip.settle()
        assert p.view.font().family() == font_family(current_theme(), "mono")
        assert p.detail.font().family() == font_family(current_theme(), "mono")
    p.close()


def _long_page(items: int = 80) -> str:
    """A workbench-shaped page taller than the ~2100 px Qt lays out before its
    incremental layout yields: a title, a fenced block, prose, a numbered
    list, then relation groups of link items."""
    parts = ["# A node title", "```yaml\nname: x\ndescription: \"" + "word " * 100 + "\"\n```"]
    parts += ["**Lead:** prose with *emphasis* — " + "and more words to wrap " * 40 for _ in range(10)]
    parts.append("## Refinements\n" + "\n".join(f"{i}. **Point {i}:** " + "text " * 60 for i in range(1, 5)))
    for g in range(4):
        parts.append(f"**RELATION{g}**")
        parts.append("\n".join(f"- ← [neighbour {i} " + "with more words " * (1 + i % 5) + f"](graph://n{i}) *Decision*"
                               for i in range(items // 4)))
    return "\n\n".join(parts) + "\n"


def test_reading_pane_relays_the_whole_document_after_a_switch(app, classical_after):
    """A long document keeps its full height across a round trip — the
    styling pass's format edits under an in-flight incremental layout once
    left every block past ~2100 px unlaid (lineCount 0) while the layout
    reported itself finished: a short scroll range after a switch."""
    th = apply_theme(app, "classical", "auto")
    p = ReadingPane()
    p.resize(1052, 600)
    p.setMarkdown(_long_page())
    p.show()
    roundtrip.settle(p)
    start = p.document().size().height()
    assert start > 3000
    th.set_system("netrunner")
    roundtrip.settle(p)
    th.set_system("classical")
    roundtrip.settle(p)
    assert p.document().lastBlock().layout().lineCount() > 0
    assert p.document().size().height() == start
    p.close()
