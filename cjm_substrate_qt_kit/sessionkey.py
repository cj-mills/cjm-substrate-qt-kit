"""Session-key adoption + the ONE mint (ruling 2bae2cc1 (3)).

The workbench and the scratchpad each carried a copy of the same ritual —
mint a timestamp key, adopt it BEFORE the journaled registration (so the
registration op stamps its OWN session, never the outgoing one — the
S-test find 2026-08-14), register the Session spine, point
`.cjm/current-session` at it, put the boot prompt on the clipboard — and
the two copies had drifted (one confirmed, one debounced differently). This
module is the one implementation; the shell wraps it with the confirm
dialog and the clipboard (`AppShell.mint_session`).

Adoption reads the environment first and NEVER overwrites an inherited
CJM_SESSION (a launcher that hands the key down is the authority); the
workspace pointer beside the writes journal is the fallback. The pointer
is written atomically. The boot prompt's mapping signal is imported from
cjm-harness-transcripts (the mapping lib owns it), never a hardcoded
string — a drifted copy would silently unmap every transcript."""

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

ENV_VAR = "CJM_SESSION"
POINTER_NAME = "current-session"
KEY_FORMAT = "%Y-%m-%d_%H-%M-%S"
REPEAT_WINDOW_S = 10.0     # a key this young means the press was a repeat, not a sitting
BOOT_PROMPT = ("Resume. Orient from the resident surface; session rituals per the "
               "resident notes. {signal}{seat}.")


def mint_signal() -> str:
    """The transcript-mapping PREFIX the boot prompt must carry (substring
    matched by the mapping lib — every seat qualifies: "…minted in-workbench",
    "…minted in-scratchpad")."""
    try:
        from cjm_harness_transcripts.mapping import MINT_SIGNAL
    except ImportError as e:  # the dependency is declared; name it when it is missing
        raise RuntimeError("cjm-harness-transcripts is required for the mint gesture "
                           "(it owns the boot-prompt signal)") from e
    return MINT_SIGNAL


def boot_prompt(seat: str) -> str:
    """The start-ritual boot prompt the mint gesture puts on the clipboard."""
    return BOOT_PROMPT.format(signal=mint_signal(), seat=seat)


def new_key(now: Optional[float] = None) -> str:
    """A session key IS its mint timestamp (local time)."""
    return datetime.fromtimestamp(time.time() if now is None else now).strftime(KEY_FORMAT)


def parse_key(key: str) -> Optional[datetime]:
    """The mint time of a key; None for legacy / free-form names."""
    try:
        return datetime.strptime(str(key), KEY_FORMAT)
    except (TypeError, ValueError):
        return None


def is_repeat(active: Optional[str], now: Optional[float] = None) -> bool:
    """A just-minted live key means this press is a key repeat / double tap
    (field find 2026-08-20: a held Shift+S minted two spines a second apart)."""
    when = parse_key(active) if active else None
    if when is None:
        return False
    age = (time.time() if now is None else now) - when.timestamp()
    return 0 <= age < REPEAT_WINDOW_S


# ---- the pointer ------------------------------------------------------------

def pointer_path(journal_paths: Sequence[Union[str, Path]]) -> Optional[Path]:
    """`.cjm/current-session` beside the WRITES journal (journal_paths[0]) —
    the pointer sits with the journal it indexes; None without a journal."""
    if not journal_paths:
        return None
    return Path(journal_paths[0]).parent / POINTER_NAME


def read_pointer(path: Optional[Union[str, Path]]) -> Optional[str]:
    """The pointed key, or None (a missing / empty pointer is not an error)."""
    if path is None:
        return None
    try:
        key = Path(path).read_text(encoding="utf-8").splitlines()[0].strip()
    except (OSError, IndexError):
        return None
    return key or None


def write_pointer(path: Union[str, Path], key: str) -> Path:
    """Point the file at `key` ATOMICALLY (tmp + replace: a reader never sees
    a half-written key)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(key, encoding="utf-8")
    os.replace(tmp, p)
    return p


def active_key(journal_paths: Sequence[Union[str, Path]] = ()) -> Optional[str]:
    """The live sitting: CJM_SESSION, else the workspace pointer."""
    return os.environ.get(ENV_VAR) or read_pointer(pointer_path(journal_paths))


def adopt(journal_paths: Sequence[Union[str, Path]] = ()) -> Tuple[Optional[str], str]:
    """Adopt the live key for this process: (key, source). An inherited
    CJM_SESSION is kept as-is ("env"); else the pointer's key is exported
    ("pointer"); else (None, "none") — the app runs unseated."""
    inherited = os.environ.get(ENV_VAR)
    if inherited:
        return inherited, "env"
    pointed = read_pointer(pointer_path(journal_paths))
    if pointed:
        os.environ[ENV_VAR] = pointed
        return pointed, "pointer"
    return None, "none"


# ---- the mint ---------------------------------------------------------------

def mint(session: Any, journal_paths: Sequence[Union[str, Path]] = (), *,
         now: Optional[float] = None) -> Dict[str, Any]:
    """The ONE mint: refuse a repeat, adopt the new key BEFORE the journaled
    registration, register through `session.register_session(key,
    started_at=)`, restore the outgoing key on failure, write the pointer.
    Returns {key, pointer, previous} or {error, key[, repeat]}. The UI half
    (confirm, clipboard, readout) is the shell's."""
    active = active_key(journal_paths)
    if active and is_repeat(active, now):
        return {"error": f"session {active} just minted — repeat ignored",
                "repeat": True, "key": active}
    key = new_key(now)
    previous = os.environ.get(ENV_VAR)
    os.environ[ENV_VAR] = key
    try:
        res = session.register_session(key, started_at=time.time() if now is None else now)
    except Exception as e:  # surfaced, never swallowed; the seat stays up
        res = {"error": str(e)}
    if not isinstance(res, dict):
        res = {"written": bool(res)}
    if res.get("error"):
        if previous is None:
            os.environ.pop(ENV_VAR, None)
        else:
            os.environ[ENV_VAR] = previous
        return {"error": str(res["error"]), "key": key}
    path = pointer_path(journal_paths)
    pointer = str(write_pointer(path, key)) if path is not None else None
    return {"key": key, "pointer": pointer, "previous": previous}


def journaled_ops_for(key: str, journal_paths: Sequence[Union[str, Path]]) -> List[dict]:
    """Every journaled op attributed to `key` besides its own registrations —
    the retract guard's evidence (an empty mint has none)."""
    try:
        from cjm_context_graph_primitives.journal import read_journal
    except ImportError:
        return []
    out: List[dict] = []
    for p in journal_paths:
        try:
            ops = read_journal(str(p))
        except OSError:
            continue
        for op in ops:
            attributed = op.get("session") or (op.get("args") or {}).get("session")
            own = (op.get("verb") == "session" and (op.get("args") or {}).get("key") == key)
            if attributed == key and not own:
                out.append(op)
    return out
