"""
App module for polling a number and saving it into the selected database.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QComboBox, QSpinBox, QLabel

from swift.app import BaseApp

class ViewerFrame(QWidget):
    """Frame of for polling a number and saving it into the selected database.
    
    Attributes:
        dbBox: A combobox for selecting a database into which the polled number is saved.
        periodBox: A spinbox for adjusting the polling period.
        countLabel: A label for showing the polled count. (how many numbers have been polled)
          This will confidently show when the polling occurs
        numberLabel: A label for showing the recently polled number
    """
    def __init__(self, parent=None):
        """
        Args:
            parent: A parent widget.
        """
        super().__init__(parent=parent)
        # widgets
        self.dbBox = QComboBox(self)
        self.periodBox = QSpinBox(self)
        self.periodBox.setMinimum(1)
        self.periodBox.setMaximum(10)
        self.countLabel = QLabel("not initiated", self)
        self.numberLabel = QLabel("not initiated", self)
        # layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.dbBox)
        layout.addWidget(self.periodBox)
        layout.addWidget(self.countLabel)
        layout.addWidget(self.numberLabel)


class PollerApp(BaseApp):
    def __init__(self, name: str, table: str):
        super().__init__(name)
        self.table = table
        self.viewerFrame = ViewerFrame()

    def frames(self):
        """Gets frames for which are managed by the app.

        Returns:
            A tuple containing frames for showing.
        """
        return (self.viewerFrame,)
