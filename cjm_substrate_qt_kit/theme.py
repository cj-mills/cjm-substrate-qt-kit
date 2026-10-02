"""The design-system RUNTIME: ONE Theme object, ONE change signal (ruling
8b7351e4 stratum (a); DEC 0b1cfd81 the build shape).

A Theme binds a QApplication to a design system (tokens as data, see
`tokens`) in one of the system's modes: Fusion pinned so QSS renders the
same on every OS, the system's fonts registered, a QPalette built from the
resolved vars (native widgets follow), the system's QSS templates rendered
with the recolored indicator icons, and the application font set. Every kit
widget connects to the change signal in its constructor and restyles itself
— a mode or system switch re-themes the whole window, including rich-text
painters, with no app code (the survey's stale-widget gap closes by
construction).

    theme = apply_theme(app)                       # prefs / env / default
    theme = apply_theme(app, "netrunner", "blue")  # an app's CLI flag
    theme.set_mode("dark"); theme.set_system("classical"); theme.toggle()
    on_change(widget.restyle)                      # any widget, any time
    current_theme()["accent"]                      # the live vars (HTML painters)

`current_theme()` is the flat vocabulary `tokens.resolve` emits — the one
vocabulary (fork 1): $bg $surface $text $accent $muted_solid $divider_solid
$selection_solid, the six state roles + `dim`, the font slots, the scale.
Before any apply (headless tests) it is Classical's first mode.

Legacy Rich color words (the spine wire format: red / yellow / green / blue /
cyan / magenta / dim) still resolve through WORD_ROLES until the spines emit
semantic role words (06d729ab)."""

import inspect
import sys
import tempfile
import weakref
from pathlib import Path
from string import Template
from typing import Callable, Dict, List, Optional, Union

import shiboken6
from cjm_design_system import systems as design_systems, tokens as T
from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import (QColor, QFont, QFontDatabase, QFontMetrics, QPalette, QTextBlockFormat,
                           QTextCursor, QTextDocument, QTextFormat)
from PySide6.QtWidgets import QApplication, QTextEdit, QWidget

from . import prefs, systems
from .icons import IconSet

KIT_QSS = Path(__file__).parent / "qss"   # the kit layer, appended after any system's templates

# Legacy Rich color words (spine wire format) -> state roles. Retires when the
# spines emit role words (06d729ab); until then every painter resolves both.
WORD_ROLES = {"red": "danger", "yellow": "warn", "green": "ok",
              "blue": "info", "cyan": "meta", "magenta": "note", "dim": "dim"}

# stylesheet indicator images: hole name -> (icon, color var)
QSS_ICONS = {
    "chevron_down": ("chevron-down", "muted"), "chevron_down_disabled": ("chevron-down", "disabled_text"),
    "chevron_up": ("chevron-up", "muted"), "chevron_right": ("chevron-right", "muted"),
    "check": ("check", "accent"), "check_disabled": ("check", "disabled_text"),
    "minus": ("minus", "accent"), "x": ("x", "muted"),
    "dot": ("dot", "accent"), "dot_disabled": ("dot", "disabled_text"),
}

# ---- the change signal + the live theme -------------------------------------

_listeners: List[object] = []          # weak refs to bound methods; strong refs to plain callables
_registered_fonts: Dict[str, List[str]] = {}   # font file -> families, once per process
_current: Optional["Theme"] = None
_headless: Optional[Dict[str, str]] = None


def on_change(slot: Callable) -> None:
    """Subscribe `slot(theme)` to every mode / system change — the ONE wire,
    alive before any Theme exists so widgets built before apply (and across
    a system swap) all hang on it. A BOUND METHOD is held weakly and dropped
    when its object dies (Python side) or its C++ half is deleted (checked at
    dispatch) — the kit widgets subscribe this way. A plain callable (a
    lambda, a module function) is held for the application's lifetime."""
    if inspect.ismethod(slot):
        _listeners.append(weakref.WeakMethod(slot))
    else:
        _listeners.append(slot)


