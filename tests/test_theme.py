"""Theme contract: per-token fallback, word->role resolution, palette/QSS
generation, apply_theme landing palette + stylesheet + fonts, and
apply_row_style resolving through the live theme."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import json

import pytest
from PySide6.QtGui import QColor, QPalette, QTextBlockFormat
from PySide6.QtWidgets import QApplication, QListWidgetItem, QTextEdit

from cjm_substrate_qt_kit import theme as th
from cjm_substrate_qt_kit.style import apply_row_style


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_resolve_theme_merges_overrides_per_token():
    t = th.resolve_theme({"content": "#000001"}, scheme="light")
    assert t["name"] == "kit-light"
    assert t["content"] == "#000001"
    assert t["base"] == th.LIGHT["base"]  # omitted tokens keep defaults
    assert t["measure"] == th.LIGHT["measure"]


def test_state_color_resolves_words_and_roles():
    assert th.state_color("red", th.DARK).name() == QColor(th.DARK["danger"]).name()
    assert th.state_color("dim", th.LIGHT).name() == QColor(th.LIGHT["content-dim"]).name()
    assert th.state_color("danger", th.LIGHT).name() == QColor(th.LIGHT["danger"]).name()
    assert th.state_color("bold", th.DARK) is None
    assert th.state_color("name", th.DARK) is None  # non-color token never leaks


def test_build_qss_carries_state_channels():
    qss = th.build_qss(th.DARK)
    assert '*[role="danger"] { color: %s; }' % th.DARK["danger"] in qss
    assert '*[role="content-dim"]' in qss
    assert th.DARK["surface"] in qss


def test_build_palette_projects_roles():
    p = th.build_palette(th.LIGHT)
    assert p.color(QPalette.ColorRole.Window).name() == QColor(th.LIGHT["base"]).name()
    assert p.color(QPalette.ColorRole.Base).name() == QColor(th.LIGHT["surface"]).name()
    assert p.color(QPalette.ColorRole.Highlight).name() == QColor(th.LIGHT["selection-bg"]).name()
    assert (p.color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text).name()
            == QColor(th.LIGHT["content-dim"]).name())


def test_load_theme_round_trips(tmp_path):
    path = tmp_path / "custom.json"
    path.write_text(json.dumps({"name": "custom", "content": "#123456"}))
    t = th.resolve_theme(th.load_theme(path), scheme="dark")
    assert t["name"] == "custom"
    assert t["content"] == "#123456"
    assert t["base"] == th.DARK["base"]


def test_apply_theme_lands_on_application(app):
    t = th.apply_theme(app, scheme="dark")
    assert th.current_theme() is t
    assert th._live["pinned"] == "dark"
    assert t["danger"] in app.styleSheet()
    assert (app.palette().color(QPalette.ColorRole.Window).name()
            == QColor(t["base"]).name())


def test_apply_row_style_resolves_through_live_theme(app):
    th.apply_theme(app, scheme="dark")
    item = QListWidgetItem("x")
    apply_row_style(item, "red bold")
    assert item.foreground().color().name() == QColor(th.DARK["danger"]).name()
    assert item.font().bold()


def test_style_text_pane_live_survives_content_swap(app):
    from PySide6.QtWidgets import QPlainTextEdit
    pane = QPlainTextEdit()
    pane.setReadOnly(True)
    th.style_text_pane(pane, th.LIGHT, live=True)
    pane.setPlainText("fresh content after styling")
    app.processEvents()
    fmt = pane.textCursor().blockFormat()
    assert fmt.lineHeight() == pytest.approx(th.LIGHT["font-body-line-height"] * 100.0)


def test_style_text_pane_sets_wrap_and_line_height(app):
    pane = QTextEdit()
    pane.setPlainText("hello\nworld")
    th.style_text_pane(pane, th.LIGHT)
    assert pane.lineWrapMode() == QTextEdit.LineWrapMode.FixedPixelWidth
    assert pane.lineWrapColumnOrWidth() > 0
    fmt = pane.textCursor().blockFormat()
    assert fmt.lineHeight() == pytest.approx(th.LIGHT["font-body-line-height"] * 100.0)
    assert fmt.lineHeightType() == QTextBlockFormat.LineHeightTypes.ProportionalHeight.value
