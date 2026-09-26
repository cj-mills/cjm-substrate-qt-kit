# Changelog

The kit's release record. Each entry names the ruling or work item the
change served, so a version reads back to its decision on the graph.
History before 0.0.7 lives in git and in the graph's session lens.

## 0.0.8 — 2026-09-25

Token schema v1 + the design-system runtime (rulings a439c226 the design
system is data, 8b7351e4 the kit's charter; design DEC 0b1cfd81; work item
95626908): a design system is one tokens.json, resolved into one vocabulary
that ONE Theme lands on the application with ONE change signal.

- `tokens` — schema v1 (the handoff bundle's shape + the six state roles per
  mode, mono / ui font slots, a `scheme` map for OS following, a `reading`
  block, an `icons` declaration); `check` refuses a malformed system naming
  every problem; `resolve` emits the flat vocabulary headlessly; `to_css`
  projects the CSS custom-properties layer for the web side.
- `theme` — rewritten around the `Theme` object: Fusion pinned, the system's
  fonts registered once per process, QPalette + rendered QSS templates (the
  system's own `qss/` or Classical's, then the kit layer `qss/90-kit.qss`
  with the state channel) + recolored indicator icons; `set_mode` /
  `set_system` / `toggle` re-target the one Theme; `on_change(slot)` is the
  one wire (bound methods held weakly, dropped when their widget dies);
  `apply_theme(app, system=None, mode=None, persist=False)` walks the
  preference precedence. RETIRED: the LIGHT / DARK dicts, resolve_theme,
  load_theme, overrides, the `_live` registry, build_qss, heading-scale.
- ONE VOCABULARY: the kit's kebab keys (base / content / content-dim / border
  / raised / selection-bg / selection-content / accent-content) are gone;
  every painter reads the resolved names (bg / text / dim / divider_solid /
  surface / selection_solid / accent …). The state role for muted text is
  `dim`; QSS `role="content-dim"` became `role="dim"`.
- Every kit widget restyles on the signal — PickerList re-renders its rows
  in place (cursor kept), VerdictStrip / ProvenancePane repaint, FormShell
  re-renders its header, KeyHintsOverlay re-renders while visible, FindBar
  repaints its matches, StatusStrip roles follow the stylesheet. Per-widget
  inline QSS chrome retired: the system templates style the chrome.
- `systems/` — Classical and Netrunner vendored as package data (tokens,
  per-system QSS, OFL fonts, Netrunner's painted widgets); `icons/` — the
  Lucide subset (ISC); `widgets` — the component-class helpers (text / tag /
  button / hr / Card / Segmented / elevate / repolish).
- `prefs` — the persisted system + mode (`$XDG_CONFIG_HOME/cjm-substrate/
  theme.json`); precedence args > `CJM_THEME` > file > classical:auto.
- `gallery` — the seed gallery (`python -m cjm_substrate_qt_kit.gallery
  --system --mode`): Controls / Data / Cards / Kit + a system's own page.
- `tools` — `css_to_tokens` (import a web-first system), `icons_pull` (from
  the local Lucide clone, upstream second), `build` (static QSS + CSS).
- `testbed` — variants are now system / mode / fs_body / line_height /
  font_body over the resolved vars (`--systems`, `--modes`, pixel sizes).
- WORD_ROLES stays until the spines emit role words (06d729ab).

## 0.0.7 — 2026-09-25

The Textual retirement (ruling 8b7351e4, work item 21145648): the kit is now
the only foundation library on any Qt app's import path.

- `configform` — `ConfigForm` / `ConfigField`, the manifest-driven config
  form MODEL, ported from the tui-kit's `form` module unchanged in
  semantics. The three consumers (transcription, decomp, correction finetune
  form) rebind here.
- `text` — `tail`, the end-keeping clamp for path-like strings, ported from
  the tui-kit's `viewport` module; the screen-line windowing math it sat
  beside retired with the archive.
- `keyhints.modal_bounds` / `keyhints.open_centered` — the one
  sizing-and-centering path for kit modals; `FormShell.open_sized` and
  `KeyHintsOverlay.open_overlay` both route through it (the second
  modal-sizing copy retired).
- `style.STYLE_COLORS` retired — the pre-theme hex map had no consumer; colors
  resolve through the live theme only.
- `__version__` lives in the package and `pyproject.toml` reads it
  dynamically (one version source).
- `tests/conftest.py` — the offscreen platform pin and the `app` fixture live
  once, not at the head of every widget test.
- ffmpeg declared as a runtime requirement for span playback (description +
  README); the app manifests (work item 165d156a) are its durable home.
- cjm-substrate-tui-kit archived to `cj-mills_archived`; nothing Textual
  remains on a live import path.

Prior releases: 0.0.6 (SpanPlayer over one persistent QAudioSink stream),
0.0.5, 0.0.4 (FormShell, PickerList, HITL chrome), 0.0.3 (theme tokens,
KeymapRegistry, key hints, status strip, find bar), 0.0.2, 0.0.1 (the
loop-thread session base, row styles, the keybinding helper).