def _dispatch(theme: "Theme") -> None:
    """Call every live listener; prune the dead (a GC'd owner, a deleted
    C++ object) instead of letting a stale wire raise mid-repaint."""
    for entry in list(_listeners):
        fn = entry() if isinstance(entry, weakref.ref) else entry
        owner = getattr(fn, "__self__", None)
        if fn is None or (isinstance(owner, QObject) and not shiboken6.isValid(owner)):
            try:
                _listeners.remove(entry)
            except ValueError:
                pass
            continue
        fn(theme)


def current() -> Optional["Theme"]:
    """The live Theme (None before apply_theme)."""
    return _current


def current_theme() -> Dict[str, str]:
    """The live resolved vars; Classical's first mode before any apply."""
    global _headless
    if _current is not None:
        return _current.vars
    if _headless is None:
        tok = T.load(design_systems.tokens_path(prefs.DEFAULT_SYSTEM))
        _headless = T.resolve(tok, T.modes(tok)[0])
    return _headless


# ---- projections ------------------------------------------------------------

def render_qss(tok: dict, mode: str, icons: IconSet, icon_out: Union[str, Path],
               qss_dir: Path) -> str:
    """Headless: tokens + mode -> the final stylesheet. The system's templates
    (its own `qss/`, else Classical's) then the kit layer, each group in file
    name order; `$holes` filled from the resolved vars; indicator SVGs
    recolored into `icon_out`."""
    v = T.resolve(tok, mode)
    v["font_mono_family"] = font_family(v, "mono")   # the font-role channel's mono face
    for hole, (name, color_var) in QSS_ICONS.items():
        v[f"icon_{hole}"] = icons.write(name, v[color_var], icon_out)
    files = sorted(Path(qss_dir).glob("*.qss")) + sorted(KIT_QSS.glob("*.qss"))
    src = "\n".join(p.read_text(encoding="utf-8") for p in files)
    return Template(src).safe_substitute(v)


def build_palette(v: Dict[str, str]) -> QPalette:
    """Project the vars onto QPalette so NATIVE widgets follow the theme (QSS
    covers the styled subset; the palette covers the rest)."""
    R, G = QPalette.ColorRole, QPalette.ColorGroup
    p = QPalette()
    roles = {
        R.Window: v["bg"], R.WindowText: v["text"], R.Base: v["bg"], R.AlternateBase: v["row_alt_solid"],
        R.Text: v["text"], R.Button: v["bg"], R.ButtonText: v["text"], R.BrightText: v["accent"],
        R.Highlight: v["selection_solid"], R.HighlightedText: v["text"],
        R.ToolTipBase: v["surface"], R.ToolTipText: v["text"], R.PlaceholderText: v["muted_solid"],
        R.Link: v["accent"], R.LinkVisited: v["accent_pressed"],
        R.Light: v["surface"], R.Midlight: v["surface"], R.Mid: v["divider_solid"],
        R.Dark: v["divider_solid"], R.Shadow: v["shadow"],
    }
    if hasattr(R, "Accent"):
        roles[R.Accent] = v["accent"]
    for role, c in roles.items():
        p.setColor(role, QColor(c))
    for role in (R.WindowText, R.Text, R.ButtonText):
        p.setColor(G.Disabled, role, QColor(v["disabled_solid"]))
    return p


# ---- the Theme --------------------------------------------------------------

