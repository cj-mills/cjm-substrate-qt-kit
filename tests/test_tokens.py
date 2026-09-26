"""Schema v1 contract: both vendored systems pass `check`; a malformed system
is refused loudly with every problem named; `resolve` emits the one
vocabulary (holes, state roles, dim, typography slots, scale) headlessly;
`to_css` projects the same tokens for the web side."""

import copy
import json

import pytest

from cjm_substrate_qt_kit import systems
from cjm_substrate_qt_kit import tokens as T


@pytest.fixture(params=["classical", "netrunner"])
def system(request):
    return request.param, T.load(systems.tokens_path(request.param))


def test_vendored_systems_pass_check(system):
    slug, tok = system
    T.check(tok, slug)
    assert T.slug(tok) == slug
    assert len(T.modes(tok)) >= 2


def test_check_refuses_loudly_naming_every_problem():
    tok = T.load(systems.tokens_path("classical"))
    bad = copy.deepcopy(tok)
    del bad["modes"]["light"]["danger"]            # a state role missing
    bad["modes"]["dark"]["accent"] = "red"         # not a hex / ref
    bad["ramps"]["accent"] = bad["ramps"]["accent"][:5]   # short ramp
    bad["scheme"]["dark"] = "midnight"             # names a mode that does not exist
    bad["schema"] = 2
    with pytest.raises(T.SchemaError) as e:
        T.check(bad, "bad.json")
    msg = str(e.value)
    assert "bad.json" in msg
    for needle in ("modes.light.danger", "modes.dark.accent", "ramps.accent", "scheme.dark", "schema:"):
        assert needle in msg, needle
    assert len(e.value.problems) >= 5


def test_resolve_emits_the_one_vocabulary(system):
    slug, tok = system
    for mode in T.modes(tok):
        v = T.resolve(tok, mode)
        assert v["system"] == slug and v["mode"] == mode
        for key in ("bg", "surface", "text", "accent", "muted", "muted_solid", "divider", "divider_solid",
                    "selection", "selection_solid", "disabled_text", "font_heading", "font_body",
                    "font_mono", "font_ui", "fs_body", "fs_mono", "fs_ui", "measure", "line_height",
                    "radius_md", "space_2", "fs_h1", "fw_h1", "icon_stroke"):
            assert key in v, key
        for role in T.STATE_ROLES:
            assert v[role].startswith("#"), role
        assert v["dim"].startswith("#") and v["dim"] == v["muted_solid"]
        # a ramp reference resolved to its step
        assert not v["accent_pressed"].startswith("@")


def test_resolve_passes_system_keys_through():
    tok = T.load(systems.tokens_path("netrunner"))
    v = T.resolve(tok, "blue")
    assert v["fill"] == tok["modes"]["blue"]["fill"]
    assert v["fill_hover"].startswith("rgba(")
    assert v["fs_display"] == "30"


def test_mode_for_scheme_follows_only_declared_maps():
    classical = T.load(systems.tokens_path("classical"))
    netrunner = T.load(systems.tokens_path("netrunner"))
    assert T.mode_for_scheme(classical, "dark") == "dark"
    assert T.mode_for_scheme(netrunner, "dark") is None


def test_color_helpers():
    assert T.rgba("#ff0000", .5) == "rgba(255, 0, 0, 128)"
    assert T.mix("#000000", "#ffffff", .5) == "#808080"
    assert T.to_hex((300, -5, 12.6)) == "#ff000d"


def test_to_css_projects_every_mode(system):
    slug, tok = system
    css = T.to_css(tok)
    first = T.modes(tok)[0]
    assert ":root {" in css
    for mode in T.modes(tok)[1:]:
        assert f':root[data-mode="{mode}"]' in css
    assert "--neutral-900:" in css and "--fs-h1:" in css and "--font-body:" in css
    assert f"--bg: {T.resolve(tok, first)['bg']};" in css
    assert "--danger:" in css and "--dim:" in css


def test_load_round_trips_json(tmp_path):
    tok = T.load(systems.tokens_path("classical"))
    p = tmp_path / "tokens.json"
    p.write_text(json.dumps(tok))
    assert T.load(p) == tok


def test_systems_locate_by_slug_dir_and_path(tmp_path):
    root = systems.locate("classical")
    assert (root / "tokens.json").is_file()
    assert systems.locate(root) == root
    assert systems.locate(root / "tokens.json") == root
    with pytest.raises(KeyError) as e:
        systems.locate("no-such-system")
    assert "classical" in str(e.value)
    assert systems.available() == ["classical", "netrunner"]
