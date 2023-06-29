"""
App module for logging.
"""

import time
import logging
from typing import Any, Optional, Tuple

from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTextEdit, QLabel, QDialogButtonBox

from qiwis import BaseApp

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Handler for dealing input log to logger
class LoggingHandler(QObject, logging.Handler):
    signal = pyqtSignal(str)
    def __init__(self, slotfunc, *args, **kwargs):
        super(LoggingHandler, self).__init__(*args, **kwargs)
        self.signal.connect(slotfunc)

    # Works when signal inserted to logger, and handler is in the logger
    def emit(self, record):
        s = self.format(record)
        self.signal.emit(s)

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
        self.levelButton = QPushButton("Set logger level")
        # layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.logEdit)
        layout.addWidget(self.clearButton)
        layout.addWidget(self.levelButton)


class ConfirmClearingFrame(QWidget):
    """
    A confirmation frame for log clearing.
    """
    confirmed = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None):
        """
        Extended.
        """
        super().__init__(parent=parent)
        # widgets
        self.label = QLabel("Are you sure to clear?")
        self.buttonBox = QDialogButtonBox()
        self.buttonBox.addButton("OK", QDialogButtonBox.AcceptRole)
        self.buttonBox.addButton("Cancel", QDialogButtonBox.RejectRole)
        # connect signals
        self.buttonBox.accepted.connect(self.buttonOKClicked)
        self.buttonBox.rejected.connect(self.buttonCancelClicked)
        # layouts
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.addWidget(self.label)
        layout.addWidget(self.buttonBox)

    def buttonOKClicked(self):
        """Clicks OK to clear log."""
        self.confirmed.emit()
        self.close()

    def buttonCancelClicked(self):
        """Clicks Cancel not to clear log."""
        self.close()

class SetLevelFrame(QWidget):

    def __init__(self, parent: Optional[QObject] = None):

        super().__init__(parent=parent)
        # widgets
        self.label = QLabel("Select logger level")
        self.buttonBox = QDialogButtonBox()
        self.buttonBox.addButton("DEBUG", QDialogButtonBox.ActionRole)
        self.buttonBox.addButton("INFO", QDialogButtonBox.ActionRole)
        self.buttonBox.addButton("WARNING", QDialogButtonBox.ActionRole)
        self.buttonBox.addButton("ERROR", QDialogButtonBox.ActionRole)
        self.buttonBox.addButton("CRITICAL", QDialogButtonBox.ActionRole)
        self.buttonBox.addButton("Cancel", QDialogButtonBox.RejectRole)

        # connect signals
        self.buttonBox.clicked.connect(self.buttonClicked)
        # layouts
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.addWidget(self.label)
        layout.addWidget(self.buttonBox)

    # change logger level by sensing which button is pressed
    def buttonClicked(self, button):
        if button.text() == "DEBUG":
            logger.setLevel(logging.DEBUG)
        elif button.text() == "INFO":
            logger.setLevel(logging.INFO)
        elif button.text() == "WARNING":
            logger.setLevel(logging.WARNING)
        elif button.text() == "ERROR":
            logger.setLevel(logging.ERROR)
        elif button.text() == "CRITICAL":
            logger.setLevel(logging.CRITICAL)
        elif button.text() == "Cancel":
            self.close()      
                  
class LoggerApp(BaseApp):
    """App for logging.

    Manages a logger frame.

    Attributes:
        loggerFrame: A frame that shows the logs.
    """
    def __init__(self, name: str, parent: Optional[QObject] = None):
        """Extended.

        Args:
            name: Name of the App
        """
        super().__init__(name, parent=parent)
        self.loggerFrame = LoggerFrame()
        # connect signals to slots
        self.loggerFrame.clearButton.clicked.connect(self.checkToClear)
        self.confirmFrame = ConfirmClearingFrame()
        self.confirmFrame.confirmed.connect(self.clearLog)
        self.loggerFrame.levelButton.clicked.connect(self.selectLevel)
        self.setlevelFrame = SetLevelFrame()
        # define handler
        self.handler = LoggingHandler(self.addLog)
        # arbitrary format
        fs ="%(name)s %(message)s"
        formatter = logging.Formatter(fs)
        self.handler.setFormatter(formatter)
        logger.addHandler(self.handler)

    def frames(self) -> Tuple[LoggerFrame]:
        """Overridden."""
        return (self.loggerFrame,)
    
    @pyqtSlot(str)
    def addLog(self, content: str):
        """Adds a channel name and log message.

        Args:
            content: Received log message.
        """
        timeString = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
        self.loggerFrame.logEdit.insertPlainText(f"{timeString}: {content}\n")

    def receivedSlot(self, channelName: str, content: Any):
        """Overridden.

        Possible channels are as follows.

        "log": Log channel.
            See self.addLog().
        """
        if channelName == "log":
            if isinstance(content, str):
                self.addLog(content)
            else:
                print("The message for the channel log should be a string.")
        else:
            print(f"The message was ignored because "
                  f"the treatment for the channel {channelName} is not implemented.")
            
    @pyqtSlot()
    def selectLevel(self):
        """"shows a level select frame"""
        self.setlevelFrame.show()

    @pyqtSlot()
    def checkToClear(self):
        """Shows a confirmation frame for log clearing."""
        self.broadcast("log", "Clicked to clear logs")
        self.confirmFrame.show()

    @pyqtSlot()
    def clearLog(self):
        """Clears the log text edit."""
        self.loggerFrame.logEdit.clear()
