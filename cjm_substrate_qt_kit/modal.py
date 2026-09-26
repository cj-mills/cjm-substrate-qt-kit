"""ONE kit modal frame (ruling d1e3043e (2); finding 533d53d0).

Kit modals were a square opaque slab with the rounded frame on the INNER
view: the frameless QDialog painted its whole rect in the surface color
with no radius, while the border + radius the eye read belonged to the
QTextBrowser inside through the generic input rule — and its accent color
was the :focus rule firing because the view takes focus. Here the DIALOG
owns its frame, the same way the shell window does (`frame`): the host is
a frameless, translucent QDialog that paints nothing; its child
QFrame[kitModal="true"] carries background, border and radius from the
tokens; the corners beyond the radius are transparent; the inner views are
borderless and transparent (the systems' stylesheets say so). The
?-overlay, the FormShell and every widget-built dialog (`Dialog`, the
prompts) inherit it, so a design system's radius reaches every modal.

`modal_bounds` / `open_centered` — the ONE sizing + centering path every
kit modal takes — live here (keyhints re-exports them for its callers)."""

from typing import Callable, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QVBoxLayout, QWidget)

from .theme import on_change
from .widgets import button, text


def modal_bounds(dialog: QWidget) -> Tuple[int, int]:
    """(avail_w, avail_h) a kit modal may occupy: the owner's size less a
    64 px margin on each axis, or a 960x640 fallback when ownerless (tests,
    detached probes). Callers size their content against these bounds and
    hand the result to open_centered, which caps again by the same rule."""
    owner = dialog.parentWidget()
    if owner is None:
        return 960, 640
    return owner.width() - 64, owner.height() - 64


