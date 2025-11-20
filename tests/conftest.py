import sys
import pytest
from PyQt6.QtWidgets import QApplication

# ...existing code...

@pytest.fixture(scope="session", autouse=True)
def qapp():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    return app