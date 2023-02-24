#!/usr/bin/env python3

"""
App module for generating and showing a random number.
"""

import sys

from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtWidgets import (QApplication, QMainWindow, QDockWidget, QWidget,
                             QVBoxLayout, QComboBox, QPushButton, QLabel)

from swift.app import BaseApp
from .backend import generate, save

class GeneratorFrame(QWidget):
    """Frame for requesting generating a random number.
    
    Attributes:
        databaseSelector: A combobox for selecting a database 
          into which the generated number is saved
        generateButton: A button for generating new number Viewer frame
    """
    def __init__(self):
        super().__init__()
        self.db_list = ["None"]  # this will be developed later
        self.init_widget()

    def init_widget(self):
        """Initializes widgets in the frame."""
        # database selector
        self.databaseSelector = QComboBox(self)
        for db_name in self.db_list:
            self.databaseSelector.addItem(db_name)
        # generator button
        self.generatorButton = QPushButton("generate number", self)
        # set layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.databaseSelector)
        layout.addWidget(self.generatorButton)


class ViewerFrame(QWidget):
    """Frame for showing the generated number.

    Attributes:
        statusLabel: A label for showing the current status 
          (database updated, random number generated, etc.)
        numberViewer: A label for showing the recently generated number
    """
    def __init__(self):
        super().__init__()
        self.init_widget()

    def init_widget(self):
        """Initializes widgets in the frame."""
        # status label
        self.statusLabel = QLabel("initialized", self)
        # number viewer
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
        self.generatorFrame = GeneratorFrame()
        self.viewerFrame = ViewerFrame()
        # connect signals to slots
        self.generatorFrame.generatorButton.clicked.connect(self.generateNumber)

    def frames(self):
        """Gets frames for which are managed by the app.

        Returns:
            tuple: A tuple containing frames for showing.
        """
        return (self.generatorFrame, self.viewerFrame)
    
    @pyqtSlot()
    def generateNumber(self):
        """Generates and shows a random number when the button is clicked."""
        num = generate()
        self.viewerFrame.statusLabel.setText("random number generated")
        self.viewerFrame.numberViewer.setText(f"generated number: {num}")


def main():
    """Main function that runs when numgen.py is called."""
    app = QApplication(sys.argv)
    main_window = QMainWindow()
    # create a app
    app = NumGenApp("numgen")
    # get frames from the app and add them as dock widgets
    for frame in app.frames():
        dock_widget = QDockWidget("random number generator", main_window)
        dock_widget.setWidget(frame)
        main_window.addDockWidget(Qt.LeftDockWidgetArea, dock_widget)
    main_window.show()
    app.exec_()


if __name__ == "__main__":
    main()
