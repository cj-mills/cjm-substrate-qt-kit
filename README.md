# cjm-substrate-qt-kit

<!-- generated from the context graph by `cjm-context-graph readme` — do not edit by hand; edit the graph (the urge to hand-edit = move it on-graph) -->

Shared foundations for the PySide6 application lane (DEC c4b0d6e5): LoopThreadSession (a private asyncio loop behind a Qt shell — GraphSession and CapabilitySession both subclass it), the row-style palette (STYLE_COLORS/apply_row_style), and the keybinding helper. Every piece extracted at its first real duplication between cjm-graph-workbench-qt and cjm-transcription-qt — the kit grows by demand, never speculation. Semantic theming (a94fa56a) and in-app config (812beb51) land here at their demand points.

## Modules

- **`cjm_substrate_qt_kit.__init__`** — Shared foundations for the PySide6 application lane — extracted at first duplication (DEC dcf8a712).
- **`cjm_substrate_qt_kit.findbar`** — The lane's find-bar universal (the Ctrl-F half of signal c7955f25).
- **`cjm_substrate_qt_kit.formdialog`** — Kit FormShell (work item d55292f9): the frameless modal FORM chrome —
- **`cjm_substrate_qt_kit.hitl`** — Kit HITL confirm chrome (work item 55bcc3c5, the payload-agnostic half of
- **`cjm_substrate_qt_kit.keyhints`** — Keyboard-hints surface: the ?-overlay + contextual hint line (DEC 2a42c028).
- **`cjm_substrate_qt_kit.keymap`** — KeymapRegistry: the QAction layer from the toolbox verdict (DEC d55f1d0f).
- **`cjm_substrate_qt_kit.keys`** — The keybinding helper both shells grew independently.
- **`cjm_substrate_qt_kit.layout`** — Layout roles for the application lane — the FastHTML-era framework's Qt
- **`cjm_substrate_qt_kit.loopthread`** — The loop-thread session base: a private asyncio loop behind a Qt shell.
- **`cjm_substrate_qt_kit.pickerlist`** — Kit PickerList (work item 8d29f0f0): the native list PAGE the painted
- **`cjm_substrate_qt_kit.player`** — Span playback via QMediaPlayer — the Qt lane's one audio component (kit
- **`cjm_substrate_qt_kit.statusstrip`** — StatusStrip: the footer's slot model (DEC 2a42c028).
- **`cjm_substrate_qt_kit.style`** — Row-style vocabulary for the lane's list widgets.
- **`cjm_substrate_qt_kit.testbed`** — Readability test-bed: error-seeded reading trials measuring which theme
- **`cjm_substrate_qt_kit.testbed_corpus`** — Bundled clean-prose corpus for the readability test-bed.
- **`cjm_substrate_qt_kit.theme`** — Semantic theme tokens for the lane: one flat dict -> QPalette + QSS + fonts.

## API

### `cjm_substrate_qt_kit.findbar`

- `FindBar` _class_ — Incremental find over an attached text pane. While the bar is open the

### `cjm_substrate_qt_kit.formdialog`

- `FormShell` _class_ — Frameless modal shell: head (QTextBrowser, fixed) / body (PickerList,

### `cjm_substrate_qt_kit.hitl`

- `HitlPanel` _class_ — The composed confirm panel: worklist (stretch) over the verdict strip
- `ProposalWorklist` _class_ — The proposal list page: items above (a kit PickerList), the host's
- `ProvenancePane` _class_ — Key/value provenance — a two-column table of whatever the lane's
- `VerdictStrip` _class_ — The derived-verdict status strip: one line per tier, each verdict
- `fmt_ts` _function_ — Source-seconds as mm:ss.s — the worklist's span column.
- `worklist_row` _function_ — Project one item into a picker row: tier glyph (? / ??), the category

### `cjm_substrate_qt_kit.keyhints`

- `KeyHintsOverlay` _class_ — ?-toggled keyboard-hints overlay. Modal + frameless, centered over
- `column_count` _function_ — Responsive column count: what the CONTAINER width affords (layout
- `group_entries` _function_ — [{verb,label,key,group}] -> [(group, entries)] in first-seen group
- `hint_line` _function_ — Project the pinned verbs (in pin order, capped at limit) into the
- `is_close_anchor` _function_ — True for the close affordance modal_header paints — the dialog's
- `keycaps` _function_ — Public key-cap renderer — the overlay's chip grammar for OTHER
- `modal_header` _function_ — A kit modal's title row: the title at left, the mouse CLOSE
- `render_hints_html` _function_ — The overlay's document: sections distributed across columns in

### `cjm_substrate_qt_kit.keymap`

- `KeymapRegistry` _class_ — Declarative verb table -> live QActions on an owner widget.

### `cjm_substrate_qt_kit.keys`

- `bind` _function_ — One QShortcut: `key` on `parent` (default: the owner window) fires `fn`.

### `cjm_substrate_qt_kit.layout`

- `afford` _function_ — R3 container affordance: how many fixed-width units fit in the
- `classify` _function_ — One geometry -> its three role ids: {"mode", "shape", "height"}.
- `height_tier` _function_ — Absolute height -> height-tier role id ("H1".."H4").
- `mode` _function_ — Width -> mode role id ("M1".."M6").
- `shape` _function_ — Aspect ratio -> shape role id ("S1".."S6").

### `cjm_substrate_qt_kit.loopthread`

- `LoopThreadSession` _class_ — Owns one daemon asyncio loop thread; subclasses put their subsystem's

### `cjm_substrate_qt_kit.pickerlist`

- `PickerList` _class_ — The kit list page: native list above, budget-reserved detail below.
- `SpanRowDelegate` _class_ — Paint one row's rich-text fragment (the _ROW_HTML data) through a
- `spans_to_html` _function_ — Project style-worded spans into one QTextDocument-ready fragment.

### `cjm_substrate_qt_kit.player`

- `SpanPlayer` _class_ — Play/stop one file span at a time; replay gestures re-enter, escape

### `cjm_substrate_qt_kit.statusstrip`

- `StatusStrip` _class_ — Two-row footer: chips + readout + transient above, hint line below

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
