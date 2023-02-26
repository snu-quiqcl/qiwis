#!/usr/bin/env python3

"""
App module for generating and showing a random number.
"""

import sys

from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtWidgets import (QApplication, QMainWindow, QDockWidget, QWidget,
                             QVBoxLayout, QComboBox, QPushButton, QLabel)

from swift.app import BaseApp
from apps.backend import generate, save

class GeneratorFrame(QWidget):
    """Frame for requesting generating a random number.
    
    Attributes:
        databaseSelector: A combobox for selecting a database 
          into which the generated number is saved.
        generateButton: A button for generating a new number.
    """
    def __init__(self):
        super().__init__()
        self.dbList = ["None", "mock_db"]  # this will be developed later
        self.init_widget()

    def init_widget(self):
        """Initializes widgets in the frame."""
        self.databaseSelector = QComboBox(self)
        for dbName in self.dbList:
            self.databaseSelector.addItem(dbName)
        self.generatorButton = QPushButton("generate number", self)
        # set layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.databaseSelector)
        layout.addWidget(self.generatorButton)


class ViewerFrame(QWidget):
    """Frame for showing the generated number.

    Attributes:
        statusLabel: A label for showing the current status.
          (database updated, random number generated, etc.)
        numberViewer: A label for showing the recently generated number.
    """
    def __init__(self):
        super().__init__()
        self.init_widget()

    def init_widget(self):
        """Initializes widgets in the frame."""
        self.statusLabel = QLabel("initialized", self)
        self.numberViewer = QLabel("not generated", self)
        # set layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.statusLabel)
        layout.addWidget(self.numberViewer)


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
        self.dbName = "None"
        self.generatorFrame = GeneratorFrame()
        self.viewerFrame = ViewerFrame()
        # connect signals to slots
        self.generatorFrame.databaseSelector.currentIndexChanged.connect(self.setDatabase)
        self.generatorFrame.generatorButton.clicked.connect(self.generateNumber)

    def frames(self):
        """Gets frames for which are managed by the app.

        Returns:
            tuple: A tuple containing frames for showing.
        """
        return (self.generatorFrame, self.viewerFrame)

    @pyqtSlot()
    def setDatabase(self):
        """Set the database to store the number."""
        self.dbName = self.generatorFrame.databaseSelector.currentText()
        self.viewerFrame.statusLabel.setText("database updated")

    @pyqtSlot()
    def generateNumber(self):
        """Generates and shows a random number when the button is clicked."""
        # generate a random number
        num = generate()
        self.viewerFrame.numberViewer.setText(f"generated number: {num}")
        # save the generated number
        is_save_success = save(num, self.dbName)
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
