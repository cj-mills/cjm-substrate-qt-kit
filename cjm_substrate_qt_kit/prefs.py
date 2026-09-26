"""The persisted theme choice — system + mode — and its precedence.

Work item 56f7f69d asked for theme selection independent of the OS scheme,
persisted; the shell that will own the in-app switcher (2bae2cc1 / 812beb51)
does not exist yet, so the kit holds the store: one small JSON file in the
user's config dir. Precedence at apply time, highest first:

    explicit arguments (an app's CLI flag)  >  CJM_THEME=<system>[:<mode>]
    >  the preferences file  >  classical:auto

`auto` means: follow the OS scheme through the system's `scheme` map, or the
system's first mode when it declares none. The file is what the shell's
in-app switcher writes (a9ba662e); the DECORATIONS choice rides beside it
(ruling d1e3043e): "client" = the shell paints the title bar and the frame
from the tokens (the default), "system" = the window manager's decorations
with the mode hinted to it (the fallback for tiling window managers,
accessibility, remote displays). Precedence: explicit > CJM_DECORATIONS >
the file > client."""

import json
import os
from pathlib import Path
from typing import Dict, Optional, Tuple

DEFAULT_SYSTEM = "classical"
DEFAULT_MODE = "auto"
ENV_VAR = "CJM_THEME"
PREFS_ENV = "CJM_KIT_PREFS"   # override the file location (tests, portable installs)
DECORATIONS_ENV = "CJM_DECORATIONS"
DECORATIONS = ("client", "system")
DEFAULT_DECORATIONS = "client"
_KEYS = ("system", "mode", "decorations")


def prefs_path() -> Path:
    """`$CJM_KIT_PREFS`, else `<config dir>/cjm-substrate/theme.json` where
    the config dir is `$XDG_CONFIG_HOME` / `~/.config` (POSIX) or `%APPDATA%`
    (Windows)."""
    override = os.environ.get(PREFS_ENV)
    if override:
        return Path(override).expanduser()
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "cjm-substrate" / "theme.json"


def read() -> Dict[str, str]:
    """The stored choices ({"system", "mode", "decorations"} — whichever are
    present) — an empty dict when absent or unreadable."""
    try:
        data = json.loads(prefs_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: str(v) for k, v in data.items() if k in _KEYS and isinstance(v, str)}


def _write_all(data: Dict[str, str]) -> Path:
    path = prefs_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


def write(system: str, mode: str) -> Path:
    """Persist the theme choice (atomic replace, the other keys kept);
    returns the file written."""
    data = read()
    data.update({"system": system, "mode": mode})
    return _write_all(data)


def write_decorations(value: str) -> Path:
    """Persist the decorations choice ("client" / "system"), the theme keys kept."""
    if value not in DECORATIONS:
        raise ValueError(f"decorations: expected one of {DECORATIONS}, got {value!r}")
    data = read()
    data["decorations"] = value
    return _write_all(data)


def decorations(explicit: Optional[str] = None) -> Tuple[str, str]:
    """(decorations, source) after the precedence walk: explicit >
    CJM_DECORATIONS > the file > "client". An unknown value at any rung is
    skipped (never a crash at launch for a typo in the environment)."""
    for value, source in ((explicit, "args"), (os.environ.get(DECORATIONS_ENV), "env"),
                          (read().get("decorations"), "prefs")):
        if value and value in DECORATIONS:
            return value, source
    return DEFAULT_DECORATIONS, "default"


def parse_env(value: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """`CJM_THEME` grammar: `<system>`, `<system>:<mode>` or `:<mode>`."""
    if not value:
        return None, None
    system, _, mode = value.partition(":")
    return (system.strip() or None), (mode.strip() or None)


def resolve(system: Optional[str] = None, mode: Optional[str] = None) -> Tuple[str, str, str]:
    """(system, mode, source) after the precedence walk. `source` names where
    each came from in words ("args" / "env" / "prefs" / "default") for the
    launch log, joined when the two differ."""
    env_system, env_mode = parse_env(os.environ.get(ENV_VAR))
    stored = read()
    chosen_system, s_src = _pick(system, env_system, stored.get("system"), DEFAULT_SYSTEM)
    chosen_mode, m_src = _pick(mode, env_mode, stored.get("mode"), DEFAULT_MODE)
    source = s_src if s_src == m_src else f"system:{s_src} mode:{m_src}"
    return chosen_system, chosen_mode, source


def _pick(arg, env, stored, default) -> Tuple[str, str]:
    if arg:
        return str(arg), "args"
    if env:
        return str(env), "env"
    if stored:
        return str(stored), "prefs"
    return default, "default"
