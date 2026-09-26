"""The kit modal frame (ruling d1e3043e (2), finding 533d53d0): every
dialog is a translucent host around a painted frame — transparent beyond
the frame, the frame's border on the dialog's own edge — and the
widget-built dialogs (prompt, confirm, notice) ride it. Modal OPENING stays
with test_keyhints (the register's offscreen active-window hazard): these
tests show non-modal frames or setVisible a dialog without open()."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QTextBrowser, QWidget

from cjm_substrate_qt_kit.formdialog import FormShell
from cjm_substrate_qt_kit.keyhints import KeyHintsOverlay
from cjm_substrate_qt_kit.modal import Confirm, Dialog, ModalFrame, Notice, TextPrompt
from cjm_substrate_qt_kit.theme import apply_theme


def test_modal_frame_is_translucent_and_frameless(app):
    dlg = ModalFrame(None, modal=False)
    assert dlg.windowFlags() & Qt.WindowType.FramelessWindowHint
    assert dlg.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    assert dlg.property("kitModalHost") is True and dlg.frame.property("kitModal") is True
    assert dlg.inner.contentsMargins().left() == 1


def test_frame_paints_transparent_corners_and_border_on_its_edge(app):
    """The finding's DoD: alpha 0 at (0,0) beyond the radius; the frame's
    border on the dialog's own edge; the surface color inside."""
    t = apply_theme(app, "classical", "light")
    owner = QWidget()
    owner.resize(900, 700)
    dlg = ModalFrame(owner, modal=False)
    view = QTextBrowser(dlg.frame)
    view.setHtml("<p>hello</p>")
    dlg.inner.addWidget(view)
    dlg.resize(300, 200)
    dlg.show()
    app.processEvents()
    img = dlg.grab().toImage()
    assert img.pixelColor(0, 0).alpha() == 0
    assert img.pixelColor(0, 100).alpha() == 255                # the border column
    assert img.pixelColor(0, 100).name() != t.vars["surface"]
    assert img.pixelColor(150, 100).name() == t.vars["surface"]  # the view is transparent over it
    dlg.close()


def test_overlay_and_formshell_sit_on_the_frame(app):
    owner = QWidget()
    owner.resize(900, 700)
    ov = KeyHintsOverlay(owner, [{"verb": "q", "label": "quit", "key": "Q", "group": ""}])
    assert isinstance(ov, ModalFrame) and ov.view.parent() is ov.frame
    ov._render()
    assert "quit" in ov.view.toPlainText()
    form = FormShell(None)
    assert isinstance(form, ModalFrame) and form.body.parent() is form.frame
    form.set_header("A FORM")
    assert "A FORM" in form.head.toPlainText()


def test_dialog_header_buttons_and_focus(app):
    dlg = Dialog(None, "Unsubscribe")
    assert dlg.header.title.text() == "Unsubscribe"
    assert dlg.header.close_btn.property("verb") == "close"
    seen = []
    ok = dlg.add_button("Yes", variant="primary", default=True, on_click=lambda: seen.append("yes"))
    assert ok.property("variant") == "primary" and ok.isDefault()
    dlg.set_focus(ok)
    dlg.setVisible(True)
    app.processEvents()
    ok.click()
    assert seen == ["yes"]
    dlg.header.close_btn.click()
    assert dlg.result() == QDialog.DialogCode.Rejected and not dlg.isVisible()


def test_text_prompt_value_on_accept_none_on_cancel(app):
    dlg = TextPrompt(None, "search", "literal term:", default="seed")
    dlg.setVisible(True)
    assert dlg.field.text() == "seed"
    dlg.field.setText("needle")
    dlg.ok_btn.click()
    assert dlg.value() == "needle"
    other = TextPrompt(None, "search", "literal term:")
    other.setVisible(True)
    other.cancel_btn.click()
    assert other.value() is None


def test_confirm_and_notice(app):
    yes = Confirm(None, "Retract", "Retract it?", ok="Retract", danger=True)
    assert yes.ok_btn.property("role") == "danger"
    yes.setVisible(True)
    yes.ok_btn.click()
    assert yes.answer() is True
    no = Confirm(None, "Retract", "Retract it?")
    no.setVisible(True)
    no.cancel_btn.click()
    assert no.answer() is False
    n = Notice(None, "Done", "all good")
    n.setVisible(True)
    n.ok_btn.click()
    assert n.result() == QDialog.DialogCode.Accepted
