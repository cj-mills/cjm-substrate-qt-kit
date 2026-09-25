"""Shared test scaffolding for the kit: every widget test runs on the
offscreen platform plugin against ONE QApplication (a second instance in
the same process is a Qt error), so the platform pin and the `app` fixture
live here once instead of at the head of each test module (the kit's
charter housekeeping, ruling 8b7351e4). Pure-model tests (configform,
text, layout, keymap data) need neither and simply do not ask for `app`."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def app():
    """The process-wide QApplication (created on first use, reused after)."""
    return QApplication.instance() or QApplication([])
