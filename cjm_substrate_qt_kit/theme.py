"""Semantic theme tokens for the lane: one flat dict -> QPalette + QSS + fonts.

A theme is data (kebab-case token keys, JSON-shaped): palette roles
(base / surface / raised / border, content / content-dim, selection-bg /
selection-content, accent / accent-content), semantic STATE channels
(danger / warn / ok / info / meta / note), and typography
(font-body-* / font-mono-* / font-ui-*, measure, heading-scale). The kit
generates everything from the dict — apps never write raw QSS. Missing
tokens fall back per-token to the built-in light/dark pair; the OS scheme
(QStyleHints.colorScheme, Qt 6.5+) picks the member unless a scheme is
pinned. Legacy Rich color words (the spine wire format) resolve through
WORD_ROLES as a temporary compatibility mapping."""

import json
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPalette, QTextBlockFormat, QTextCursor
from PySide6.QtWidgets import QApplication, QTextEdit, QWidget

# Legacy Rich color words (spine wire format) -> semantic state roles.
# Temporary compatibility mapping; migrating the spines to semantic words
# is a named future item, not v1 scope.
WORD_ROLES = {"red": "danger", "yellow": "warn", "green": "ok",
              "blue": "info", "cyan": "meta", "magenta": "note",
              "dim": "content-dim"}

_TYPOGRAPHY = {"font-body-family": "", "font-body-size": 12.0,
               "font-body-weight": 400, "font-body-line-height": 1.45,
               "font-mono-family": "", "font-mono-size": 11.0,
               "font-ui-family": "", "font-ui-size": 10.5,
               "measure": 68, "heading-scale": 1.2}

# Provisional reading-first pair — starting values are test-bed hypotheses
# (family/size/line-height/measure/contrast tune on trial evidence).
LIGHT = {"name": "kit-light",
         "base": "#eceae4", "surface": "#f7f5f0", "raised": "#ffffff",
         "border": "#d5d0c4", "content": "#20211f", "content-dim": "#5c6166",
         "selection-bg": "#c7dbf0", "selection-content": "#20211f",
         "accent": "#3d63a8", "accent-content": "#ffffff",
         "danger": "#a83226", "warn": "#8a5f00", "ok": "#2c7a41",
         "info": "#3d63a8", "meta": "#1f7386", "note": "#7d4796",
         **_TYPOGRAPHY}

DARK = {"name": "kit-dark",
        "base": "#191b1f", "surface": "#20242a", "raised": "#292e36",
        "border": "#3a4048", "content": "#e6e4df", "content-dim": "#9aa1a9",
        "selection-bg": "#31455e", "selection-content": "#e6e4df",
        "accent": "#7da2d9", "accent-content": "#12161c",
        "danger": "#e0796d", "warn": "#d3a44a", "ok": "#6dbd83",
        "info": "#82a5e0", "meta": "#5cb4c7", "note": "#bd8bd3",
        **_TYPOGRAPHY}

# Live-theme registry: what apply_theme last resolved, the overrides it
# carried, and whether the scheme is pinned; the colorSchemeChanged hook
# reads it to re-apply on OS flips.
_live = {"theme": None, "overrides": None, "pinned": None, "connected": False}


def _os_scheme() -> str:
    """The OS color scheme as "light"/"dark" (dark when undetectable)."""
    app = QApplication.instance()
    hints = app.styleHints() if app is not None else None
    scheme = hints.colorScheme() if hasattr(hints, "colorScheme") else None
    return "light" if scheme == Qt.ColorScheme.Light else "dark"


def resolve_theme(overrides: Optional[dict] = None,
                  scheme: Optional[str] = None) -> dict:
    """Merge override tokens onto the built-in pair member for the scheme
    ("light"/"dark"; None = the OS scheme). Per-token fallback: anything a
    custom theme omits keeps the default value."""
    base = LIGHT if (scheme or _os_scheme()) == "light" else DARK
    theme = dict(base)
    theme.update(overrides or {})
    return theme


