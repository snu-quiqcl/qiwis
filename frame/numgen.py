"""
Logic module for generating a random number.
"""

import sys
import random

from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtWidgets import (QApplication, QMainWindow, QDockWidget,
                             QWidget, QHBoxLayout, QPushButton, QLabel)

from swift.logic import BaseLogic

class _NumGenFrame(QWidget):
    """Frame class for reque

    Args:
        QWidget (_type_): _description_
    """
    def __init__(self):
        super().__init__()
        self.init_widget()

    def init_widget(self):
        """Initializes widgets in the frame.
        """
        self.btn = QPushButton("generate number", self)
        self.label = QLabel("not generated", self)

        layout = QHBoxLayout(self)
        layout.addWidget(self.btn)
        layout.addWidget(self.label)


class NumGenLogic(BaseLogic):
    """Logic class for managing a frame and generating a random number.

    Attributes:
        frame: A frame that request generating and show a random number.
    """
    def __init__(self, name: str):
        super().__init__(name)
        self.frame = _NumGenFrame()

        # connect the button clicked signal to the slot generating a number
        self.frame.btn.clicked.connect(self.generate_number)

    def frames(self):
        return (self.frame, )

    @pyqtSlot()
    def generate_number(self):
        """Generates and shows a random number when the button is clicked.
        """
        num = random.randrange(0, 10)

        self.frame.label.clear()
        self.frame.label.setText(f"generated number: {num}")


def main():
    """Main function that runs when numgen.py is called. 
    """
    app = QApplication(sys.argv)
    main_window = QMainWindow()

    # create a logic
    logic = NumGenLogic("numgen")

    # get frames from the logic and add them as dock widgets
    for frame in logic.frames():
        dock_widget = QDockWidget("random number generator", main_window)
        dock_widget.setWidget(frame)

        main_window.addDockWidget(Qt.LeftDockWidgetArea, dock_widget)

    main_window.show()
    app.exec_()


if __name__ == "__main__":
    main()
