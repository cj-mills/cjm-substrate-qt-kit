"""FormShell contract (work item d55292f9): fixed chrome around a native
row body — the header carries the mouse-close anchor and never scrolls,
the footer holds whatever the subclass paints there, the esc ladder closes
an open editor before the dialog, and open_sized sizes to the rendered
rows capped by the owner."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication

from cjm_substrate_qt_kit.formdialog import FormShell


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def rows():
    return [{"kind": "item", "spans": [("  Seed: ", ""), ("42", "bold")],
             "key": "seed"},
            {"kind": "item", "spans": [("  Epochs: ", ""), ("20", "bold")],
             "key": "max_epochs"}]


def test_chrome_is_fixed_and_carries_the_close_anchor(app):
    dlg = FormShell(None)
    dlg.set_header("FINETUNE — demo")
    dlg.set_footer("j/k move · esc cancel")
    dlg.body.set_rows(rows(), cursor=0)
    assert 'href="close:"' in dlg.head.toHtml()
    assert "FINETUNE — demo" in dlg.head.toPlainText()
    assert "esc cancel" in dlg.foot.text()
    assert "Seed" in dlg.body.plain_text()
    dlg.open_sized()
    assert dlg.isVisible()
    dlg._on_anchor(QUrl("pin:x"))     # any other anchor is ignored
    assert dlg.isVisible()
    dlg._on_anchor(QUrl("close:"))    # the header's mouse close
    assert not dlg.isVisible()
    dlg.close()


def test_esc_ladder_closes_the_editor_first(app):
    dlg = FormShell(None)
    dlg.body.set_rows(rows(), cursor=0)
    dlg.open_sized()
    dlg.open_editor("42")
    assert dlg.editor.isVisible() and dlg.editor.text() == "42"
    dlg.reject()                      # step one: the editor closes
    assert not dlg.editor.isVisible() and dlg.isVisible()
    dlg.reject()                      # step two: the dialog goes
    assert not dlg.isVisible()
    dlg.close()


def test_cursor_and_activation_route_through_the_body(app):
    seen = {"cursor": [], "activated": []}
    dlg = FormShell(None, on_cursor=seen["cursor"].append,
                    on_activate=seen["activated"].append)
    dlg.body.set_rows(rows(), cursor=0)
    dlg.body.move(1)
    dlg.body.activate()
    assert seen["cursor"] == [1]
    assert seen["activated"] == ["max_epochs"]