def current_theme() -> dict:
    """The theme apply_theme last landed (default-resolved before any apply)."""
    return _live["theme"] or resolve_theme()


def load_theme(path) -> dict:
    """Read a theme-as-data JSON file (a flat token dict): themes are shared
    data a projection binds, never code."""
    return json.loads(Path(path).read_text())


def state_color(word: str, theme: Optional[dict] = None) -> Optional[QColor]:
    """Resolve a legacy style word or a semantic role to the theme's color
    (None for words with no color binding, e.g. "bold")."""
    t = theme if theme is not None else current_theme()
    value = t.get(WORD_ROLES.get(word, word))
    return QColor(value) if isinstance(value, str) and value.startswith("#") else None


def make_font(theme: Optional[dict] = None, kind: str = "body") -> QFont:
    """Build the theme's font for a slot: "body" / "mono" / "ui". An empty
    family token means the system default (mono keeps the fixed style hint)."""
    t = theme if theme is not None else current_theme()
    font = QFont()
    family = str(t.get("font-" + kind + "-family") or "")
    if family:
        font.setFamily(family)
    elif kind == "mono":
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFamily("monospace")
    font.setPointSizeF(float(t.get("font-" + kind + "-size") or 11.0))
    if kind == "body":
        font.setWeight(QFont.Weight(int(t.get("font-body-weight") or 400)))
    return font


def build_palette(theme: dict) -> QPalette:
    """Project the palette roles onto QPalette so NATIVE widgets follow the
    theme (QSS covers the styled subset; the palette covers the rest)."""
    def color(key: str) -> QColor:
        return QColor(theme[key])
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window, color("base"))
    p.setColor(QPalette.ColorRole.WindowText, color("content"))
    p.setColor(QPalette.ColorRole.Base, color("surface"))
    p.setColor(QPalette.ColorRole.AlternateBase, color("raised"))
    p.setColor(QPalette.ColorRole.Text, color("content"))
    p.setColor(QPalette.ColorRole.PlaceholderText, color("content-dim"))
    p.setColor(QPalette.ColorRole.Button, color("raised"))
    p.setColor(QPalette.ColorRole.ButtonText, color("content"))
    p.setColor(QPalette.ColorRole.Highlight, color("selection-bg"))
    p.setColor(QPalette.ColorRole.HighlightedText, color("selection-content"))
    p.setColor(QPalette.ColorRole.Link, color("accent"))
    p.setColor(QPalette.ColorRole.ToolTipBase, color("raised"))
    p.setColor(QPalette.ColorRole.ToolTipText, color("content"))
    for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text,
                 QPalette.ColorRole.ButtonText):
        p.setColor(QPalette.ColorGroup.Disabled, role, color("content-dim"))
    return p


def build_qss(theme: dict) -> str:
    """Generate the lane's QSS layer: chrome polish + dynamic-property state
    channels — a widget declares setProperty("role", "danger") and the
    stylesheet colors it (state rendered declaratively, per-widget)."""
    t = theme
    states = "\n".join('*[role="%s"] { color: %s; }' % (role, t[role])
                       for role in ("danger", "warn", "ok", "info", "meta",
                                    "note", "content-dim", "accent"))
    return (
        f"QListWidget {{ background: {t['surface']}; border: 1px solid {t['border']}; }}\n"
        f"QListWidget::item {{ padding: 2px 6px; }}\n"
        f"QListWidget::item:selected {{ background: {t['selection-bg']}; color: {t['selection-content']}; }}\n"
        f"QTextEdit, QPlainTextEdit, QTextBrowser {{ background: {t['surface']}; "
        f"border: 1px solid {t['border']}; "
        f"selection-background-color: {t['selection-bg']}; "
        f"selection-color: {t['selection-content']}; }}\n"
        f"QLineEdit {{ background: {t['raised']}; border: 1px solid {t['border']}; padding: 2px 4px; }}\n"
        f"QToolTip {{ background: {t['raised']}; color: {t['content']}; border: 1px solid {t['border']}; }}\n"
        f"QSplitter::handle {{ background: {t['border']}; }}\n"
        f"QStatusBar {{ color: {t['content-dim']}; }}\n"
        + states + "\n")


