"""Session-key adoption + the ONE mint (ruling 2bae2cc1 (3)): env first and
never overwritten, the pointer as the fallback, the adopt-before-write
order, the repeat guard, the atomic pointer, the boot prompt's signal."""

import os
import time

import pytest

from cjm_substrate_qt_kit import sessionkey as sk


@pytest.fixture(autouse=True)
def no_env(monkeypatch):
    monkeypatch.delenv(sk.ENV_VAR, raising=False)
    yield


class FakeSession:
    def __init__(self, fail=False):
        self.writes = []
        self.fail = fail

    def register_session(self, key, **kw):
        kw["env_at_write"] = os.environ.get(sk.ENV_VAR)
        self.writes.append((key, kw))
        if self.fail:
            return {"error": "graph down", "written": False}
        return {"written": True, "key": key}


def test_pointer_beside_the_writes_journal_atomic(tmp_path):
    journals = [str(tmp_path / ".cjm" / "g.writes.jsonl")]
    path = sk.pointer_path(journals)
    assert path == tmp_path / ".cjm" / "current-session"
    assert sk.read_pointer(path) is None
    sk.write_pointer(path, "2026-09-25_19-12-44")
    assert sk.read_pointer(path) == "2026-09-25_19-12-44"
    assert not path.with_name(path.name + ".tmp").exists()
    assert sk.pointer_path([]) is None and sk.read_pointer(None) is None


def test_adopt_env_first_pointer_fallback(tmp_path, monkeypatch):
    journals = [str(tmp_path / ".cjm" / "g.writes.jsonl")]
    assert sk.adopt(journals) == (None, "none")
    sk.write_pointer(sk.pointer_path(journals), "2026-09-25_19-12-44")
    assert sk.adopt(journals) == ("2026-09-25_19-12-44", "pointer")
    assert os.environ[sk.ENV_VAR] == "2026-09-25_19-12-44"
    monkeypatch.setenv(sk.ENV_VAR, "inherited-key")
    assert sk.adopt(journals) == ("inherited-key", "env")   # never overwritten
    assert sk.active_key(journals) == "inherited-key"


def test_mint_adopts_before_the_write_and_points(tmp_path):
    journals = [str(tmp_path / ".cjm" / "g.writes.jsonl")]
    session = FakeSession()
    res = sk.mint(session, journals, now=time.time() - 3600)
    key = res["key"]
    assert sk.parse_key(key) is not None and res["previous"] is None
    assert session.writes[0][1]["env_at_write"] == key          # stamped with its OWN key
    assert os.environ[sk.ENV_VAR] == key
    assert sk.read_pointer(sk.pointer_path(journals)) == key
    assert res["pointer"] == str(sk.pointer_path(journals))


def test_mint_refuses_a_repeat_and_restores_on_failure(tmp_path, monkeypatch):
    journals = [str(tmp_path / ".cjm" / "g.writes.jsonl")]
    fresh = sk.new_key()
    monkeypatch.setenv(sk.ENV_VAR, fresh)
    res = sk.mint(FakeSession(), journals)
    assert res.get("repeat") and res["key"] == fresh and "repeat" in res["error"]
    monkeypatch.setenv(sk.ENV_VAR, "outgoing")
    res = sk.mint(FakeSession(fail=True), journals, now=time.time() - 3600)
    assert res["error"] == "graph down"
    assert os.environ[sk.ENV_VAR] == "outgoing"              # the outgoing key survives
    assert sk.read_pointer(sk.pointer_path(journals)) is None
    monkeypatch.delenv(sk.ENV_VAR)
    res = sk.mint(FakeSession(fail=True), [], now=time.time() - 3600)
    assert res["error"] and sk.ENV_VAR not in os.environ


def test_boot_prompt_carries_the_mapping_signal():
    prompt = sk.boot_prompt("workbench")
    assert prompt.endswith("New session minted in-workbench.")
    assert sk.mint_signal() == "New session minted in-"


def test_is_repeat_window():
    key = sk.new_key(1_800_000_000.0)
    assert sk.is_repeat(key, now=1_800_000_003.0)
    assert not sk.is_repeat(key, now=1_800_000_030.0)
    assert not sk.is_repeat("manual-key")
    assert not sk.is_repeat(None)
