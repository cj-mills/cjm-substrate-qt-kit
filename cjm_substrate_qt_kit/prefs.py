"""The persisted theme choice — system + mode — and its precedence.

Work item 56f7f69d asked for theme selection independent of the OS scheme,
persisted; the shell that will own the in-app switcher (2bae2cc1 / 812beb51)
does not exist yet, so the kit holds the store: one small JSON file in the
user's config dir. Precedence at apply time, highest first:

    explicit arguments (an app's CLI flag)  >  CJM_THEME=<system>[:<mode>]
    >  the preferences file  >  classical:auto

`auto` means: follow the OS scheme through the system's `scheme` map, or the
system's first mode when it declares none. The file is the one thing the
in-app switcher will write once the shell lands; nothing else persists here."""

import json
import os
from pathlib import Path
from typing import Dict, Optional, Tuple

DEFAULT_SYSTEM = "classical"
DEFAULT_MODE = "auto"
ENV_VAR = "CJM_THEME"
PREFS_ENV = "CJM_KIT_PREFS"   # override the file location (tests, portable installs)


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
    """The stored choice ({"system", "mode"}) — an empty dict when absent or unreadable."""
    try:
        data = json.loads(prefs_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: str(v) for k, v in data.items() if k in ("system", "mode") and isinstance(v, str)}


def write(system: str, mode: str) -> Path:
    """Persist the choice (atomic replace); returns the file written."""
    path = prefs_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"system": system, "mode": mode}, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


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