def document_css(theme: Optional[dict] = None) -> str:
    """Default stylesheet for rich-text documents (setDefaultStyleSheet):
    heading sizes walk heading-scale down to body size, links take accent."""
    t = theme if theme is not None else current_theme()
    body = float(t.get("font-body-size") or 12.0)
    scale = float(t.get("heading-scale") or 1.2)
    rules = [f"a {{ color: {t['accent']}; }}"]
    for level in (1, 2, 3, 4):
        rules.append(f"h{level} {{ font-size: {round(body * scale ** (4 - level), 1)}pt; }}")
    return "\n".join(rules)


def style_text_pane(pane: QWidget, theme: Optional[dict] = None,
                    mono: bool = False, measure: bool = True,
                    live: bool = False) -> None:
    """Reading-quality setup for a text pane (QTextEdit / QTextBrowser /
    QPlainTextEdit): body (or mono) font, line-height via QTextBlockFormat,
    measure as a fixed wrap width — QSS can express none of these. The block
    format lands on the CURRENT document content: one-shot callers re-call
    after loading; panes whose content repaints pass live=True, which keeps
    line-height applied across content swaps by re-merging on textChanged
    (recursion-guarded; meant for read-only panes, not editors — every merge
    is an undoable edit)."""
    t = theme if theme is not None else current_theme()
    font = make_font(t, "mono" if mono else "body")
    pane.setFont(font)
    doc = pane.document()
    doc.setDocumentMargin(12.0)
    doc.setDefaultStyleSheet(document_css(t))
    height = float(t.get("font-body-line-height") or 1.0) * 100.0
    _merge_line_height(pane, height)
    if measure and t.get("measure") and isinstance(pane, QTextEdit):
        width = QFontMetrics(font).averageCharWidth() * int(t["measure"])
        pane.setLineWrapMode(QTextEdit.LineWrapMode.FixedPixelWidth)
        pane.setLineWrapColumnOrWidth(width + 2 * int(doc.documentMargin()))
    if live:
        first_wire = not hasattr(pane, "_kit_live_height")
        pane._kit_live_height = height
        if first_wire:
            pane.textChanged.connect(
                lambda: _merge_line_height(pane, pane._kit_live_height))


def _on_scheme_change() -> None:
    """Re-apply on OS scheme flips — only while the scheme is not pinned."""
    app = QApplication.instance()
    if app is not None and _live["pinned"] is None:
        apply_theme(app, _live["overrides"])


def apply_theme(app: QApplication, overrides: Optional[dict] = None,
                scheme: Optional[str] = None) -> dict:
    """THE entry point: resolve the theme and land palette + QSS + ui font on
    the whole application. scheme None = follow the OS live (re-applies on
    colorSchemeChanged); an explicit "light"/"dark" pins the member."""
    theme = resolve_theme(overrides, scheme)
    _live.update(theme=theme, overrides=overrides, pinned=scheme)
    app.setPalette(build_palette(theme))
    app.setStyleSheet(build_qss(theme))
    app.setFont(make_font(theme, "ui"))
    hints = app.styleHints()
    if not _live["connected"] and hasattr(hints, "colorSchemeChanged"):
        hints.colorSchemeChanged.connect(lambda _scheme: _on_scheme_change())
        _live["connected"] = True
    return theme


def _merge_line_height(pane: QWidget, height: float) -> None:
    """Merge a proportional line-height onto the pane's whole document,
    guarded so the merge's own textChanged signal cannot recurse."""
    if getattr(pane, "_kit_height_busy", False):
        return
    pane._kit_height_busy = True
    try:
        fmt = QTextBlockFormat()
        fmt.setLineHeight(height,
                          QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
        cursor = QTextCursor(pane.document())
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.mergeBlockFormat(fmt)
    finally:
        pane._kit_height_busy = False
