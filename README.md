# cjm-substrate-qt-kit

<!-- generated from the context graph by `cjm-context-graph readme` — do not edit by hand; edit the graph (the urge to hand-edit = move it on-graph) -->

Shared foundations for the PySide6 application lane (DEC c4b0d6e5): LoopThreadSession (a private asyncio loop behind a Qt shell — GraphSession and CapabilitySession both subclass it), the row-style palette (STYLE_COLORS/apply_row_style), and the keybinding helper. Every piece extracted at its first real duplication between cjm-graph-workbench-qt and cjm-transcription-qt — the kit grows by demand, never speculation. Semantic theming (a94fa56a) and in-app config (812beb51) land here at their demand points.

## Modules

- **`cjm_substrate_qt_kit.__init__`** — Shared foundations for the PySide6 application lane — extracted at first duplication (DEC dcf8a712).
- **`cjm_substrate_qt_kit.findbar`** — The lane's find-bar universal (the Ctrl-F half of signal c7955f25).
- **`cjm_substrate_qt_kit.keymap`** — KeymapRegistry: the QAction layer from the toolbox verdict (DEC d55f1d0f).
- **`cjm_substrate_qt_kit.keys`** — The keybinding helper both shells grew independently.
- **`cjm_substrate_qt_kit.loopthread`** — The loop-thread session base: a private asyncio loop behind a Qt shell.
- **`cjm_substrate_qt_kit.style`** — Row-style vocabulary for the lane's list widgets.
- **`cjm_substrate_qt_kit.testbed`** — Readability test-bed: error-seeded reading trials measuring which theme
- **`cjm_substrate_qt_kit.testbed_corpus`** — Bundled clean-prose corpus for the readability test-bed.
- **`cjm_substrate_qt_kit.theme`** — Semantic theme tokens for the lane: one flat dict -> QPalette + QSS + fonts.

## API

### `cjm_substrate_qt_kit.findbar`

- `FindBar` _class_ — Incremental find over an attached text pane.

### `cjm_substrate_qt_kit.keymap`

- `KeymapRegistry` _class_ — Declarative verb table -> live QActions on an owner widget.

### `cjm_substrate_qt_kit.keys`

- `bind` _function_ — One QShortcut: `key` on `parent` (default: the owner window) fires `fn`.

### `cjm_substrate_qt_kit.loopthread`

- `LoopThreadSession` _class_ — Owns one daemon asyncio loop thread; subclasses put their subsystem's

### `cjm_substrate_qt_kit.style`

- `apply_row_style` _function_ — Map a row's style words onto a list item (color words + bold).

### `cjm_substrate_qt_kit.testbed`

- `ClickPane` _class_ — Read-only pane reporting the whitespace-token index of clicks that
- `TrialWindow` _class_ — The trial loop: render the paragraph under its variant, take the
- `build_trials` _function_ — The trial plan: variants covered evenly (shuffled round-robin over the
- `build_variants` _function_ — Cross the sweep dimensions into variant dicts. Defaults reproduce the
- `load_paragraphs` _function_ — Prose paragraphs from a markdown file: fence markers stripped (fence
- `main` _function_ — CLI: run trials over a markdown file, or summarize result JSONLs.
- `seed_error` _function_ — Apply one error class to a token list; (mutated_words, target_token,
- `summarize` _function_ — Catch rate + latency per dimension marginal, per variant cell, per

### `cjm_substrate_qt_kit.theme`

- `apply_theme` _function_ — THE entry point: resolve the theme and land palette + QSS + ui font on
- `build_palette` _function_ — Project the palette roles onto QPalette so NATIVE widgets follow the
- `build_qss` _function_ — Generate the lane's QSS layer: chrome polish + dynamic-property state
- `current_theme` _function_ — The theme apply_theme last landed (default-resolved before any apply).
- `document_css` _function_ — Default stylesheet for rich-text documents (setDefaultStyleSheet):
- `load_theme` _function_ — Read a theme-as-data JSON file (a flat token dict): themes are shared
- `make_font` _function_ — Build the theme's font for a slot: "body" / "mono" / "ui". An empty
- `resolve_theme` _function_ — Merge override tokens onto the built-in pair member for the scheme
- `state_color` _function_ — Resolve a legacy style word or a semantic role to the theme's color
- `style_text_pane` _function_ — Reading-quality setup for a text pane (QTextEdit / QTextBrowser /

## Dependencies

**Depends on:** `PySide6`
**Used by:** `cjm-graph-workbench-qt`, `cjm-session-scratchpad-qt`, `cjm-transcript-correction-qt`, `cjm-transcript-decomp-qt`, `cjm-transcription-qt`, `cjm-workflow-hub-qt`
