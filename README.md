# cjm-substrate-qt-kit

Shared foundations for the PySide6 application lane: the loop-thread session base (a private asyncio loop behind a Qt shell), the row-style palette, and the keybinding helper. Every piece was extracted at its first real duplication between `cjm-graph-workbench-qt` and `cjm-transcription-qt` — the kit grows by demand, never speculation.

(README is projected from the context graph — `readme --write cjm-substrate-qt-kit` regenerates it.)
