#!/usr/bin/env python3

"""
App module for generating and showing a random number.
"""

import sys

from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtWidgets import (QApplication, QMainWindow, QDockWidget, QWidget,
                             QVBoxLayout, QComboBox, QPushButton, QLabel)

from swift.app import BaseApp
from apps.backend import generate, write

class GeneratorFrame(QWidget):
    """Frame for requesting generating a random number.
    
    Attributes:
        dbBox: A combobox for selecting a database 
          into which the generated number is saved.
        generateButton: A button for generating a new number.
    """
    def __init__(self, parent=None):
        """
        Args:
            parent: A parent widget.
        """
        super().__init__(parent=parent)
        # TODO(BECATRUE): Remove mock_db when connecting to real databases is implemented.
        # For testing whether dbBox works correctly, I added a definite path temporarily.
        # Later, It will have to be implemented as below.
        # - When this frame is created, dbList is created as ["None"]
        # - When this app receives a global signal from database bus, dbList is updated.
        self.dbList = ["None", "./db.sqlite"]
        self._initWidget()

    def _initWidget(self):
        """Initializes widgets in the frame."""
        self.dbBox = QComboBox(self)
        for dbPath in self.dbList:
            self.dbBox.addItem(dbPath)
        self.generateButton = QPushButton("generate number", self)
        # set layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.dbBox)
        layout.addWidget(self.generateButton)


class ViewerFrame(QWidget):
    """Frame for showing the generated number.

    Attributes:
        statusLabel: A label for showing the current status.
          (database updated, random number generated, etc.)
        numberLabel: A label for showing the recently generated number.
    """
    def __init__(self, parent=None):
        """
        Args:
            parent: A parent widget.
        """
        super().__init__(parent=parent)
        self._initWidget()

    def _initWidget(self):
        """Initializes widgets in the frame."""
        self.statusLabel = QLabel("initialized", self)
        self.numberLabel = QLabel("not generated", self)
        # set layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.statusLabel)
        layout.addWidget(self.numberLabel)


class NumGenApp(BaseApp):
    """App for generating and showing a random number.

    Manage a generator frame and a viewer frame.
    Communicate with the backend.

    Attributes:
        generatorFrame: A frame that requests generating a random number.
        viewerFrame: A frame that shows the generated number.
    """
    def __init__(self, name: str):
        super().__init__(name)
        self.dbPath = "None"
        self.generatorFrame = GeneratorFrame()
        self.viewerFrame = ViewerFrame()
        # connect signals to slots
        self.generatorFrame.dbBox.currentIndexChanged.connect(self.setDatabase)
        self.generatorFrame.generateButton.clicked.connect(self.generateNumber)

    def frames(self):
        """Gets frames for which are managed by the app.

        Returns:
            A tuple containing frames for showing.
        """
        return (self.generatorFrame, self.viewerFrame)

    @pyqtSlot()
    def setDatabase(self):
        """Sets the database to store the number."""
        self.dbPath = self.generatorFrame.dbBox.currentText()
        self.viewerFrame.statusLabel.setText("database updated")

    @pyqtSlot()
    def generateNumber(self):
        """Generates and shows a random number when the button is clicked."""
        # generate a random number
        num = generate()
        self.viewerFrame.numberLabel.setText(f"generated number: {num}")
        # save the generated number
        is_save_success = write(self.dbPath, "number", num)
        if is_save_success:
            self.viewerFrame.statusLabel.setText("number saved successfully")
        else:
            self.viewerFrame.statusLabel.setText("failed to save number")


def main():
    """Main function that runs when numgen module is executed rather than imported."""
    _app = QApplication(sys.argv)
    mainWindow = QMainWindow()
    # create an app
    app = NumGenApp("numgen")
    # get frames from the app and add them as dock widgets
    for frame in app.frames():
        dockWidget = QDockWidget("random number generator", mainWindow)
        dockWidget.setWidget(frame)
        mainWindow.addDockWidget(Qt.LeftDockWidgetArea, dockWidget)
    mainWindow.show()
    _app.exec_()


if __name__ == "__main__":
    main()
