# cjm-substrate-qt-kit

<!-- generated from the context graph by `cjm-context-graph readme` — do not edit by hand; edit the graph (the urge to hand-edit = move it on-graph) -->

Shared foundations for the PySide6 application lane (DEC c4b0d6e5): LoopThreadSession (a private asyncio loop behind a Qt shell — GraphSession and CapabilitySession both subclass it), the row-style palette (STYLE_COLORS/apply_row_style), and the keybinding helper. Every piece extracted at its first real duplication between cjm-graph-workbench-qt and cjm-transcription-qt — the kit grows by demand, never speculation. Semantic theming (a94fa56a) and in-app config (812beb51) land here at their demand points.

## Modules

- **`cjm_substrate_qt_kit`** — Shared foundations for the PySide6 application lane — extracted at first duplication (DEC dcf8a712).
- **`cjm_substrate_qt_kit.keys`** — The keybinding helper both shells grew independently.
- **`cjm_substrate_qt_kit.loopthread`** — The loop-thread session base: a private asyncio loop behind a Qt shell.
- **`cjm_substrate_qt_kit.style`** — Row-style vocabulary for the lane's list widgets.

## API

### `cjm_substrate_qt_kit.keys`

- `bind` _function_ — One QShortcut: `key` on `parent` (default: the owner window) fires `fn`.

### `cjm_substrate_qt_kit.loopthread`

- `LoopThreadSession` _class_ — Owns one daemon asyncio loop thread; subclasses put their subsystem's

### `cjm_substrate_qt_kit.style`

- `apply_row_style` _function_ — Map a row's style words onto a list item (color words + bold).

## Dependencies

**Depends on:** `PySide6`
**Used by:** `cjm-graph-workbench-qt`, `cjm-transcription-qt`
