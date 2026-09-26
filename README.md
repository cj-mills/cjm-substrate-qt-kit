# cjm-substrate-qt-kit

<!-- generated from the context graph by `cjm-context-graph readme` — do not edit by hand; edit the graph (the urge to hand-edit = move it on-graph) -->

The ONE Qt foundation library for the cjm-substrate application lane (ruling 8b7351e4), in three strata: (a) the design-system runtime — semantic theme tokens as data -> QPalette + QSS + fonts; (b) the app shell (ruling 2bae2cc1, landing); (c) the chrome every app shares — the loop-thread session base, KeymapRegistry, key hints + the modal grammar, the status strip, find bar, picker list, form shell + the manifest-driven config-form model, the HITL panel, the span player (requires ffmpeg on PATH), and text clamps. Born at first duplication between the workbench and the transcription shell (DEC dcf8a712); grown by demand, never speculation. The Textual-era tui-kit's live pieces (ConfigForm, tail) ported here 2026-09-25 and the tui-kit archived — nothing Textual remains on any app's import path.

## Modules

- **`cjm_substrate_qt_kit.__init__`** — The ONE Qt foundation library for the cjm-substrate application lane (ruling 8b7351e4).
- **`cjm_substrate_qt_kit.configform`** — Manifest-driven config form MODEL — the schema half of every kit form.
- **`cjm_substrate_qt_kit.findbar`** — The lane's find-bar universal (the Ctrl-F half of signal c7955f25).
- **`cjm_substrate_qt_kit.formdialog`** — Kit FormShell (work item d55292f9): the frameless modal FORM chrome —
- **`cjm_substrate_qt_kit.gallery`** — The gallery SEED: every component class under any design system + mode
- **`cjm_substrate_qt_kit.hitl`** — Kit HITL confirm chrome (work item 55bcc3c5, the payload-agnostic half of
- **`cjm_substrate_qt_kit.icons`** — Icons recolored at runtime from the vendored Lucide subset (ISC; the
- **`cjm_substrate_qt_kit.keyhints`** — Keyboard-hints surface: the ?-overlay + contextual hint line (DEC 2a42c028).
- **`cjm_substrate_qt_kit.keymap`** — KeymapRegistry: the QAction layer from the toolbox verdict (DEC d55f1d0f).
- **`cjm_substrate_qt_kit.keys`** — The keybinding helper both shells grew independently.
- **`cjm_substrate_qt_kit.layout`** — Layout roles for the application lane — the FastHTML-era framework's Qt
- **`cjm_substrate_qt_kit.loopthread`** — The loop-thread session base: a private asyncio loop behind a Qt shell.
- **`cjm_substrate_qt_kit.pickerlist`** — Kit PickerList (work item 8d29f0f0): the native list PAGE the painted
- **`cjm_substrate_qt_kit.player`** — Span playback over ONE persistent audio stream — the Qt lane's one audio
- **`cjm_substrate_qt_kit.prefs`** — The persisted theme choice — system + mode — and its precedence.
- **`cjm_substrate_qt_kit.statusstrip`** — StatusStrip: the footer's slot model (DEC 2a42c028).
- **`cjm_substrate_qt_kit.style`** — Row-style vocabulary for the lane's list widgets.
- **`cjm_substrate_qt_kit.systems.__init__`** — The design systems the kit ships as DATA (ruling a439c226): one directory
- **`cjm_substrate_qt_kit.systems.classical.__init__`** — Classical — the first seed system: outlined serif (Cormorant Garamond
- **`cjm_substrate_qt_kit.systems.netrunner.__init__`** — Netrunner — the second seed system: hard-edged terminal look (Silkscreen
- **`cjm_substrate_qt_kit.systems.netrunner.widgets`** — Netrunner's painted widgets: what QSS cannot draw (chamfered header bars,
- **`cjm_substrate_qt_kit.testbed`** — Readability test-bed: error-seeded reading trials measuring which theme
- **`cjm_substrate_qt_kit.testbed_corpus`** — Bundled clean-prose corpus for the readability test-bed.
- **`cjm_substrate_qt_kit.text`** — Text clamps for one-line surfaces — path-like strings keep their END.
- **`cjm_substrate_qt_kit.theme`** — The design-system RUNTIME: ONE Theme object, ONE change signal (ruling
- **`cjm_substrate_qt_kit.tokens`** — Token schema v1 — a design system as DATA, resolved headlessly (ruling
- **`cjm_substrate_qt_kit.tools.__init__`** — Kit tools (run as modules):
- **`cjm_substrate_qt_kit.tools.build`** — Build the static projections of a design system, no QApplication needed:
- **`cjm_substrate_qt_kit.tools.css_to_tokens`** — Import a web-first design system's CSS into a schema-v1 tokens file.
- **`cjm_substrate_qt_kit.tools.icons_pull`** — Pull named Lucide icons into the kit's vendored subset (or a system's own
- **`cjm_substrate_qt_kit.widgets`** — Small helpers that map the design system's component classes onto Qt —

## API

### `cjm_substrate_qt_kit.configform`

- `ConfigField` _class_ — One schema property as an editable form row.
- `ConfigForm` _class_ — A capability's editable config, derived from its manifest config_schema.

### `cjm_substrate_qt_kit.findbar`

- `FindBar` _class_ — Incremental find over an attached text pane. While the bar is open the

### `cjm_substrate_qt_kit.formdialog`

- `FormShell` _class_ — Frameless modal shell: head (QTextBrowser, fixed) / body (PickerList,

### `cjm_substrate_qt_kit.gallery`

- `Gallery` _class_
- `field` _function_
- `main` _function_
- `row` _function_
- `section` _function_

### `cjm_substrate_qt_kit.hitl`

- `HitlPanel` _class_ — The composed confirm panel: worklist (stretch) over the verdict strip
- `ProposalWorklist` _class_ — The proposal list page: items above (a kit PickerList), the host's
- `ProvenancePane` _class_ — Key/value provenance — a two-column table of whatever the lane's
- `VerdictStrip` _class_ — The derived-verdict status strip: one line per tier, each verdict
- `fmt_ts` _function_ — Source-seconds as mm:ss.s — the worklist's span column.
- `worklist_row` _function_ — Project one item into a picker row: tier glyph (? / ??), the category

### `cjm_substrate_qt_kit.icons`

- `IconSet` _class_ — Named SVG icons -> recolored SVG text, files (for QSS url()), QIcons.

### `cjm_substrate_qt_kit.keyhints`

- `KeyHintsOverlay` _class_ — ?-toggled keyboard-hints overlay. Modal + frameless, centered over
- `column_count` _function_ — Responsive column count: what the CONTAINER width affords (layout
- `group_entries` _function_ — [{verb,label,key,group}] -> [(group, entries)] in first-seen group
- `hint_line` _function_ — Project the pinned verbs (in pin order, capped at limit) into the
- `is_close_anchor` _function_ — True for the close affordance modal_header paints — the dialog's
- `keycaps` _function_ — Public key-cap renderer — the overlay's chip grammar for OTHER
- `modal_bounds` _function_ — (avail_w, avail_h) a kit modal may occupy: the owner's size less a
- `modal_header` _function_ — A kit modal's title row: the title at left, the mouse CLOSE
- `open_centered` _function_ — Open a kit modal centered over its owner at (width, height) capped by
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

- `SpanPlayer` _class_ — Play/stop one file span at a time over the persistent stream; replay
- `decode_command` _function_ — The ffmpeg invocation for one span: input-side seek (fast), `-t` bounds

### `cjm_substrate_qt_kit.prefs`

- `parse_env` _function_ — `CJM_THEME` grammar: `<system>`, `<system>:<mode>` or `:<mode>`.
- `prefs_path` _function_ — `$CJM_KIT_PREFS`, else `<config dir>/cjm-substrate/theme.json` where
- `read` _function_ — The stored choice ({"system", "mode"}) — an empty dict when absent or unreadable.
- `resolve` _function_ — (system, mode, source) after the precedence walk. `source` names where
- `write` _function_ — Persist the choice (atomic replace); returns the file written.

### `cjm_substrate_qt_kit.statusstrip`

- `StatusStrip` _class_ — Two-row footer: chips + readout + transient above, hint line below

### `cjm_substrate_qt_kit.style`

- `apply_row_style` _function_ — Map a row's style words onto a list item (color words + bold).

### `cjm_substrate_qt_kit.systems.__init__`

- `available` _function_ — Every vendored system slug (a directory carrying a tokens.json).
- `locate` _function_ — The directory of a system: a vendored slug, a directory holding a
- `tokens_path` _function_

### `cjm_substrate_qt_kit.systems.netrunner.widgets`

- `ChamferHeader` _class_ — Solid fill bar with the top-left corner cut. Colors come from the live theme.
- `Panel` _class_ — Chamfered header + surface body. Click the header to collapse.
- `gallery_page` _function_ — The system's own gallery tab: the panel + chamfer grammar the shared
- `para` _function_
- `section_title` _function_
- `tracked` _function_ — Display / section label with letter-spacing (QSS has none).

### `cjm_substrate_qt_kit.testbed`

- `ClickPane` _class_ — Read-only pane reporting the whitespace-token index of clicks that
- `TrialWindow` _class_ — The trial loop: render the paragraph under its variant, take the
- `build_trials` _function_ — The trial plan: variants covered evenly (shuffled round-robin over the
- `build_variants` _function_ — Cross the sweep dimensions into variant dicts. Defaults reproduce the
- `load_paragraphs` _function_ — Prose paragraphs from a markdown file: fence markers stripped (fence
- `main` _function_ — CLI: run trials over a markdown file, or summarize result JSONLs.
- `seed_error` _function_ — Apply one error class to a token list; (mutated_words, target_token,
- `summarize` _function_ — Catch rate + latency per dimension marginal, per variant cell, per

### `cjm_substrate_qt_kit.text`

- `tail` _function_ — Clamp a string to width keeping its END.

### `cjm_substrate_qt_kit.theme`

- `Theme` _class_ — theme = Theme.apply(app) — or apply_theme(app), the module-level door.
- `apply_theme` _function_ — Module-level door to Theme.apply (the name every app's launch calls).
- `build_palette` _function_ — Project the vars onto QPalette so NATIVE widgets follow the theme (QSS
- `current` _function_ — The live Theme (None before apply_theme).
- `current_theme` _function_ — The live resolved vars; Classical's first mode before any apply.
- `document_css` _function_ — Default stylesheet for rich-text documents: headings from the type
- `make_font` _function_ — The system's font for a slot: "body" / "mono" / "ui" / "heading",
- `on_change` _function_ — Subscribe `slot(theme)` to every mode / system change — the ONE wire,
- `render_qss` _function_ — Headless: tokens + mode -> the final stylesheet. The system's templates
- `state_color` _function_ — A state role (danger / warn / ok / info / meta / note / dim / accent)
- `style_text_pane` _function_ — Reading-quality setup for a text pane (QTextEdit / QTextBrowser /

### `cjm_substrate_qt_kit.tokens`

- `SchemaError` _class_ — A tokens file that violates schema v1 — every problem listed, so one
- `check` _function_ — Refuse a malformed system loudly: every missing / mistyped field named
- `load` _function_ — Read a tokens file (JSON). `check` it before resolving anything.
- `mix` _function_ — Flatten `fg` at opacity `t` over `bg` -> a solid hex (QPalette, painters,
- `mode_for_scheme` _function_ — The mode the system maps an OS scheme ("light" / "dark") onto — None
- `modes` _function_
- `resolve` _function_ — tokens + mode -> the flat vocabulary every projection reads: the QSS
- `rgba` _function_ — QSS rgba() with a 0-255 alpha (the form every Qt 6 version parses).
- `slug` _function_ — The system's file-system / preference slug: lower-case, spaces -> dashes.
- `to_css` _function_ — The CSS custom-properties layer for a system — the ruling's second
- `to_hex` _function_

### `cjm_substrate_qt_kit.tools.build`

- `main` _function_

### `cjm_substrate_qt_kit.tools.css_to_tokens`

- `convert` _function_
- `darker` _function_
- `family` _function_
- `main` _function_
- `parse_root` _function_
- `px` _function_
- `ramp` _function_

### `cjm_substrate_qt_kit.tools.icons_pull`

- `local_clone` _function_
- `main` _function_
- `pull` _function_

### `cjm_substrate_qt_kit.widgets`

- `Card` _class_ — The card class — bordered, unfilled by default. Card(kicker=, title=,
- `Segmented` _class_ — The segmented control — exclusive checkable buttons sharing hairlines.
- `button` _function_
- `elevate` _function_ — A drop shadow at the system's strength (shadow + shadow_strength vars).
- `hr` _function_
- `kicker` _function_
- `repolish` _function_ — Call after changing a dynamic property so QSS re-matches.
- `tag` _function_
- `text` _function_

## Dependencies

**Depends on:** `PySide6`
**Used by:** `cjm-graph-workbench-qt`, `cjm-session-scratchpad-qt`, `cjm-transcript-correction-qt`, `cjm-transcript-decomp-qt`, `cjm-transcription-qt`, `cjm-workflow-hub-qt`
