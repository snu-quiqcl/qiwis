"""
App module for showing the sum of two values from selected databases.
"""

from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QComboBox, QPushButton, QLabel

from swift.app import BaseApp
from apps.backend import read

class ViewerFrame(QWidget):
    """Frame of for selecting databases and showing the calculated number.
    
    Attributes:
        dbBoxes: A dictionary containing two comboboxes for selecting the database 
          from which the value of A and B is fetched.
        calculateButton: A button for calculating the sum of recently fetched 'A' and 'B'.
        numberLabel: A label showing the sum, or an error message if something goes wrong.
    """
    def __init__(self, parent=None):
        """
        Args:
            parent: A parent widget.
        """
        super().__init__(parent=parent)
        # widgets
        self.dbBoxes = {
            "A": QComboBox(self),
            "B": QComboBox(self),
        }
        self.calculateButton = QPushButton("sum", self)
        self.numberLabel = QLabel("not calculated", self)
        # layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.dbBoxes["A"])
        layout.addWidget(self.dbBoxes["B"])
        layout.addWidget(self.calculateButton)
        layout.addWidget(self.numberLabel)


class DataCalcApp(BaseApp):
    def __init__(self, name: str):
        super().__init__(name)
        self.viewerFrame = ViewerFrame()

    def frames(self):
        """Gets frames for which are managed by the app.

        Returns:
            A tuple containing frames for showing.
        """
        return (self.viewerFrame,)
