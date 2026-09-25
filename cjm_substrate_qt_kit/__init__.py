"""The ONE Qt foundation library for the cjm-substrate application lane (ruling 8b7351e4).

Three strata: (a) the design-system runtime — semantic theme tokens as data
-> QPalette + QSS + fonts (theme); (b) the app shell (its own ruling,
2bae2cc1 — landing); (c) the chrome every app shares: the loop-thread session
base (loopthread), KeymapRegistry (keymap), key hints + modal grammar
(keyhints), the status strip, find bar, picker list, form shell + the
config-form model (formdialog, configform), the HITL panel, the span player
(needs ffmpeg on PATH), and text clamps (text). Born at first duplication
between the workbench and the transcription shell (DEC dcf8a712); grown by
demand, never speculation.
"""

__version__ = "0.0.7"
