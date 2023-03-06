"""
App module for logging.
"""

import sys

from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtWidgets import (QApplication, QMainWindow, QDockWidget, QWidget,
                             QVBoxLayout, QPushButton, QTextEdit)

from swift.app import BaseApp

class LoggerFrame(QWidget):
    """Frame for logging.
    
    Attributes:
        textEdit: A textEdit which shows all logs.
        clearButton: A button for clearing all logs.
    """
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.logEdit = QTextEdit(self)
        self.clearButton = QPushButton(self)
        
        layout = QVBoxLayout(self)
        layout.addWidget(self.logEdit)
        layout.addWidget(self.clearButton)

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
        self.loggerFrame.clearButton.clicked.connect(self.clearLog)

    def frames(self):
        """Gets frames for which are managed by the app.

        Returns:
            A tuple containing frames for showing.
        """
        return (self.loggerFrame, )

    @pyqtSlot(str, str)
    def addLog(self, bus_name, msg):
        """Add a log message and bus name"""
        self.loggerFrame.logEdit.insertPlainText(f"[{bus_name}]: {msg}")

    @pyqtSlot()
    def clearLog(self):
        """Clear the log text edit"""
        self.loggerFrame.logEdit.clear()

def main():
    """Main function that runs when numgen module is executed rather than imported."""
    _app = QApplication(sys.argv)
    mainWindow = QMainWindow()
    # create an app
    app = LoggerApp("logger")
    # get frames from the app and add them as dock widgets
    for frame in app.frames():
        dockWidget = QDockWidget("logger", mainWindow)
        dockWidget.setWidget(frame)
        mainWindow.addDockWidget(Qt.LeftDockWidgetArea, dockWidget)
    mainWindow.show()
    _app.exec_()


if __name__ == "__main__":
    main()