class Theme(QObject):
    """theme = Theme.apply(app) — or apply_theme(app), the module-level door."""

    changed = Signal(object)

    def __init__(self, app: QApplication, system: Union[str, Path], mode: str = "auto", *,
                 cache_dir: Optional[Union[str, Path]] = None):
        super().__init__(app)
        self.app = app
        self._cache_root = Path(cache_dir) if cache_dir else Path(tempfile.gettempdir())
        self.requested = mode          # what was asked ("auto" follows the OS)
        self.mode = ""
        self.vars: Dict[str, str] = {}
        self._load_system(system)
        self.set_mode(mode)
        hints = app.styleHints()
        if hasattr(hints, "colorSchemeChanged"):
            hints.colorSchemeChanged.connect(lambda _scheme: self._on_os_scheme())

    # -- construction / system loading --

    @classmethod
    def apply(cls, app: QApplication, system: Optional[Union[str, Path]] = None,
              mode: Optional[str] = None, *, persist: bool = False,
              cache_dir: Optional[Union[str, Path]] = None) -> "Theme":
        """THE entry point. `system` / `mode` None walk the precedence in
        `prefs` (args > CJM_THEME > the prefs file > classical:auto). Fusion is
        pinned once. A second apply re-targets the ONE live Theme instead of
        minting another; `persist=True` writes the choice."""
        global _current
        system, mode, _source = prefs.resolve(None if system is None else str(system), mode)
        if _current is None or _current.app is not app:
            # The string overload: Qt creates AND owns the style. Passing a
            # QStyleFactory.create() temporary hands Python a wrapper it then
            # frees, leaving the application with a dangling style pointer
            # (a segfault on the next widget's polish).
            app.setStyle("Fusion")
            _current = cls(app, system, mode, cache_dir=cache_dir)
        else:
            _current.set_system(system, mode)
        if persist:
            prefs.write(_current.system, _current.requested)
        return _current

    def _load_system(self, system: Union[str, Path]) -> None:
        root = design_systems.locate(system)
        path = root / "tokens.json"
        tok = T.load(path)
        T.check(tok, str(path))
        self.root, self.tokens, self.system = root, tok, T.slug(tok)
        self.qss_dir = systems.qss_dir(self.system, root)
        icon_dirs = [root / "icons"] if (root / "icons").is_dir() else []
        stroke = float((tok.get("icons") or {}).get("stroke_width", T.ICONS_DEFAULTS["stroke_width"]))
        self.icons = IconSet(icon_dirs, stroke_width=stroke)
        self.cache = self._cache_root / f"cjm-qt-kit-{self.system}"
        self.families = self._load_fonts()

    def _load_fonts(self) -> List[str]:
        """Register the system's vendored font files — each file ONCE per
        process (a system swap must not re-add fonts the database already
        holds); name what is missing."""
        fams: List[str] = []
        fonts_dir = self.root / "fonts"
        for pat in self.tokens["fonts"].get("files", ["*.ttf", "*.otf"]):
            for f in sorted(fonts_dir.glob(pat)):
                key = str(f.resolve())
                if key not in _registered_fonts:
                    fid = QFontDatabase.addApplicationFont(key)
                    _registered_fonts[key] = (QFontDatabase.applicationFontFamilies(fid)
                                              if fid >= 0 else [])
                fams += _registered_fonts[key]
        f = self.tokens["fonts"]
        want = {f["heading"]["family"], f["body"]["family"]}
        want |= {str(f[slot]["family"]) for slot in ("mono", "ui") if f.get(slot, {}).get("family")}
        missing = want - set(fams) - set(QFontDatabase.families())
        if missing:
            print(f"cjm-substrate-qt-kit: {self.system}: fonts not found: {sorted(missing)} "
                  f"(expected under {fonts_dir})", file=sys.stderr)
        return fams

    # -- modes --

    @property
    def modes(self) -> List[str]:
        return T.modes(self.tokens)

    @property
    def follows_os(self) -> bool:
        """True while the requested mode is "auto" AND the system maps the OS scheme."""
        return self.requested == "auto" and bool(self.tokens.get("scheme"))

    def _os_scheme(self) -> str:
        hints = self.app.styleHints()
        scheme = hints.colorScheme() if hasattr(hints, "colorScheme") else None
        return "light" if scheme == Qt.ColorScheme.Light else "dark"

    def resolve_mode(self, mode: Optional[str]) -> str:
        """"auto" -> the OS scheme through the system's `scheme` map, else the
        first mode; a named mode must exist (KeyError names the modes)."""
        if not mode or mode == "auto":
            return T.mode_for_scheme(self.tokens, self._os_scheme()) or self.modes[0]
        if mode not in self.modes:
            raise KeyError(f"{self.system}: no mode {mode!r} — modes: {self.modes}")
        return mode

    def set_mode(self, mode: Optional[str] = "auto", *, persist: bool = False) -> None:
        """Land a mode on the application: font, palette, stylesheet — then
        the change signal. `persist=True` records the choice."""
        self.requested = mode or "auto"
        self.mode = self.resolve_mode(self.requested)
        self.vars = T.resolve(self.tokens, self.mode)
        self.app.setFont(make_font(self.vars, "ui"))
        self.app.setPalette(build_palette(self.vars))
        self.app.setStyleSheet(render_qss(self.tokens, self.mode, self.icons,
                                          self.cache / self.mode, self.qss_dir))
        if persist:
            prefs.write(self.system, self.requested)
        self.changed.emit(self)
        _dispatch(self)

    def set_system(self, system: Union[str, Path], mode: Optional[str] = None, *,
                   persist: bool = False) -> None:
        """Swap the design system (fonts, templates, icons) and land `mode` —
        the requested mode when it exists in the new system, else "auto"."""
        self._load_system(system)
        wanted = mode or self.requested
        if wanted != "auto" and wanted not in self.modes:
            wanted = "auto"
        self.set_mode(wanted, persist=persist)

    def toggle(self, *, persist: bool = False) -> None:
        """Cycle through the system's modes (pins the mode: OS following stops)."""
        ms = self.modes
        self.set_mode(ms[(ms.index(self.mode) + 1) % len(ms)], persist=persist)

    def _on_os_scheme(self) -> None:
        if self.requested == "auto":
            self.set_mode("auto")

    # -- conveniences --

    def color(self, var: str) -> QColor:
        return _qcolor(self.vars[var])

    def icon(self, name: str, color_var: str = "text", size: int = 18):
        return self.icons.icon(name, self.vars[color_var], size, self.vars["disabled_text"])


