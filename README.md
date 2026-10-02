# cjm-substrate-qt-kit

<!-- generated from the context graph by `cjm-context-graph readme` — do not edit by hand; edit the graph (the urge to hand-edit = move it on-graph) -->

The ONE Qt foundation library for the cjm-substrate application lane (ruling 8b7351e4), in three strata: (a) the design-system runtime — semantic theme tokens as data -> QPalette + QSS + fonts; (b) the app shell (ruling 2bae2cc1, landing); (c) the chrome every app shares — the loop-thread session base, KeymapRegistry, key hints + the modal grammar, the status strip, find bar, picker list, form shell + the manifest-driven config-form model, the HITL panel, the span player (requires ffmpeg on PATH), and text clamps. Born at first duplication between the workbench and the transcription shell (DEC dcf8a712); grown by demand, never speculation. The Textual-era tui-kit's live pieces (ConfigForm, tail) ported here 2026-09-25 and the tui-kit archived — nothing Textual remains on any app's import path.

## Modules

- **`cjm_substrate_qt_kit.__init__`** — The ONE Qt foundation library for the cjm-substrate application lane (ruling 8b7351e4).
- **`cjm_substrate_qt_kit.bridge`** — The Future -> Signal bridge (ruling 2bae2cc1 (2)): a concurrent Future
- **`cjm_substrate_qt_kit.configform`** — Manifest-driven config form MODEL — the schema half of every kit form.
- **`cjm_substrate_qt_kit.findbar`** — The lane's find-bar universal (the Ctrl-F half of signal c7955f25).
- **`cjm_substrate_qt_kit.formdialog`** — Kit FormShell (work item d55292f9): the frameless modal FORM chrome —
- **`cjm_substrate_qt_kit.frame`** — The window frame — client-side decorations as a shell surface (ruling
- **`cjm_substrate_qt_kit.gallery`** — The gallery SEED: every component class under any design system + mode
- **`cjm_substrate_qt_kit.hitl`** — Kit HITL confirm chrome (work item 55bcc3c5, the payload-agnostic half of
- **`cjm_substrate_qt_kit.icons`** — Icons recolored at runtime from the vendored Lucide subset (ISC; the
- **`cjm_substrate_qt_kit.jobs`** — The JOB SEAT (ruling 2bae2cc1 (5)): a progress surface for long-running
- **`cjm_substrate_qt_kit.keyhints`** — Keyboard-hints surface: the ?-overlay + contextual hint line (DEC 2a42c028).
- **`cjm_substrate_qt_kit.keymap`** — KeymapRegistry: the QAction layer from the toolbox verdict (DEC d55f1d0f).
- **`cjm_substrate_qt_kit.keys`** — The keybinding helper both shells grew independently — plus the shell's
- **`cjm_substrate_qt_kit.launch`** — Launch resolution (ruling 2bae2cc1 (4)): where an app's launch values —
- **`cjm_substrate_qt_kit.layout`** — Layout roles for the application lane — the FastHTML-era framework's Qt
- **`cjm_substrate_qt_kit.loopthread`** — The loop-thread session base: a private asyncio loop behind a Qt shell.
- **`cjm_substrate_qt_kit.modal`** — ONE kit modal frame (ruling d1e3043e (2); finding 533d53d0).
- **`cjm_substrate_qt_kit.pickerlist`** — Kit PickerList (work item 8d29f0f0): the native list PAGE the painted
- **`cjm_substrate_qt_kit.player`** — Span playback over ONE persistent audio stream — the Qt lane's one audio
- **`cjm_substrate_qt_kit.prefs`** — The persisted theme choice — system + mode — and its precedence.
- **`cjm_substrate_qt_kit.readingpane`** — The reading pane: a QTextBrowser with the keyboard reading contract the
- **`cjm_substrate_qt_kit.roundtrip`** — The switch-equals-launch check (finding b7e68f56): a design-system or mode
- **`cjm_substrate_qt_kit.sessionkey`** — Session-key adoption + the ONE mint (ruling 2bae2cc1 (3)).
- **`cjm_substrate_qt_kit.shell`** — The APP SHELL (ruling 2bae2cc1; the decorations ruling d1e3043e): every
- **`cjm_substrate_qt_kit.statusstrip`** — StatusStrip: the footer's slot model (DEC 2a42c028).
- **`cjm_substrate_qt_kit.style`** — Row-style vocabulary for the lane's list widgets.
- **`cjm_substrate_qt_kit.systems.__init__`** — The Qt half of each design system (ruling a439c226, design 0858bbd0): a
- **`cjm_substrate_qt_kit.systems.classical.__init__`** — Classical — the first seed system: outlined serif (Cormorant Garamond
- **`cjm_substrate_qt_kit.systems.netrunner.__init__`** — Netrunner — the second seed system: hard-edged terminal look (Silkscreen
- **`cjm_substrate_qt_kit.systems.netrunner.widgets`** — Netrunner's painted widgets: what QSS cannot draw (chamfered header bars,
- **`cjm_substrate_qt_kit.testbed`** — Readability test-bed: error-seeded reading trials measuring which theme
- **`cjm_substrate_qt_kit.testbed_corpus`** — Bundled clean-prose corpus for the readability test-bed.
- **`cjm_substrate_qt_kit.text`** — Text clamps for one-line surfaces — path-like strings keep their END.
- **`cjm_substrate_qt_kit.theme`** — The design-system RUNTIME: ONE Theme object, ONE change signal (ruling
- **`cjm_substrate_qt_kit.tools.__init__`** — Kit tools (run as modules):
- **`cjm_substrate_qt_kit.tools.build`** — Build the static Qt projections of a design system, no QApplication
- **`cjm_substrate_qt_kit.tools.icons_pull`** — Pull named Lucide icons into the kit's vendored subset (or a system's own
- **`cjm_substrate_qt_kit.widgets`** — Small helpers that map the design system's component classes onto Qt —

## API

### `cjm_substrate_qt_kit.bridge`

- `FutureBridge` _class_ — watch(future, on_result, on_error) — the callbacks run on the bridge's

### `cjm_substrate_qt_kit.configform`

- `ConfigField` _class_ — One schema property as an editable form row.
- `ConfigForm` _class_ — A capability's editable config, derived from its manifest config_schema.

### `cjm_substrate_qt_kit.findbar`

- `FindBar` _class_ — Incremental find over an attached text pane. While the bar is open the

### `cjm_substrate_qt_kit.formdialog`

- `FormShell` _class_ — Frameless modal shell on the kit modal frame: head (QTextBrowser,

### `cjm_substrate_qt_kit.frame`

- `EdgeGrip` _class_ — One invisible strip laid OVER the frame's outer band (top / bottom /
- `FramedWindow` _class_ — The frameless, translucent HOST whose central widget is the painted
- `ShellFrame` _class_ — The painted frame: title bar, then the chrome slot (menubar, toolbars),
- `TitleBar` _class_ — The frame's top row: title left, the window verbs right, a leading
- `edge_value` _function_ — Qt.Edge flags as an int (PySide's flag enums carry .value).
- `hint_system_scheme` _function_ — The fallback's mode hint: when the window manager paints the frame,
- `verb_button` _function_ — One window verb: a QToolButton[role="window-verb"][verb=<verb>] the
- `verb_icon` _function_ — A window-verb glyph inked by the live system (`titlebar_ink`): the

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

### `cjm_substrate_qt_kit.jobs`

- `Job` _class_ — One running job: progress(done, total) moves the bar, finish() /
- `JobSeat` _class_ — The rows of running jobs; hidden while empty. `job_done(label, text,
- `fmt_elapsed` _function_

### `cjm_substrate_qt_kit.keyhints`

- `KeyHintsOverlay` _class_ — ?-toggled keyboard-hints overlay. Modal + frameless on the kit modal
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
- `enter_twins` _function_ — A key and its numpad twin: "Return" -> ["Return", "Enter"],

### `cjm_substrate_qt_kit.launch`

- `LaunchConfig` _class_ — The resolved values + where each came from ("workspace" / "prefs" /
- `LaunchError` _class_ — A workspace was named (flag or env) but is not a workspace root.
- `app_config_path` _function_
- `config_dir` _function_ — `$XDG_CONFIG_HOME` / `~/.config` (POSIX) or `%APPDATA%` (Windows), under
- `persist` _function_ — Merge `values` into the persisted in-app config (the in-app settings
- `read_json` _function_ — A JSON object, defensively: {} when absent, unreadable or not an object.
- `record` _function_ — Merge `values` into the workspace's launch record for `app_id` (a
- `resolve` _function_ — Walk the precedence for every key named (the union of the record, the
- `workspace_record_path` _function_
- `workspace_root` _function_ — The workspace root: `explicit` > CJM_WORKSPACE > None. A named
- `write_json` _function_ — Atomic replace (tmp + rename).

### `cjm_substrate_qt_kit.layout`

- `afford` _function_ — R3 container affordance: how many fixed-width units fit in the
- `classify` _function_ — One geometry -> its three role ids: {"mode", "shape", "height"}.
- `height_tier` _function_ — Absolute height -> height-tier role id ("H1".."H4").
- `mode` _function_ — Width -> mode role id ("M1".."M6").
- `shape` _function_ — Aspect ratio -> shape role id ("S1".."S6").

### `cjm_substrate_qt_kit.loopthread`

- `LoopThreadSession` _class_ — Owns one daemon asyncio loop thread; subclasses put their subsystem's
- `op_write` _function_ — One session write gesture = ONE op clock window (design 8f6f2343, amendment efd659a1's

### `cjm_substrate_qt_kit.modal`

- `Confirm` _class_ — A question with two answers; `answer()` is True on the affirmative.
- `Dialog` _class_ — A widget-built kit dialog: header (title + close), a `content` layout
- `ModalFrame` _class_ — The translucent host + the painted frame. Subclasses parent their
- `ModalHeader` _class_ — A widget-built modal's title row: the title left, the close verb
- `Notice` _class_ — A message with one button.
- `TextPrompt` _class_ — One line of text: a label, a field, OK (default) / Cancel. The value
- `ask_text` _function_ — Blocking text prompt (the kit's QInputDialog.getText): the text on
- `center_over_owner` _function_ — Move the dialog to the owner's center (no-op when ownerless).
- `confirm` _function_ — Blocking yes/no (the kit's QMessageBox.question).
- `modal_bounds` _function_ — (avail_w, avail_h) a kit modal may occupy: the owner's size less a
- `notice` _function_ — Blocking message (the kit's QMessageBox.information).
- `open_centered` _function_ — Open a kit modal centered over its owner at (width, height) capped by

### `cjm_substrate_qt_kit.pickerlist`

- `PickerList` _class_ — The kit list page: native list above, budget-reserved detail below.
- `SpanRowDelegate` _class_ — Paint one row's rich-text fragment (the _ROW_HTML data) through a
- `spans_to_html` _function_ — Project style-worded spans into one QTextDocument-ready fragment.

### `cjm_substrate_qt_kit.player`

- `SpanPlayer` _class_ — Play/stop one file span at a time over the persistent stream; replay
- `decode_command` _function_ — The ffmpeg invocation for one span: input-side seek (fast), `-t` bounds

### `cjm_substrate_qt_kit.prefs`

- `decorations` _function_ — (decorations, source) after the precedence walk: explicit >
- `parse_env` _function_ — `CJM_THEME` grammar: `<system>`, `<system>:<mode>` or `:<mode>`.
- `prefs_path` _function_ — `$CJM_KIT_PREFS`, else `<config dir>/cjm-substrate/theme.json` where
- `read` _function_ — The stored choices ({"system", "mode", "decorations"} — whichever are
- `resolve` _function_ — (system, mode, source) after the precedence walk. `source` names where
- `write` _function_ — Persist the theme choice (atomic replace, the other keys kept);
- `write_decorations` _function_ — Persist the decorations choice ("client" / "system"), the theme keys kept.

### `cjm_substrate_qt_kit.readingpane`

- `ReadingPane` _class_

### `cjm_substrate_qt_kit.roundtrip`

- `Diff` _class_
- `check_switch` _function_ — Run both legs for systems `a` -> `b` -> `a` and return every differing
- `diff_images` _function_ — (differing pixel count, bbox) — (0, None) when identical; (-1, None)
- `grab` _function_ — Grab every page of `window` (ARGB32, comparable across grabs).
- `settle` _function_ — Let polish, layout and deferred restores (seat restores ride the next
- `tabs_of` _function_ — Every tab of `tabs` as a page (the gallery's shape:

### `cjm_substrate_qt_kit.sessionkey`

- `active_key` _function_ — The live sitting: CJM_SESSION, else the workspace pointer.
- `adopt` _function_ — Adopt the live key for this process: (key, source). An inherited
- `boot_prompt` _function_ — The start-ritual boot prompt the mint gesture puts on the clipboard.
- `is_repeat` _function_ — A just-minted live key means this press is a key repeat / double tap
- `journaled_ops_for` _function_ — Every journaled op attributed to `key` besides its own registrations —
- `mint` _function_ — The ONE mint: refuse a repeat, adopt the new key BEFORE the journaled
- `mint_signal` _function_ — The transcript-mapping PREFIX the boot prompt must carry (substring
- `new_key` _function_ — A session key IS its mint timestamp (local time).
- `parse_key` _function_ — The mint time of a key; None for legacy / free-form names.
- `pointer_path` _function_ — `.cjm/current-session` beside the WRITES journal (journal_paths[0]) —
- `read_pointer` _function_ — The pointed key, or None (a missing / empty pointer is not an error).
- `write_pointer` _function_ — Point the file at `key` ATOMICALLY (tmp + replace: a reader never sees

### `cjm_substrate_qt_kit.shell`

- `AppShell` _class_
- `add_theme_menu` _function_ — The in-app theme switcher (item 812beb51): Design system + Mode radio

### `cjm_substrate_qt_kit.statusstrip`

- `StatusStrip` _class_ — Two-row footer: chips + readout + transient above, hint line below

### `cjm_substrate_qt_kit.style`

- `apply_row_style` _function_ — Map a row's style words onto a list item (color words + bold).

### `cjm_substrate_qt_kit.systems.__init__`

- `qss_dir` _function_ — A trial system's own `qss/` beside its tokens.json first, else the

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
- `font_family` _function_ — The face a type slot names; an EMPTY mono slot means the platform's
- `font_role` _function_ — Declare a widget's type slot ("mono" / "body") on the ONE font
- `make_font` _function_ — The system's font for a slot: "body" / "mono" / "ui" / "heading",
- `on_change` _function_ — Subscribe `slot(theme)` to every mode / system change — the ONE wire,
- `render_qss` _function_ — Headless: tokens + mode -> the final stylesheet. The system's templates
- `state_color` _function_ — A state role (danger / warn / ok / info / meta / note / dim / accent)
- `style_document` _function_ — Land the design system on a PARSED document: headings in the heading
- `style_text_pane` _function_ — Reading-quality setup for a text pane (QTextEdit / QTextBrowser /

### `cjm_substrate_qt_kit.tools.build`

- `main` _function_

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

**Depends on:** `PySide6`, `cjm-design-system`, `cjm-harness-transcripts`
**Used by:** `cjm-graph-workbench-qt`, `cjm-session-scratchpad-qt`, `cjm-transcript-correction-qt`, `cjm-transcript-decomp-qt`, `cjm-transcription-qt`, `cjm-workflow-hub-qt`
