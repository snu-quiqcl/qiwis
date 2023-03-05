"""
App module for showing the sum of two values from selected databases.
"""

from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QComboBox, QPushButton, QLabel

from swift.app import BaseApp
from apps.backend import read

class ViewerFrame(QWidget):
    def __init__(self, parent=None):
        """
        Args:
            parent: A parent widget.
        """
        super().__init__(parent=parent)


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
