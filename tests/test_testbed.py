"""Test-bed contract: paragraph loading keeps fence content, seeders are
deterministic and mark the right token, trial plans cover the variant grid
evenly, click token-indexing is exact, and a trial response lands a JSONL
row with hit scoring."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import json
import random

import pytest
from PySide6.QtWidgets import QApplication

from cjm_substrate_qt_kit import testbed as tb

PROSE = ("This paragraph carries more than twenty words of ordinary prose so "
         "that the loader will keep it around for trials and seeding checks "
         "without complaint from the filter.")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_load_paragraphs_keeps_fence_content(tmp_path):
    md = tmp_path / "scratch.md"
    md.write_text("# heading\n\n" + PROSE + "\n\n```markdown\n" + PROSE + "\n```\n\n- a list line\n\nshort block\n")
    paragraphs = tb.load_paragraphs(md)
    assert len(paragraphs) == 2  # prose + fence content; heading/list/short dropped
    assert all(p.startswith("This paragraph") for p in paragraphs)


def test_load_paragraphs_rejects_flattened_structure(tmp_path):
    md = tmp_path / "scratch.md"
    flattened_list = "Enhancements for the next phase:\n- one bullet item here\n- another bullet item follows"
    json_block = '{\n"text": {"start_char": 150, "end_char": 300},\n"video": {"start_time": 120.5}\n}'
    tool_block = "● Bash(python -c \"import this\")\n⎿ output line one with some words in it that keep going for a while longer"
    numbery = ("word " * 10) + "1234 5678 {90} [12] (34) == != <> :: " * 3
    md.write_text("\n\n".join([PROSE, flattened_list, json_block, tool_block, numbery]))
    paragraphs = tb.load_paragraphs(md)
    assert paragraphs == [" ".join(PROSE.split())]


def test_seeders_are_deterministic_and_mark_the_token():
    words = PROSE.split()
    for cls in tb.CLASSES:
        a = tb.seed_error(words, cls, random.Random(7))
        b = tb.seed_error(words, cls, random.Random(7))
        assert a == b, cls
        if a is None:
            continue
        mutated, target, detail = a
        assert " ".join(mutated) != " ".join(words), cls
        assert 0 <= target < len(mutated), cls
        assert detail


def test_seed_drop_and_double_shift_lengths():
    words = PROSE.split()
    dropped = tb._seed_drop(words, random.Random(1))
    assert dropped is not None and len(dropped[0]) == len(words) - 1
    doubled = tb._seed_double(words, random.Random(1))
    assert doubled is not None and len(doubled[0]) == len(words) + 1
    di = doubled[1]
    assert doubled[0][di] == doubled[0][di - 1]


def test_build_trials_covers_grid_evenly():
    rng = random.Random(0)
    trials = tb.build_trials([PROSE], rng, 36, clean_ratio=0.2)
    assert len(trials) == 36
    counts = {}
    for t in trials:
        key = tuple(sorted(t["variant"].items()))
        counts[key] = counts.get(key, 0) + 1
    assert len(counts) == 18 and set(counts.values()) == {2}
    assert any(t["cls"] is None for t in trials)
    assert any(t["cls"] is not None for t in trials)


def test_build_variants_sweeps(tmp_path):
    assert len(tb.build_variants()) == 18  # default grid unchanged
    focused = tb.build_variants(schemes=["dark"], sizes=[13],
                                line_heights=[1.3, 1.45],
                                families=["", "Noto Sans"])
    assert len(focused) == 4
    assert {v["font-body-family"] for v in focused} == {"", "Noto Sans"}
    theme_file = tmp_path / "warm.json"
    theme_file.write_text(json.dumps({"content": "#111111"}))
    themed = tb.build_variants(schemes=["dark"], sizes=[13], line_heights=[1.3],
                               themes=[("warm", json.loads(theme_file.read_text()))])
    assert themed == [{"scheme": "dark", "font-body-size": 13.0,
                       "font-body-line-height": 1.3, "content": "#111111",
                       "theme": "warm"}]
    trials = tb.build_trials([PROSE], random.Random(0), 8, variants=focused)
    counts = {}
    for t in trials:
        key = tuple(sorted(t["variant"].items()))
        counts[key] = counts.get(key, 0) + 1
    assert len(counts) == 4 and set(counts.values()) == {2}


def test_token_index_maps_clicks_to_tokens():
    text = "alpha beta gamma"
    assert tb._token_index(text, 0) == 0
    assert tb._token_index(text, 3) == 0
    assert tb._token_index(text, 6) == 1   # start of beta
    assert tb._token_index(text, 8) == 1
    assert tb._token_index(text, len(text)) == 2


def test_click_pane_ignores_blank_space(app):
    from PySide6.QtCore import QPointF
    pane = tb.ClickPane()
    pane.setPlainText("alpha beta gamma")
    pane.resize(400, 200)
    pane.show()  # offscreen: forces document layout so rects are real
    app.processEvents()
    cursor = pane.textCursor()
    cursor.setPosition(7)  # inside "beta"
    rect = pane.cursorRect(cursor)
    assert pane.hit_token(QPointF(rect.center().x() + 2.0, rect.center().y())) == 1
    assert pane.hit_token(QPointF(390.0, 190.0)) is None  # blank area


def test_trial_window_records_scored_rows(app, tmp_path):
    out = tmp_path / "rows.jsonl"
    trials = tb.build_trials([PROSE], random.Random(3), 3, clean_ratio=0.0)
    window = tb.TrialWindow(trials, out)
    assert window.index == -1                    # intro screen, not a trial
    window.respond(0)                            # intro click: no row
    assert not out.exists()
    window.next_trial()                          # what Enter triggers
    window.respond(trials[0]["target"])          # exact hit
    window.index = 1                             # advance without event loop
    window.answered = False
    window.respond(None)                         # "clean" on a seeded trial
    rows = [json.loads(ln) for ln in out.read_text().splitlines()]
    assert len(rows) == 2
    assert rows[0]["hit"] is True and rows[0]["cls"] == trials[0]["cls"]
    assert rows[1]["hit"] is False and rows[1]["clicked"] is None
    assert rows[0]["variant"] == trials[0]["variant"]
    assert rows[0]["n_tokens"] == len(trials[0]["text"].split())
    window.close()


def test_summarize_reports_position_thirds(tmp_path, capsys):
    out = tmp_path / "rows.jsonl"
    base = {"variant": {"scheme": "dark", "font-body-size": 12.0,
                        "font-body-line-height": 1.45},
            "cls": "drop", "hit": True, "ms": 1000}
    rows = [dict(base, target=1, n_tokens=30),
            dict(base, target=15, n_tokens=30),
            dict(base, target=29, n_tokens=30, hit=False),
            dict(base, cls=None, target=None, n_tokens=30)]
    out.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    tb.summarize([out])
    text = capsys.readouterr().out
    assert "== error position ==" in text
    assert "1-early: 1/1" in text and "3-late: 0/1" in text
    assert "hits 1000 ms" in text


def test_corpus_is_clean_and_every_class_bites():
    from cjm_substrate_qt_kit.testbed_corpus import PARAGRAPHS
    assert len(PARAGRAPHS) >= 40
    for p in PARAGRAPHS:
        words = p.split()
        assert 30 <= len(words) <= 90, p[:40]
        assert "  " not in p, p[:40]
        for a, b in zip(words, words[1:]):       # no pre-existing doubles
            assert a != b, (a, p[:40])
    rng = random.Random(0)
    for cls in tb.CLASSES:
        bites = sum(1 for p in PARAGRAPHS
                    if tb.seed_error(p.split(), cls, rng) is not None)
        floor = 0.3 if cls == "swap" else 0.9
        assert bites / len(PARAGRAPHS) >= floor, (cls, bites)
