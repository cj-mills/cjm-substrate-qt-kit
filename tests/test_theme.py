"""The runtime contract: one Theme lands fonts + palette + stylesheet on the
application; mode and system switches re-target the SAME Theme and fire the
ONE change signal; every kit widget restyles on it (the survey's
stale-widget gap, closed by construction); the preference precedence;
state words resolve through the live vars; the reading-quality pane setup."""

import json
import os

import pytest
from PySide6.QtGui import QColor, QPalette, QTextBlockFormat
from PySide6.QtWidgets import QLabel, QListWidgetItem, QTextEdit

from cjm_substrate_qt_kit import prefs
from cjm_substrate_qt_kit import theme as th
from cjm_substrate_qt_kit import tokens as T
from cjm_substrate_qt_kit.findbar import FindBar
from cjm_substrate_qt_kit.formdialog import FormShell
from cjm_substrate_qt_kit.hitl import ProvenancePane, VerdictStrip
from cjm_substrate_qt_kit.keyhints import KeyHintsOverlay
from cjm_substrate_qt_kit.pickerlist import PickerList, _ROW_HTML
from cjm_substrate_qt_kit.statusstrip import StatusStrip
from cjm_substrate_qt_kit.style import apply_row_style


@pytest.fixture(autouse=True)
def isolated_prefs(tmp_path, monkeypatch):
    monkeypatch.setenv(prefs.PREFS_ENV, str(tmp_path / "theme.json"))
    monkeypatch.delenv(prefs.ENV_VAR, raising=False)
    yield


@pytest.fixture
def theme(app):
    return th.apply_theme(app, "classical", "light")


def test_headless_default_vars_before_apply():
    v = th.current_theme()
    assert v["system"] == "classical" and v["accent"].startswith("#")


def test_apply_lands_on_application_and_is_one_object(app):
    t = th.apply_theme(app, "classical", "dark")
    assert th.current() is t and th.current_theme() is t.vars
    assert t.system == "classical" and t.mode == "dark" and t.requested == "dark"
    # Fusion is pinned underneath; with an application stylesheet set, Qt
    # answers style() with its stylesheet proxy — which is the proof the
    # rendered QSS is live on the application.
    assert app.style().metaObject().className() == "QStyleSheetStyle"
    assert t.vars["danger"] in app.styleSheet()
    assert '*[role="danger"]' in app.styleSheet()
    assert app.palette().color(QPalette.ColorRole.Window).name() == QColor(t.vars["bg"]).name()
    assert app.font().pixelSize() == int(float(t.vars["fs_ui"]))
    again = th.apply_theme(app, "netrunner", "blue")
    assert again is t                      # re-targeted, never a second Theme
    assert t.system == "netrunner" and t.mode == "blue"
    assert "Silkscreen" in app.styleSheet() or t.vars["font_heading"] == "Silkscreen"


def test_fonts_registered_from_the_system(theme):
    assert any("Lora" in f for f in theme.families)
    assert any("Cormorant" in f for f in theme.families)


def test_mode_switch_fires_the_one_signal(theme):
    seen = []
    th.on_change(lambda t: seen.append((t.system, t.mode)))
    theme.set_mode("dark")
    theme.toggle()
    theme.set_system("netrunner")
    assert seen == [("classical", "dark"), ("classical", "light"), ("netrunner", "red")]
    with pytest.raises(KeyError):
        theme.set_mode("midnight")


def test_set_system_keeps_a_requested_mode_when_it_exists(theme):
    theme.set_mode("dark")
    theme.set_system("netrunner")          # no dark mode there -> auto -> first mode
    assert theme.mode == "red" and theme.requested == "auto"
    theme.set_system("classical", "dark")
    assert theme.mode == "dark"


def test_auto_follows_os_only_with_a_scheme_map(app):
    t = th.apply_theme(app, "classical", "auto")
    assert t.follows_os and t.mode in ("light", "dark")
    t.set_system("netrunner", "auto")
    assert not t.follows_os and t.mode == "red"


def test_prefs_precedence(app, monkeypatch, tmp_path):
    assert prefs.resolve() == ("classical", "auto", "default")
    prefs.write("netrunner", "green")
    assert prefs.resolve()[:2] == ("netrunner", "green")
    monkeypatch.setenv(prefs.ENV_VAR, "classical:dark")
    assert prefs.resolve()[:2] == ("classical", "dark")
    monkeypatch.setenv(prefs.ENV_VAR, ":light")
    assert prefs.resolve() == ("netrunner", "light", "system:prefs mode:env")
    assert prefs.resolve("classical", "auto")[:2] == ("classical", "auto")
    monkeypatch.delenv(prefs.ENV_VAR)
    t = th.apply_theme(app)                 # walks the prefs file
    assert (t.system, t.requested) == ("netrunner", "green")
    t.set_mode("blue", persist=True)
    assert json.loads(prefs.prefs_path().read_text()) == {"system": "netrunner", "mode": "blue"}


def test_state_color_resolves_roles_and_legacy_words(theme):
    v = theme.vars
    assert th.state_color("red").name() == QColor(v["danger"]).name()
    assert th.state_color("danger").name() == QColor(v["danger"]).name()
    assert th.state_color("dim").name() == QColor(v["dim"]).name()
    assert th.state_color("bold") is None
    assert th.state_color("font_body") is None      # a non-color var never leaks
    assert th.state_color("name") is None


def test_apply_row_style_resolves_through_live_theme(theme):
    item = QListWidgetItem("x")
    apply_row_style(item, "red bold")
    assert item.foreground().color().name() == QColor(theme.vars["danger"]).name()
    assert item.font().bold()


