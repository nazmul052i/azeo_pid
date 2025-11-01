from __future__ import annotations
from datetime import datetime
from PySide6 import QtWidgets


class ConsolePanel(QtWidgets.QPlainTextEdit):
    """
    Simple console with timestamped logging and auto-scroll.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)

    def log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.appendPlainText(f"[{ts}] {msg}")
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
