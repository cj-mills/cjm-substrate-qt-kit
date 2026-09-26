"""Launch resolution (ruling 2bae2cc1 (4)): where an app's launch values —
the graph db, the journals, the manifests dir, the theme — come from.

Precedence, highest first:

    the WORKSPACE RECORD    <workspace>/.cjm/launch/<app_id>.json
    the PERSISTED IN-APP CONFIG    <config dir>/cjm-substrate/apps/<app_id>.json
    the CLI flag
    the default

The workspace is named EXPLICITLY (a --workspace flag) or by CJM_WORKSPACE,
and must carry the substrate's marker (`cjm-workspace.yaml`); the launch
never walks up from the current directory — a graph db, a journal or a
manifest resolved from cwd was the drift class the ruling retires (rule
027bbe56: dev `.cjm/` paths are scaffolding, never baked-in defaults). A
record may carry workspace-relative paths as "${WS}/<rel>" (the substrate's
own recording token); they resolve against the workspace root. Every
resolved value remembers its source so the launch log can say where each
came from."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Union

WORKSPACE_ENV = "CJM_WORKSPACE"
WORKSPACE_MARKER = "cjm-workspace.yaml"
WS_TOKEN = "${WS}"


class LaunchError(Exception):
    """A workspace was named (flag or env) but is not a workspace root."""


def config_dir() -> Path:
    """`$XDG_CONFIG_HOME` / `~/.config` (POSIX) or `%APPDATA%` (Windows), under
    the substrate's own folder — the same home the theme prefs use."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "cjm-substrate"


def app_config_path(app_id: str) -> Path:
    return config_dir() / "apps" / f"{app_id}.json"


def workspace_root(explicit: Optional[Union[str, Path]] = None) -> Optional[Path]:
    """The workspace root: `explicit` > CJM_WORKSPACE > None. A named
    directory WITHOUT the marker raises LaunchError — loud, never a silent
    fallback. Never the current directory."""
    for value, source in ((explicit, "--workspace"), (os.environ.get(WORKSPACE_ENV), WORKSPACE_ENV)):
        if not value:
            continue
        root = Path(value).expanduser().resolve()
        if not (root / WORKSPACE_MARKER).is_file():
            raise LaunchError(f"{source}={root} has no {WORKSPACE_MARKER} — not a workspace root")
        return root
    return None


def workspace_record_path(root: Union[str, Path], app_id: str) -> Path:
    return Path(root) / ".cjm" / "launch" / f"{app_id}.json"


def read_json(path: Union[str, Path]) -> Dict[str, Any]:
    """A JSON object, defensively: {} when absent, unreadable or not an object."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def write_json(path: Union[str, Path], data: Mapping[str, Any]) -> Path:
    """Atomic replace (tmp + rename)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(dict(data), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, p)
    return p


def _resolve_ws(value: Any, root: Optional[Path]) -> Any:
    """"${WS}/<rel>" -> the absolute path under the workspace root."""
    if root is not None and isinstance(value, str):
        if value == WS_TOKEN:
            return str(root)
        if value.startswith(WS_TOKEN + "/"):
            return str(root / value[len(WS_TOKEN) + 1:])
    return value


@dataclass
class LaunchConfig:
    """The resolved values + where each came from ("workspace" / "prefs" /
    "cli" / "default" / "unset")."""
    app_id: str
    values: Dict[str, Any] = field(default_factory=dict)
    sources: Dict[str, str] = field(default_factory=dict)
    workspace: Optional[Path] = None

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self.values[key]

    def source(self, key: str) -> str:
        return self.sources.get(key, "unset")

    def describe(self) -> str:
        """One launch-log line: `key=value (source)` per key."""
        parts = [f"{k}={self.values[k]!r} ({self.sources[k]})" for k in sorted(self.values)]
        head = f"workspace={self.workspace}" if self.workspace else "workspace=none"
        return f"{self.app_id}: {head} · " + " · ".join(parts)


def resolve(app_id: str, *, cli: Optional[Mapping[str, Any]] = None,
            defaults: Optional[Mapping[str, Any]] = None,
            workspace: Optional[Union[str, Path]] = None,
            keys: Optional[Iterable[str]] = None) -> LaunchConfig:
    """Walk the precedence for every key named (the union of the record, the
    persisted config, `cli`, `defaults` and `keys`). A CLI value of None
    means "not given" and falls through."""
    root = workspace_root(workspace)
    record = read_json(workspace_record_path(root, app_id)) if root else {}
    stored = read_json(app_config_path(app_id))
    cli = dict(cli or {})
    defaults = dict(defaults or {})
    names = list(dict.fromkeys([*record, *stored, *cli, *defaults, *(keys or [])]))
    cfg = LaunchConfig(app_id=app_id, workspace=root)
    for k in names:
        if k in record:
            cfg.values[k], cfg.sources[k] = _resolve_ws(record[k], root), "workspace"
        elif k in stored:
            cfg.values[k], cfg.sources[k] = stored[k], "prefs"
        elif cli.get(k) is not None:
            cfg.values[k], cfg.sources[k] = cli[k], "cli"
        elif k in defaults:
            cfg.values[k], cfg.sources[k] = defaults[k], "default"
        else:
            cfg.values[k], cfg.sources[k] = None, "unset"
    return cfg


def persist(app_id: str, values: Mapping[str, Any]) -> Path:
    """Merge `values` into the persisted in-app config (the in-app settings
    surface writes here; a None value removes the key)."""
    data = read_json(app_config_path(app_id))
    for k, v in values.items():
        if v is None:
            data.pop(k, None)
        else:
            data[k] = v
    return write_json(app_config_path(app_id), data)


def record(root: Union[str, Path], app_id: str, values: Mapping[str, Any]) -> Path:
    """Merge `values` into the workspace's launch record for `app_id` (a
    workspace tool writes here; paths under the root are recorded
    workspace-relative as "${WS}/<rel>")."""
    root = Path(root).resolve()
    data = read_json(workspace_record_path(root, app_id))
    for k, v in values.items():
        if v is None:
            data.pop(k, None)
            continue
        if isinstance(v, str):
            p = Path(v)
            if p.is_absolute():
                try:
                    v = f"{WS_TOKEN}/{p.resolve().relative_to(root).as_posix()}"
                except ValueError:
                    pass
        data[k] = v
    return write_json(workspace_record_path(root, app_id), data)
