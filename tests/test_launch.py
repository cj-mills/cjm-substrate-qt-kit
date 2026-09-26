"""Launch resolution (ruling 2bae2cc1 (4)): the workspace record and the
persisted in-app config outrank the CLI flag, which outranks the default;
a named workspace must carry the marker; the current directory is never
consulted; ${WS} records resolve against the root."""

import os

import pytest

from cjm_substrate_qt_kit import launch


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.delenv(launch.WORKSPACE_ENV, raising=False)
    return tmp_path


def workspace(root):
    root.mkdir(parents=True, exist_ok=True)
    (root / launch.WORKSPACE_MARKER).write_text("name: test\n")
    return root


def test_precedence_walk(home):
    ws = workspace(home / "ws")
    launch.record(ws, "workbench", {"graph_db_path": str(ws / ".cjm" / "dev-graph.db"),
                                    "anchor": "program-x"})
    launch.persist("workbench", {"theme": "netrunner:red", "anchor": "from-prefs"})
    cfg = launch.resolve("workbench", cli={"theme": "classical", "graph_db_path": "/cli/db",
                                           "limit": 5, "anchor": None},
                         defaults={"limit": 25, "manifests_dir": "/default/m"}, workspace=ws)
    assert cfg["graph_db_path"] == str(ws / ".cjm" / "dev-graph.db") and cfg.source("graph_db_path") == "workspace"
    assert cfg["anchor"] == "program-x"                      # workspace beats prefs
    assert cfg["theme"] == "netrunner:red" and cfg.source("theme") == "prefs"   # prefs beat cli
    assert cfg["limit"] == 5 and cfg.source("limit") == "cli"
    assert cfg["manifests_dir"] == "/default/m" and cfg.source("manifests_dir") == "default"
    assert cfg.workspace == ws.resolve()
    assert "graph_db_path=" in cfg.describe() and "(workspace)" in cfg.describe()
    # the record stores the path workspace-relative
    stored = launch.read_json(launch.workspace_record_path(ws, "workbench"))
    assert stored["graph_db_path"] == "${WS}/.cjm/dev-graph.db"


def test_named_workspace_must_carry_the_marker(home, monkeypatch):
    bare = home / "bare"
    bare.mkdir()
    with pytest.raises(launch.LaunchError):
        launch.resolve("x", workspace=bare)
    monkeypatch.setenv(launch.WORKSPACE_ENV, str(bare))
    with pytest.raises(launch.LaunchError):
        launch.resolve("x")
    ws = workspace(home / "ws")
    monkeypatch.setenv(launch.WORKSPACE_ENV, str(ws))
    assert launch.resolve("x").workspace == ws.resolve()


def test_cwd_is_never_a_workspace(home, monkeypatch):
    ws = workspace(home / "ws")
    monkeypatch.chdir(ws)
    cfg = launch.resolve("x", cli={"graph_db_path": None}, defaults={})
    assert cfg.workspace is None
    assert cfg["graph_db_path"] is None and cfg.source("graph_db_path") == "unset"


def test_persist_merges_and_removes(home):
    launch.persist("x", {"a": 1, "b": 2})
    launch.persist("x", {"a": None, "c": 3})
    assert launch.read_json(launch.app_config_path("x")) == {"b": 2, "c": 3}
    assert launch.app_config_path("x").parent == launch.config_dir() / "apps"
    assert os.environ["XDG_CONFIG_HOME"] in str(launch.config_dir())
