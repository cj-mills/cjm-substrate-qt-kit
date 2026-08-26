"""Layout-role contract: registries classify by role boundary, the named
windows land where the framework says they do, afford clamps."""

from cjm_substrate_qt_kit.layout import (NAMED_WINDOWS, afford, classify,
                                         height_tier, mode, shape)


def test_mode_boundaries():
    assert mode(639) == "M1"
    assert mode(640) == "M2"
    assert mode(1024) == "M3"
    assert mode(1535) == "M3"
    assert mode(1536) == "M4"
    assert mode(2560) == "M5"
    assert mode(3840) == "M6"


def test_shape_boundaries():
    assert shape(1080, 2560) == "S1"   # rotated monitor
    assert shape(1000, 1000) == "S2"
    assert shape(1280, 960) == "S3"    # 4:3
    assert shape(1920, 1080) == "S4"
    assert shape(3440, 1440) == "S5"
    assert shape(5120, 1440) == "S6"


def test_height_tiers():
    assert height_tier(699) == "H1"
    assert height_tier(700) == "H2"
    assert height_tier(1100) == "H3"
    assert height_tier(1700) == "H4"


def test_named_windows_classify_as_ratified():
    # cc55a7b5's three real windows as points in M/S/H space
    assert classify(*NAMED_WINDOWS["half-landscape"]) == {
        "mode": "M3", "shape": "S2", "height": "H3"}
    assert classify(*NAMED_WINDOWS["full-landscape"]) == {
        "mode": "M5", "shape": "S4", "height": "H3"}
    assert classify(*NAMED_WINDOWS["portrait"]) == {
        "mode": "M3", "shape": "S1", "height": "H4"}


def test_afford_clamps_floor_and_cap():
    assert afford(300, 360, 3) == 1    # floor
    assert afford(800, 360, 3) == 2
    assert afford(3000, 360, 3) == 3   # cap
    assert afford(3000, 360, 9, floor=2) == 8