def apply_theme(app: QApplication, system: Optional[Union[str, Path]] = None,
                mode: Optional[str] = None, *, persist: bool = False) -> Theme:
    """Module-level door to Theme.apply (the name every app's launch calls)."""
    return Theme.apply(app, system, mode, persist=persist)


# ---- typography + painters over the live vars ------------------------------

def make_font(theme: Optional[Dict[str, str]] = None, kind: str = "body") -> QFont:
    """The system's font for a slot: "body" / "mono" / "ui" / "heading",
    pixel-sized from the tokens. An empty mono family means the platform's
    fixed font."""
    v = theme if theme is not None else current_theme()
    font = QFont()
    family = str(v.get(f"font_{kind}") or "")
    if family:
        font.setFamily(family)
    elif kind == "mono":
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFamily("monospace")
    size = v.get("fs_title" if kind == "heading" else f"fs_{kind}") or v["fs_body"]
    font.setPixelSize(max(1, int(round(float(size)))))
    if kind == "heading":
        font.setWeight(QFont.Weight(int(v.get("heading_weight") or 600)))
    elif kind == "body":
        font.setWeight(QFont.Weight(int(v.get("body_weight") or 400)))
    return font


def state_color(word: str, theme: Optional[Dict[str, str]] = None) -> Optional[QColor]:
    """A state role (danger / warn / ok / info / meta / note / dim / accent)
    or a legacy Rich word -> the theme's color; None for words with no color
    binding ("bold") and for any non-color var (a font name never leaks)."""
    v = theme if theme is not None else current_theme()
    key = WORD_ROLES.get(word, word)
    if key in T.STATE_ROLES or key in ("dim", "accent", "text", "muted_solid"):
        value = v.get(key)
        return _qcolor(value) if isinstance(value, str) and value.startswith(("#", "rgba(")) else None
    return None


def document_css(theme: Optional[Dict[str, str]] = None) -> str:
    """Default stylesheet for rich-text documents: headings from the type
    scale in the heading face, links in accent, code in the mono slot."""
    v = theme if theme is not None else current_theme()
    rules = [f"a {{ color: {v['accent']}; }}"]
    for level in (1, 2, 3, 4):
        rules.append(f"h{level} {{ font-family: '{v['font_heading']}'; font-size: {v[f'fs_h{level}']}px; "
                     f"font-weight: {v[f'fw_h{level}']}; }}")
    if v.get("font_mono"):
        rules.append(f"code, pre {{ font-family: '{v['font_mono']}'; font-size: {v['fs_mono']}px; }}")
    return "\n".join(rules)


