"""Tests for the manifest-driven config form model (schema -> fields, closed-
set cycling, transient-editor parsing, overrides round-trip). SCHEMA mirrors
the real whisper capability manifest's pydantic-emitted shape. Ported with
the model from the tui-kit (work item 21145648)."""
import pytest

from cjm_substrate_qt_kit.configform import ConfigForm

SCHEMA = {
    "type": "object",
    "properties": {
        "model": {"type": "string", "title": "Model",
                  "enum": ["tiny", "base", "large-v3"], "default": "base"},
        "device": {"type": "string", "title": "Device",
                   "enum": ["auto", "cpu", "cuda"], "default": "auto"},
        "language": {"type": ["string", "null"], "title": "Language",
                     "default": None},
        "temperature": {"type": "number", "title": "Temperature",
                        "minimum": 0.0, "maximum": 1.0, "default": 0.0},
        "beam_size": {"type": "integer", "title": "Beam Size",
                      "minimum": 1, "maximum": 10, "default": 5},
        "fp16": {"type": "boolean", "title": "FP16", "default": True},
    },
}


def test_from_schema_fields_and_skip():
    form = ConfigForm.from_schema(SCHEMA, skip=("model",))
    assert [f.key for f in form.fields] == [
        "device", "language", "temperature", "beam_size", "fp16"]  # order kept, axis skipped
    lang = form.field("language")
    assert lang.nullable and lang.kind == "string"
    assert form.field("beam_size").kind == "integer"
    assert form.field("fp16").kind == "bool"
    assert form.overrides() == {}                # everything at default
    with pytest.raises(KeyError):
        form.field("model")


def test_cycle_closed_sets():
    form = ConfigForm.from_schema(SCHEMA)
    device = form.field("device")
    assert device.cycle() and device.value == "cpu"       # auto -> cpu
    assert device.cycle(-1) is True and device.value == "auto"
    fp16 = form.field("fp16")
    assert fp16.cycle() and fp16.value is False           # bool toggles
    lang = form.field("language")
    assert lang.cycle() is False                          # open kind: the editor's job
    temp = form.field("temperature")
    assert temp.cycle() is False


def test_parse_types_bounds_and_null():
    form = ConfigForm.from_schema(SCHEMA)
    beam = form.field("beam_size")
    assert beam.parse("7") == 7
    with pytest.raises(ValueError):
        beam.parse("11")                    # above maximum
    with pytest.raises(ValueError):
        beam.parse("2.5")                   # not an integer
    assert beam.value == 7                  # failures leave the value untouched
    temp = form.field("temperature")
    assert temp.parse("0.4") == 0.4
    lang = form.field("language")
    assert lang.parse("en") == "en"
    assert lang.parse("none") is None       # nullable escape
    fp16 = form.field("fp16")
    assert fp16.parse("false") is False
    with pytest.raises(ValueError):
        fp16.parse("nah")
    device = form.field("device")
    with pytest.raises(ValueError):
        device.parse("gpu")                 # not one of the options
    assert device.parse("cuda") == "cuda"


def test_overrides_apply_and_rows_round_trip():
    form = ConfigForm.from_schema(SCHEMA, skip=("model",))
    form.field("device").parse("cpu")
    form.field("beam_size").parse("3")
    assert form.overrides() == {"device": "cpu", "beam_size": 3}
    fresh = ConfigForm.from_schema(SCHEMA, skip=("model",))
    fresh.apply(form.overrides() | {"stale_key": 1})   # unknown keys ignored
    assert fresh.overrides() == {"device": "cpu", "beam_size": 3}
    rows = dict((title, (value, modified))
                for title, value, modified in fresh.rows())
    assert rows["Device"] == ("cpu", True)
    assert rows["Language"] == ("none", False)         # null renders as 'none'
    assert rows["FP16"] == ("true", False)             # spec-grammar bool shape


def test_real_manifest_shape():
    import json
    from pathlib import Path
    real = Path("/mnt/SN850X_8TB_EXT4/Projects/GitHub/cj-mills/cjm-transcription-core/.cjm/manifests/cjm-capability-whisper.json")
    if not real.exists():
        pytest.skip("real whisper manifest not on this machine")
    code = json.loads(real.read_text())["code"]
    form = ConfigForm.from_schema(code["config_schema"], skip=("model",))
    assert form.overrides() == {}          # defaults are a clean instance
    assert all(len(r) == 3 for r in form.rows())
    form.field("device").parse("cpu")      # the voxtral-small case, expressible
    assert form.overrides() == {"device": "cpu"}
