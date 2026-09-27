"""The ONE Qt foundation library for the cjm-substrate application lane (ruling 8b7351e4).

Three strata: (a) the DESIGN-SYSTEM RUNTIME — a design system is DATA (one
tokens.json per system, schema v1 in `tokens`; Classical and Netrunner
vendored under `systems/`) resolved into one flat vocabulary that ONE Theme
object (`theme`) lands on the application as fonts + QPalette + rendered
QSS + recolored Lucide icons (`icons`), with ONE change signal every kit
widget restyles on; the persisted choice lives in `prefs`; the component
class helpers in `widgets`; the gallery (`gallery`) renders every component
under any system + mode; a switch lands exactly what a fresh launch lands —
fonts ride ONE channel (the stylesheet's font roles), parsed content
re-parses on the signal — and `roundtrip` checks it pixel-for-pixel; (b) the APP SHELL (rulings 2bae2cc1 + d1e3043e) —
every Qt app is an instance of `shell.AppShell`: the window frame with
client-side decorations painted from the tokens (`frame`: the translucent
host, the painted frame, the title bar, the resize grip, the window-manager
fallback), the kit modal frame every dialog rides (`modal`: the overlay, the
form shell, prompt / confirm / notice), the menus derived from the keymap +
the Theme menu, the job seat (`jobs`), the Future -> Signal bridge
(`bridge`), launch resolution (`launch`), session-key adoption + the ONE
mint (`sessionkey`), and the reading pane (`readingpane`); (c) the chrome
every app shares: the loop-thread session base with its open / journal /
close pattern (loopthread), KeymapRegistry (keymap) + the keyboard contract
(keys: numpad Enter answers wherever Return binds), key hints + modal grammar
(keyhints), the status strip, find bar, picker list, form shell + the
config-form model (formdialog, configform), the HITL panel, the span player
(needs ffmpeg on PATH), and text clamps (text). Born at first duplication
between the workbench and the transcription shell (DEC dcf8a712); grown by
demand, never speculation.
"""

__version__ = "0.0.10"