def style_text_pane(pane: QWidget, theme: Optional[Dict[str, str]] = None,
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
    v = theme if theme is not None else current_theme()
    font = make_font(v, "mono" if mono else "body")
    pane.setFont(font)
    doc = pane.document()
    doc.setDocumentMargin(12.0)
    doc.setDefaultStyleSheet(document_css(v))
    height = float(v.get("line_height") or 1.0) * 100.0
    _merge_line_height(pane, height)
    if measure and int(float(v.get("measure") or 0)) and isinstance(pane, QTextEdit):
        width = QFontMetrics(font).averageCharWidth() * int(float(v["measure"]))
        pane.setLineWrapMode(QTextEdit.LineWrapMode.FixedPixelWidth)
        pane.setLineWrapColumnOrWidth(width + 2 * int(doc.documentMargin()))
    if live:
        first_wire = not hasattr(pane, "_kit_live_height")
        pane._kit_live_height = height
        if first_wire:
            pane.textChanged.connect(
                lambda: _merge_line_height(pane, pane._kit_live_height))


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


def _qcolor(c: str) -> QColor:
    """A resolved var -> QColor ("#rrggbb" or "rgba(r, g, b, 0-255)")."""
    if c.startswith("rgba("):
        r, g, b, a = [int(x) for x in c[5:-1].split(",")]
        return QColor(r, g, b, a)
    return QColor(c)


def font_family(theme: Optional[Dict[str, str]] = None, kind: str = "body") -> str:
    """The face a type slot names; an EMPTY mono slot means the platform's
    fixed font, spelled "monospace" (the fontconfig alias) so the kit
    stylesheet, make_font and the document pass all name the same face."""
    v = theme if theme is not None else current_theme()
    family = str(v.get(f"font_{kind}") or "")
    return family or ("monospace" if kind == "mono" else "")


def font_role(widget: QWidget, kind: str) -> QWidget:
    """Declare a widget's type slot ("mono" / "body") on the ONE font
    channel: the kit stylesheet layer sets the face from the tokens
    (`*[kitFont="mono"]`), so a system switch lands what a fresh launch
    lands. setFont under an application stylesheet is order-dependent — the
    stylesheet wins at launch, setFont after a switch (finding b7e68f56)."""
    widget.setProperty("kitFont", kind)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    return widget


def style_document(doc: QTextDocument, theme: Optional[Dict[str, str]] = None) -> None:
    """Land the design system on a PARSED document: headings in the heading
    face at the type scale, code in the mono slot, links in accent. The
    markdown importer ignores the default stylesheet (document_css reaches
    HTML only) and bakes the link color + the fixed face at parse time, so a
    pane runs this pass after every parse and re-parses on the change signal
    (the ReadingPane does both — finding b7e68f56)."""
    v = theme if theme is not None else current_theme()
    heading, mono = font_family(v, "heading"), font_family(v, "mono")
    accent = _qcolor(v["accent"])
    P = QTextFormat.Property
    runs = []                                 # (start, end, format): collected first —
    block = doc.begin()                       # setCharFormat merges fragments under the walk
    while block.isValid():
        bf = block.blockFormat()
        level = min(bf.headingLevel(), 4)
        fenced = bf.hasProperty(P.BlockCodeFence) or bf.nonBreakableLines()
        it = block.begin()
        while not it.atEnd():
            frag = it.fragment()
            fmt = frag.charFormat()
            if level > 0:
                fmt.clearProperty(P.FontSizeAdjustment)
                fmt.setFontFamilies([heading])
                fmt.setProperty(P.FontPixelSize, int(round(float(v[f"fs_h{level}"]))))
                fmt.setFontWeight(int(v[f"fw_h{level}"]))
            elif fenced or fmt.fontFixedPitch():
                fmt.setFontFamilies([mono])
                fmt.setProperty(P.FontPixelSize, int(round(float(v["fs_mono"]))))
            if fmt.isAnchor():
                fmt.setForeground(accent)
            if fmt != frag.charFormat():
                runs.append((frag.position(), frag.position() + frag.length(), fmt))
            it += 1
        block = block.next()
    cursor = QTextCursor(doc)
    cursor.beginEditBlock()
    for start, end, fmt in runs:
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        cursor.setCharFormat(fmt)
    cursor.endEditBlock()
    if runs:
        # Format edits under an in-flight incremental layout can leave trailing
        # blocks unlaid (lineCount 0) while the layout reports itself finished —
        # a short scroll range after a switch; invalidate the whole document.
        doc.markContentsDirty(0, doc.characterCount())
