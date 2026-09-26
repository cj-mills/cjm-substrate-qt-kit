"""The JOB SEAT (ruling 2bae2cc1 (5)): a progress surface for long-running
work, in the window. The transcription and decomp apps EXIT to run and the
user watches a terminal log — the hand_off-after-window-exit carryover from
the Textual TUIs, a defect class. Here a run is a row in the seat: label,
a progress bar (indeterminate until the job reports a total), elapsed time,
an optional cancel; the seat hides when idle and the job's outcome lands
on the shell's readout. Never a text-only readout; a run never requires
leaving the window."""

import time
from typing import Callable, List, Optional

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QToolButton, QVBoxLayout, QWidget

from .theme import on_change


def fmt_elapsed(seconds: float) -> str:
    s = max(0, int(seconds))
    return f"{s // 60}:{s % 60:02d}"


class Job(QObject):
    """One running job: progress(done, total) moves the bar, finish() /
    fail() close the row and report through the seat."""

    def __init__(self, seat: "JobSeat", label: str, *,
                 on_cancel: Optional[Callable[[], None]] = None):
        super().__init__(seat)
        self.seat = seat
        self.label_text = label
        self.started = time.time()
        self.done = False
        self._on_cancel = on_cancel
        self.row = QWidget(seat)
        self.row.setProperty("role", "job-row")
        self.label = QLabel(label, self.row)
        self.label.setProperty("role", "job-label")
        self.bar = QProgressBar(self.row)
        self.bar.setRange(0, 0)               # indeterminate until a total is known
        self.bar.setTextVisible(False)
        self.bar.setMinimumWidth(140)
        self.elapsed = QLabel(fmt_elapsed(0), self.row)
        self.elapsed.setProperty("role", "dim")
        self.cancel_btn = QToolButton(self.row)
        self.cancel_btn.setProperty("role", "window-verb")
        self.cancel_btn.setProperty("verb", "cancel")
        self.cancel_btn.setToolTip("Cancel")
        self.cancel_btn.setAutoRaise(True)
        self.cancel_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.cancel_btn.setVisible(on_cancel is not None)
        self.cancel_btn.clicked.connect(lambda _c=False: self.cancel())
        lay = QHBoxLayout(self.row)
        lay.setContentsMargins(8, 3, 8, 3)
        lay.setSpacing(10)
        lay.addWidget(self.label, 1)
        lay.addWidget(self.bar)
        lay.addWidget(self.elapsed)
        lay.addWidget(self.cancel_btn)

    def progress(self, done: int, total: Optional[int] = None,
                 text: Optional[str] = None) -> None:
        if total is not None and total > 0:
            self.bar.setRange(0, int(total))
            self.bar.setValue(int(done))
        if text:
            self.label.setText(f"{self.label_text} — {text}")

    def tick(self) -> None:
        self.elapsed.setText(fmt_elapsed(time.time() - self.started))

    def finish(self, text: Optional[str] = None, role: str = "ok") -> None:
        self._close(text if text is not None else f"{self.label_text} done", role)

    def fail(self, text: Optional[str] = None) -> None:
        self._close(text if text is not None else f"{self.label_text} failed", "danger")

    def cancel(self) -> None:
        if self._on_cancel is not None:
            self._on_cancel()
        self._close(f"{self.label_text} cancelled", "warn")

    def _close(self, text: str, role: str) -> None:
        if self.done:
            return
        self.done = True
        self.seat._remove(self, text, role)


class JobSeat(QWidget):
    """The rows of running jobs; hidden while empty. `job_done(label, text,
    role)` fires when a row closes — the shell paints it on the readout."""

    job_done = Signal(str, str, str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setProperty("role", "jobseat")
        self._jobs: List[Job] = []
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(0)
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self.setVisible(False)
        on_change(self._on_theme)

    def start(self, label: str, *, on_cancel: Optional[Callable[[], None]] = None) -> Job:
        job = Job(self, label, on_cancel=on_cancel)
        self._jobs.append(job)
        self._lay.addWidget(job.row)
        self.setVisible(True)
        if not self._timer.isActive():
            self._timer.start()
        return job

    def jobs(self) -> List[Job]:
        return list(self._jobs)

    def count(self) -> int:
        return len(self._jobs)

    def _tick(self) -> None:
        for job in self._jobs:
            job.tick()

    def _remove(self, job: Job, text: str, role: str) -> None:
        if job in self._jobs:
            self._jobs.remove(job)
        self._lay.removeWidget(job.row)
        job.row.deleteLater()
        if not self._jobs:
            self._timer.stop()
            self.setVisible(False)
        self.job_done.emit(job.label_text, text, role)

    def _on_theme(self, _theme) -> None:
        self.update()
