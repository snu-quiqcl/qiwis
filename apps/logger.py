"""
App module for logging.
"""

import time

from PyQt5.QtCore import pyqtSlot, pyqtSignal
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QTextEdit, QLabel)

from swift.app import BaseApp

class LoggerFrame(QWidget):
    """Frame for logging.
    
    Attributes:
        logEdit: A textEdit which shows all logs.
        clearButton: A button for clearing all logs.
    """
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.logEdit = QTextEdit(self)
        self.logEdit.setReadOnly(True)
        self.clearButton = QPushButton("Clear")

        layout = QVBoxLayout(self)
        layout.addWidget(self.logEdit)
        layout.addWidget(self.clearButton)


class ConfirmClearingFrame(QWidget):
    """
    A confirmation frame for log clearing.
    """
    confirmed = pyqtSignal()

    def __init__(self):
        """
        Initializes confirmation frame
        """
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.label = QLabel("Are you sure to clear?")
        self.buttonOK = QPushButton("OK")
        self.buttonCancel = QPushButton("Cancel")
        layout.addWidget(self.label)
        layout.addWidget(self.buttonOK)
        layout.addWidget(self.buttonCancel)

        self.buttonOK.clicked.connect(self.buttonOKClicked)
        self.buttonCancel.clicked.connect(self.buttonCancelClicked)

    def buttonOKClicked(self):
        """Clicks OK to clear log.
        """
        self.confirmed.emit()
        self.close()

    def buttonCancelClicked(self):
        """Clicks Cancel not to clear log
        """
        self.close()


class LoggerApp(BaseApp):
    """App for logging.

    Manage a logger frame.

    Attributes:
        loggerFrame: A frame that shows the logs.
    """
    def __init__(self, name: str):
        super().__init__(name)
        self.loggerFrame = LoggerFrame()

        # connect signals to slots
        self.received.connect(self.addLog)
        self.loggerFrame.clearButton.clicked.connect(self.checkToClear)
        self.confirmFrame = ConfirmClearingFrame()
        self.confirmFrame.confirmed.connect(self.clearLog)

    def frames(self):
        """Gets frames for which are managed by the app.

        Returns:
            A tuple containing frames for showing.
        """
        return (self.loggerFrame,)

    @pyqtSlot(str, str)
    def addLog(self, busName, msg):
        """Adds a bus name and log message.

        Args:
            busName (str): the name of bus
            msg (str): log message
        """
        self.loggerFrame.logEdit.insertPlainText(
            f"{time.strftime('%c', time.localtime(time.time()))}[{busName}]: {msg}\n")

    @pyqtSlot()
    def checkToClear(self):
        """Show a confirmation frame for log clearing.
        """
        self.confirmFrame.show()

    @pyqtSlot()
    def clearLog(self):
        """Clear the log text edit
        """
        self.loggerFrame.logEdit.clear()
