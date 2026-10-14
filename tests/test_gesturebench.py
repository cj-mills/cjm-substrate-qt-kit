"""The gesture runner (design detail 4389a579): a driver by name, its params as JSON."""

import json

import pytest
from cjm_substrate_qt_kit.gesturebench import ladder, load_driver, main

SEEN = []


def fake_driver(params):
    SEEN.append(params)
    return ["portfolio", "node"]


def test_main_runs_the_named_driver_with_its_params(capsys):
    assert main(["test_gesturebench:fake_driver", "--params", '{"db": "x.db"}']) == 0
    assert SEEN[-1] == {"db": "x.db"}
    assert json.loads(capsys.readouterr().out)["gestures"] == ["portfolio", "node"]


def test_a_malformed_driver_refuses():
    with pytest.raises(ValueError):
        load_driver("no_colon")
    assert load_driver("json:dumps") is json.dumps


def test_ladder_records_a_failure_and_goes_on(capsys):
    def boom():
        raise RuntimeError("no graph")
    assert ladder([("a", lambda: 1), ("b", boom), ("c", lambda: None)]) == [
        "a", "b: RuntimeError", "c"]
    assert "gesture b failed" in capsys.readouterr().err
