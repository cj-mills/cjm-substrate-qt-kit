"""The reading pane: link cycling from the text cursor, Return activation
through the one route a click takes, the seat round-trip, block-exact
scroll-to-group."""

from PySide6.QtCore import Qt, QUrl
from PySide6.QtTest import QTest

from cjm_substrate_qt_kit.readingpane import ReadingPane

HTML = ('<p>intro <a href="graph://one">one</a> then <a href="graph://two">two</a></p>'
        '<p>neighbours (2)</p><p>REFERENCES</p><p>a <a href="graph://three">three</a></p>'
        '<p>SHAPES</p>' + "".join(f"<p>para {i}</p>" for i in range(60)))


def pane(app):
    p = ReadingPane()
    p.resize(600, 300)
    p.setHtml(HTML)
    p.show()
    app.processEvents()
    return p


def test_anchor_spans_and_cycling(app):
    p = pane(app)
    assert [h for _s, _e, h in p.anchor_spans()] == ["graph://one", "graph://two", "graph://three"]
    p.cycle_link(1)
    assert p.textCursor().selectedText() == "one" and p.focused_href() == "graph://one"
    p.cycle_link(1)
    assert p.textCursor().selectedText() == "two"
    p.cycle_link(-1)
    assert p.textCursor().selectedText() == "one"
    p.cycle_link(-1)                                  # wraps to the last
    assert p.textCursor().selectedText() == "three"
    p.close()


def test_return_activates_the_selected_link_through_one_route(app):
    p = pane(app)
    seen = []
    p.activated.connect(lambda url: seen.append(url.toString()))
    QTest.keyClick(p, Qt.Key.Key_Tab)
    QTest.keyClick(p, Qt.Key.Key_Return)
    assert seen == ["graph://one"]
    QTest.keyClick(p, Qt.Key.Key_Backtab)
    QTest.keyClick(p, Qt.Key.Key_Enter)               # the numpad key too
    assert seen == ["graph://one", "graph://three"]
    p.setTextCursor(p.textCursor().__class__(p.document()))   # no selection
    assert p.activate_link() is False
    p.close()


def test_seat_round_trip_and_scroll_to_block(app):
    p = pane(app)
    bar = p.verticalScrollBar()
    assert bar.maximum() > 0
    p.cycle_link(1)
    p.cycle_link(1)
    bar.setValue(bar.maximum() // 2)
    seat = p.seat()
    assert seat[0] == bar.maximum() // 2 and seat[1] != seat[2]
    p.setHtml(HTML)                                   # a repaint loses everything
    p.restore_seat(seat, deferred=False)
    assert p.textCursor().selectedText() == "two" and bar.value() == seat[0]
    bar.setValue(0)
    assert p.scroll_to_block("SHAPES", after_prefix="neighbours (")
    assert bar.value() > 0 and p.textCursor().block().text() == "SHAPES"
    assert not p.scroll_to_block("nowhere", after_prefix="neighbours (")
    assert not p.scroll_to_block("intro one then two", after_prefix="neighbours (")   # before the prefix
    p.close()