def center_over_owner(dialog: QWidget) -> None:
    """Move the dialog to the owner's center (no-op when ownerless)."""
    owner = dialog.parentWidget()
    if owner is not None:
        center = owner.mapToGlobal(owner.rect().center())
        dialog.move(center.x() - dialog.width() // 2,
                    center.y() - dialog.height() // 2)


def open_centered(dialog: QDialog, width: int, height: int,
                  focus: Optional[QWidget] = None) -> None:
    """Open a kit modal centered over its owner at (width, height) capped by
    modal_bounds — the ONE sizing/centering path. QDialog.open is
    non-blocking, but the owner's shortcuts stay inert underneath; `focus`
    (default: the dialog itself) takes the keyboard."""
    avail_w, avail_h = modal_bounds(dialog)
    dialog.resize(min(avail_w, width), min(avail_h, height))
    center_over_owner(dialog)
    dialog.open()
    (focus if focus is not None else dialog).setFocus()


class ModalFrame(QDialog):
    """The translucent host + the painted frame. Subclasses parent their
    widgets to `self.frame` and add them to `self.inner` (the frame's
    vertical layout, with the 1 px border margin)."""

    def __init__(self, parent: Optional[QWidget] = None, *, modal: bool = True):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(modal)
        self.setProperty("kitModalHost", True)
        self.frame = QFrame(self)
        self.frame.setProperty("kitModal", True)
        host = QVBoxLayout(self)
        host.setContentsMargins(0, 0, 0, 0)
        host.setSpacing(0)
        host.addWidget(self.frame)
        self.inner = QVBoxLayout(self.frame)
        self.inner.setContentsMargins(1, 1, 1, 1)
        self.inner.setSpacing(0)

    def open_centered(self, width: int, height: int,
                      focus: Optional[QWidget] = None) -> None:
        open_centered(self, width, height, focus)


class ModalHeader(QFrame):
    """A widget-built modal's title row: the title left, the close verb
    right (the same window-verb glyph the title bar paints); a drag on the
    row moves the dialog through the window manager."""

    def __init__(self, dialog: QDialog, title: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        from .frame import verb_button, verb_icon   # frame imports modal's siblings; keep it lazy
        self.setProperty("role", "modal-header")
        self._dialog = dialog
        self.title = QLabel(title, self)
        self.title.setProperty("role", "modal-title")
        self.close_btn = verb_button(self, "close", "Close", dialog.reject)
        self._verb_icon = verb_icon
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 8, 8, 6)
        lay.setSpacing(8)
        lay.addWidget(self.title, 1)
        lay.addWidget(self.close_btn)
        on_change(self._on_theme)
        self._on_theme(None)

    def _on_theme(self, _theme) -> None:
        self.close_btn.setIcon(self._verb_icon("x"))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self._dialog.windowHandle()
            if handle is not None:
                handle.startSystemMove()
            event.accept()
            return
        super().mousePressEvent(event)


class Dialog(ModalFrame):
    """A widget-built kit dialog: header (title + close), a `content` layout
    the caller fills, a `buttons` row (right-packed). Return / numpad Enter
    fire the default button (QDialog's own rule), Escape rejects; the
    widget named by set_focus takes the keyboard when the dialog shows."""

    def __init__(self, parent: Optional[QWidget] = None, title: str = ""):
        super().__init__(parent)
        self.header = ModalHeader(self, title, self.frame)
        self.content = QVBoxLayout()
        self.content.setContentsMargins(18, 10, 18, 12)
        self.content.setSpacing(12)
        self.buttons = QHBoxLayout()
        self.buttons.setContentsMargins(18, 0, 18, 16)
        self.buttons.setSpacing(8)
        self.buttons.addStretch(1)
        self.inner.addWidget(self.header)
        self.inner.addLayout(self.content)
        self.inner.addLayout(self.buttons)
        self._focus: Optional[QWidget] = None
        self.setWindowTitle(title)

    def set_title(self, title: str) -> None:
        self.header.title.setText(title)
        self.setWindowTitle(title)

    def add_button(self, label: str, *, variant: Optional[str] = None,
                   default: bool = False,
                   on_click: Optional[Callable[[], None]] = None) -> QPushButton:
        b = button(label, variant)
        b.setParent(self.frame)
        b.setAutoDefault(default)
        b.setDefault(default)
        if on_click is not None:
            b.clicked.connect(lambda _checked=False: on_click())
        self.buttons.addWidget(b)
        return b

    def set_focus(self, widget: Optional[QWidget]) -> None:
        self._focus = widget

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._focus is not None:
            self._focus.setFocus()

    def open_sized(self, min_width: int = 440) -> None:
        """Size to the content (never narrower than min_width), open centered."""
        self.adjustSize()
        hint = self.sizeHint()
        self.open_centered(max(min_width, hint.width()), hint.height())

    def exec_centered(self, min_width: int = 440) -> int:
        """The blocking form: size, center, run the modal loop; returns
        QDialog.Accepted / Rejected."""
        self.adjustSize()
        hint = self.sizeHint()
        avail_w, avail_h = modal_bounds(self)
        self.resize(min(avail_w, max(min_width, hint.width())), min(avail_h, hint.height()))
        center_over_owner(self)
        return self.exec()


class TextPrompt(Dialog):
    """One line of text: a label, a field, OK (default) / Cancel. The value
    is the field's text on accept, None on cancel (`value()`)."""

    def __init__(self, parent: Optional[QWidget] = None, title: str = "",
                 label: str = "", default: str = "", placeholder: str = ""):
        super().__init__(parent, title)
        if label:
            self.content.addWidget(text(label, "dialog-body"))
        self.field = QLineEdit(self.frame)
        self.field.setText(default)
        self.field.setPlaceholderText(placeholder)
        self.field.returnPressed.connect(self.accept)
        self.content.addWidget(self.field)
        self.cancel_btn = self.add_button("Cancel", on_click=self.reject)
        self.ok_btn = self.add_button("OK", variant="primary", default=True, on_click=self.accept)
        self.set_focus(self.field)
        self.field.selectAll()

    def value(self) -> Optional[str]:
        return self.field.text() if self.result() == QDialog.DialogCode.Accepted else None


class Confirm(Dialog):
    """A question with two answers; `answer()` is True on the affirmative."""

    def __init__(self, parent: Optional[QWidget] = None, title: str = "",
                 question: str = "", ok: str = "OK", cancel: str = "Cancel",
                 danger: bool = False):
        super().__init__(parent, title)
        self.content.addWidget(text(question, "dialog-body"))
        self.cancel_btn = self.add_button(cancel, on_click=self.reject)
        self.ok_btn = self.add_button(ok, variant="primary", default=True, on_click=self.accept)
        if danger:
            self.ok_btn.setProperty("role", "danger")
        self.set_focus(self.ok_btn)

    def answer(self) -> bool:
        return self.result() == QDialog.DialogCode.Accepted


class Notice(Dialog):
    """A message with one button."""

    def __init__(self, parent: Optional[QWidget] = None, title: str = "",
                 message: str = "", ok: str = "OK"):
        super().__init__(parent, title)
        self.content.addWidget(text(message, "dialog-body"))
        self.ok_btn = self.add_button(ok, variant="primary", default=True, on_click=self.accept)
        self.set_focus(self.ok_btn)


def ask_text(parent: Optional[QWidget], title: str, label: str = "",
             default: str = "", placeholder: str = "") -> Optional[str]:
    """Blocking text prompt (the kit's QInputDialog.getText): the text on
    OK / Return, None on Cancel / Escape."""
    dlg = TextPrompt(parent, title, label, default, placeholder)
    dlg.exec_centered()
    return dlg.value()


def confirm(parent: Optional[QWidget], title: str, question: str,
            ok: str = "OK", cancel: str = "Cancel", danger: bool = False) -> bool:
    """Blocking yes/no (the kit's QMessageBox.question)."""
    dlg = Confirm(parent, title, question, ok, cancel, danger)
    dlg.exec_centered()
    return dlg.answer()


def notice(parent: Optional[QWidget], title: str, message: str, ok: str = "OK") -> None:
    """Blocking message (the kit's QMessageBox.information)."""
    Notice(parent, title, message, ok).exec_centered()
