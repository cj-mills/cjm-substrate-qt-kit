"""The job seat (ruling 2bae2cc1 (5)): a row per running job, hidden when
idle, progress and outcomes reported through the seat's signal."""

from cjm_substrate_qt_kit.jobs import JobSeat, fmt_elapsed


def test_rows_come_and_go_with_the_outcome_signal(app):
    seat = JobSeat()
    seen = []
    seat.job_done.connect(lambda label, text, role: seen.append((label, text, role)))
    assert not seat.isVisibleTo(seat.parentWidget() or seat) and seat.count() == 0
    job = seat.start("finetune")
    assert seat.count() == 1 and seat.isVisibleTo(seat)
    assert job.bar.maximum() == 0                           # indeterminate
    job.progress(3, 10, "epoch 3")
    assert (job.bar.minimum(), job.bar.maximum(), job.bar.value()) == (0, 10, 3)
    assert job.label.text() == "finetune — epoch 3"
    job.finish()
    assert seat.count() == 0 and not seat.isVisibleTo(seat)
    assert seen == [("finetune", "finetune done", "ok")]
    job.finish()                                            # idempotent
    assert len(seen) == 1


def test_fail_and_cancel(app):
    seat = JobSeat()
    seen = []
    seat.job_done.connect(lambda label, text, role: seen.append((text, role)))
    cancelled = []
    a = seat.start("export")
    b = seat.start("propose", on_cancel=lambda: cancelled.append(1))
    assert b.cancel_btn.isVisibleTo(b.row) and not a.cancel_btn.isVisibleTo(a.row)
    a.fail("⚠ export: boom")
    b.cancel_btn.click()
    assert cancelled == [1]
    assert seen == [("⚠ export: boom", "danger"), ("propose cancelled", "warn")]
    assert seat.count() == 0


def test_elapsed_format():
    assert fmt_elapsed(0) == "0:00" and fmt_elapsed(65) == "1:05" and fmt_elapsed(3600) == "60:00"
