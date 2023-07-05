"""
App module for logging.
"""

import time
import logging
from typing import Any, Optional, Tuple 
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTextEdit, QLabel, QDialogButtonBox
from qiwis import BaseApp


class Signaller(QObject):
    """Signal for LoggingHandler."""
    signal = pyqtSignal(str)


class LoggingHandler(logging.Handler):
    """Handler for logger.

    Sends a log message to connected function using emit.
    """

    def __init__(self, slotfunc):
        """Connect an input function to the signal.

        Args:
            slotfunc: method function connected to signal.
        """
        super().__init__()
        self.signaller = Signaller()
        self.signaller.signal.connect(slotfunc)

    def emit(self, record: logging.LogRecord):
        """ Emits input signal to connected function."""
        s = self.format(record)
        self.signaller.signal.emit(s)


class LoggerFrame(QWidget):
    """Frame for logging.

    Attributes:
        logEdit: A textEdit which shows all logs.
        clearButton: A button for clearing all logs.
    """

    def __init__(self, parent: Optional[QObject] = None):
        """Extended."""
        super().__init__(parent=parent)
        # widgets
        self.logEdit = QTextEdit(self)
        self.logEdit.setReadOnly(True)
        self.clearButton = QPushButton("Clear")
        # layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.logEdit)
        layout.addWidget(self.clearButton)