def test_make_font_slots(theme):
    assert th.make_font(kind="body").family() == "Lora"
    assert th.make_font(kind="heading").family() == "Cormorant Garamond"
    assert th.make_font(kind="mono").pixelSize() == int(float(theme.vars["fs_mono"]))
    theme.set_system("netrunner")
    assert th.make_font(kind="mono").family() == "Courier Prime"


def test_document_css_from_the_type_scale(theme):
    css = th.document_css()
    assert f"h1 {{ font-family: 'Cormorant Garamond'; font-size: {theme.vars['fs_h1']}px" in css
    assert f"a {{ color: {theme.vars['accent']}; }}" in css


def test_style_text_pane_sets_wrap_and_line_height(theme):
    pane = QTextEdit()
    pane.setPlainText("hello\nworld")
    th.style_text_pane(pane)
    assert pane.lineWrapMode() == QTextEdit.LineWrapMode.FixedPixelWidth
    assert pane.lineWrapColumnOrWidth() > 0
    fmt = pane.textCursor().blockFormat()
    assert fmt.lineHeight() == pytest.approx(float(theme.vars["line_height"]) * 100.0)
    assert fmt.lineHeightType() == QTextBlockFormat.LineHeightTypes.ProportionalHeight.value


def test_style_text_pane_live_survives_content_swap(app, theme):
    from PySide6.QtWidgets import QPlainTextEdit
    pane = QPlainTextEdit()
    pane.setReadOnly(True)
    th.style_text_pane(pane, live=True)
    pane.setPlainText("fresh content after styling")
    app.processEvents()
    fmt = pane.textCursor().blockFormat()
    assert fmt.lineHeight() == pytest.approx(float(theme.vars["line_height"]) * 100.0)


# ---- restyle-on-signal, one per kit widget --------------------------------

def _mode_colors(theme):
    """(danger under light, danger under dark) as the probe pair."""
    light = T.resolve(theme.tokens, "light")["danger"]
    dark = T.resolve(theme.tokens, "dark")["danger"]
    assert light != dark
    return light, dark


def test_pickerlist_rerenders_rows_and_detail_on_signal(theme):
    light, dark = _mode_colors(theme)
    p = PickerList()
    p.set_rows([{"kind": "item", "spans": [("boom", "danger")], "key": 1}], cursor=0)
    p.set_detail([[("why", "danger")]])
    assert light in p.view.item(0).data(_ROW_HTML) and light in p.detail.toHtml()
    theme.set_mode("dark")
    assert dark in p.view.item(0).data(_ROW_HTML) and light not in p.view.item(0).data(_ROW_HTML)
    assert dark in p.detail.toHtml()
    assert p.cursor == 0 and p.count() == 1        # no rebuild, the cursor stays


def test_verdict_strip_and_provenance_repaint_on_signal(theme):
    light, dark = _mode_colors(theme)
    strip = VerdictStrip()
    strip.set_verdicts({"rejected": 2})            # rejected paints danger
    prov = ProvenancePane()
    prov.set_entries([("set", "s1")])
    dim_light = theme.vars["dim"]
    assert light in strip.text() and dim_light in prov.toHtml()
    theme.set_mode("dark")
    assert dark in strip.text() and light not in strip.text()
    assert theme.vars["dim"] in prov.toHtml() and theme.vars["dim"] != dim_light


def test_formshell_and_keyhints_rerender_on_signal(app, theme):
    shell = FormShell(None)
    shell.set_header("TITLE")
    text_light = theme.vars["text"]
    assert text_light in shell.head.toHtml()
    overlay = KeyHintsOverlay(shell, entries=[{"verb": "quit", "label": "Quit", "key": "q", "group": "App"}])
    overlay._render()                     # the document, without the modal open (test_keyhints owns that)
    overlay.setVisible(True)              # a visible overlay re-renders on the signal
    caps_light = theme.vars["tag_neutral_bg"]
    assert caps_light in overlay.view.toHtml()
    theme.set_mode("dark")
    assert theme.vars["text"] in shell.head.toHtml() and text_light not in shell.head.toHtml()
    assert theme.vars["tag_neutral_bg"] in overlay.view.toHtml() and caps_light not in overlay.view.toHtml()
    overlay.setVisible(False)


def test_findbar_repaints_matches_on_signal(app, theme):
    pane = QTextEdit()
    pane.setPlainText("alpha beta alpha")
    bar = FindBar(pane)
    bar.open()
    bar.field.setText("alpha")
    app.processEvents()

    def focused_background() -> str:
        selections = pane.extraSelections()       # keep the list alive while reading
        return QColor(selections[0].format.background().color()).name()

    before = focused_background()
    theme.set_mode("dark")
    after = focused_background()
    assert before != after
    assert after == QColor(theme.vars["accent"]).name()
    bar.close_bar()


def test_statusstrip_role_colors_follow_the_stylesheet(app, theme):
    strip = StatusStrip()
    strip.set_readout("bad", role="danger")
    strip.show()
    app.processEvents()
    light, dark = _mode_colors(theme)
    assert strip.readout.palette().color(QPalette.ColorRole.WindowText).name() == QColor(light).name()
    theme.set_mode("dark")
    app.processEvents()
    assert strip.readout.palette().color(QPalette.ColorRole.WindowText).name() == QColor(dark).name()
    strip.close()


def test_role_property_colors_any_label(app, theme):
    lb = QLabel("x")
    lb.setProperty("role", "ok")
    lb.show()
    app.processEvents()
    assert lb.palette().color(QPalette.ColorRole.WindowText).name() == QColor(theme.vars["ok"]).name()
    lb.close()
