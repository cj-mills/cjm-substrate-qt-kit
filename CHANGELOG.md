# Changelog

The kit's release record. Each entry names the ruling or work item the
change served, so a version reads back to its decision on the graph.
History before 0.0.7 lives in git and in the graph's session lens.

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
