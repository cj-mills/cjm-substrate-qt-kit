"""Kit HITL chrome contract (work item 55bcc3c5): worklist rows carry the
tier glyph / category chip / span / confidence / quote, items map to pickable
rows with the host-owned cursor, the payload slot repaints alone, the
verdict strip paints only non-empty tiers by role, and the provenance pane
renders escaped key/value pairs."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from cjm_substrate_qt_kit.hitl import (fmt_ts, HitlPanel, ProposalWorklist, ProvenancePane,
                                       VerdictStrip, worklist_row)
from cjm_substrate_qt_kit.theme import current_theme, state_color


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def items():
    return [
        {"key": "p1", "tier": 1, "category": "apparatus", "start": 3.0, "end": 4.8,
         "confidence": 0.95, "quote": "Forward by David Perel.", "index": 0},
        {"key": "p2", "tier": 2, "category": "research-mark", "start": 43.1, "end": 50.8,
         "confidence": 0.35, "quote": "docile and obedient", "index": 12},
        {"key": "p3", "tier": 1, "category": "quotation", "start": 249.8, "end": 279.8,
         "confidence": None, "quote": "Gatto wrote", "index": 89, "state": "accepted"},
    ]


def test_fmt_ts_and_row_projection(app):
    assert fmt_ts(None) == "--:--" and fmt_ts(3.0) == "00:03.0" and fmt_ts(279.75) == "04:39.8"
    r1 = worklist_row(items()[0])
    flat = "".join(t for t, _ in r1["spans"])
    assert flat.startswith("? apparatus") and "00:03.0–00:04.8" in flat and "c=0.95" in flat
    assert "“Forward by David Perel.”" in flat and r1["key"] == "p1"
    r2 = worklist_row(items()[1])
    flat2 = "".join(t for t, _ in r2["spans"])
    assert flat2.startswith("??research-mark") and r2["spans"][1][1].endswith("magenta")
    r3 = worklist_row(items()[2])
    flat3 = "".join(t for t, _ in r3["spans"])
    assert flat3.endswith("[accepted]") and "c=" not in flat3


def test_worklist_items_cursor_and_payload_slot(app):
    moves, picks = [], []
    w = ProposalWorklist(on_cursor=moves.append, on_activate=picks.append)
    w.set_items(items(), cursor=1, header="LG Foreword · set e006880d")
    assert w.count() == 3 and w.current_key() == "p2"
    assert w.current_item()["category"] == "research-mark"
    assert w.plain_text().splitlines()[0] == "LG Foreword · set e006880d"
    w.move(1)
    assert w.current_key() == "p3" and moves == [2]
    w.activate()
    assert picks == ["p3"]
    assert w.picker.detail.isHidden()
    w.set_payload([[("Why: ", "dim"), ("boilerplate", "")], [("Quote: ", "dim"), ("“x”", "")]])
    assert not w.picker.detail.isHidden()
    w.set_items([], cursor=0)
    assert w.count() == 0 and w.current_item() is None
    assert "(no pending proposals)" in w.plain_text()


def test_verdict_strip_paints_nonempty_tiers_by_role(app):
    t = current_theme()
    strip = VerdictStrip()
    strip.set_verdicts({"accepted": 9, "edited": 2, "relabeled": 0, "rejected": 0, "unvisited": 0},
                       {"accepted": 0, "edited": 0, "relabeled": 0, "unaccepted": 0, "unvisited": 0},
                       watermark="935.0s", extra="22 live strata")
    plain = strip.plain_text()
    assert plain.startswith("tier-1: accepted 9 · edited 2") and "tier-2" not in plain
    assert "watermark 935.0s" in plain and plain.endswith("22 live strata")
    assert state_color("ok", t).name() in strip.text()      # accepted paints ok
    assert state_color("info", t).name() in strip.text()    # edited paints info
    strip.set_verdicts(None, None, watermark=None)
    assert strip.plain_text() == ""


def test_provenance_pane_escapes_and_lists(app):
    pane = ProvenancePane(budget_rows=3)
    assert "(no provenance)" in pane.toHtml()
    pane.set_entries([("set", "propset_20260901_202802_e006880d"),
                      ("proposer", "claude-code-subagent:reader-lg02 <fable>"),
                      ("window", None)])
    assert pane.entries()[2] == ("window", "")
    assert pane.plain_text().splitlines()[0] == "set: propset_20260901_202802_e006880d"
    assert "&lt;fable&gt;" in pane.toHtml()


def test_panel_composes_the_three(app):
    panel = HitlPanel()
    panel.worklist.set_items(items())
    panel.verdicts.set_verdicts({"accepted": 1})
    panel.provenance.set_entries([("actor", "human")])
    assert panel.worklist.count() == 3
    assert panel.verdicts.plain_text() == "tier-1: accepted 1"
    assert panel.provenance.plain_text() == "actor: human"
    panel.restyle()


def test_worklist_detail_sits_above_the_rows_by_default(app):
    """User ruling 2026-09-02: the focused proposal's card (the 'Why:') is
    what the eye checks first, so it sits ABOVE the listing; PickerList keeps
    rows-first as its own default for the pickers."""
    from cjm_substrate_qt_kit.hitl import ProposalWorklist
    from cjm_substrate_qt_kit.pickerlist import PickerList
    w = ProposalWorklist()
    lay = w.picker.layout()
    assert lay.itemAt(0).widget() is w.picker.detail
    assert lay.itemAt(1).widget() is w.picker.view
    p = PickerList()
    assert p.layout().itemAt(0).widget() is p.view
    w2 = ProposalWorklist(detail_above=False)
    assert w2.picker.layout().itemAt(0).widget() is w2.picker.view


def test_unchanged_items_do_not_rebuild_the_rows(app, monkeypatch):
    """Per-frame lag on multi-hour spines (2026-09-02): a walk step re-sent
    the same ~2800 items and the picker re-minted every Qt row. Unchanged
    items + header only move the cursor."""
    from cjm_substrate_qt_kit.hitl import ProposalWorklist
    w = ProposalWorklist()
    items = [{"key": f"p{i}", "tier": 1, "category": "inhale", "start": float(i), "end": i + 0.5,
              "confidence": 0.9, "quote": f"q{i}", "index": i} for i in range(5)]
    w.set_items(items, cursor=0, header="set x")
    rebuilt = []
    monkeypatch.setattr(w.picker, "set_rows", lambda rows, cursor=None: rebuilt.append(len(rows)))
    w.set_items(list(items), cursor=3, header="set x")      # same content, new cursor
    assert rebuilt == [] and w.cursor == 3
    w.set_items(items[:4], cursor=1, header="set x")        # an accept removed a row
    assert rebuilt == [5]                                    # header + 4 rows
    w.set_items(items[:4], cursor=1, header="set y")        # header changed
    assert rebuilt == [5, 5]


def test_delegate_size_hint_is_memoized(app):
    from PySide6.QtCore import QModelIndex
    from PySide6.QtWidgets import QListWidget, QListWidgetItem, QStyleOptionViewItem
    from cjm_substrate_qt_kit.pickerlist import SpanRowDelegate, _ROW_HTML
    lst = QListWidget()
    for i in range(3):
        it = QListWidgetItem()
        it.setData(_ROW_HTML, "<div style='white-space:pre'>row</div>" if i < 2 else "<div>other</div>")
        lst.addItem(it)
    d = SpanRowDelegate(lst)
    opt = QStyleOptionViewItem()
    opt.font = lst.font()
    a = d.sizeHint(opt, lst.model().index(0, 0))
    b = d.sizeHint(opt, lst.model().index(1, 0))
    c = d.sizeHint(opt, lst.model().index(2, 0))
    assert a == b and a.height() > 0
    assert len(d._sizes) == 2          # two distinct fragments, one cache entry each
    assert c.height() == a.height()
