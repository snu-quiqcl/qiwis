import sys
import random

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QDockWidget,\
                            QWidget, QVBoxLayout, QPushButton, QLabel

from swift.logic import BaseLogic

class NumGenFrame(QWidget):
    def __init__(self):
        super().__init__()
        self.init_widget()

    def init_widget(self):
        self.btn = QPushButton("generate number", self)
        self.btn.clicked.connect(self.generate_number)
        self.label = QLabel("not generated", self)

        layout = QVBoxLayout(self)
        layout.addWidget(self.btn)
        layout.addWidget(self.label)

    def generate_number(self):
        num = random.randrange(0, 10)

        self.label.clear()
        self.label.setText(f"generated number: {num}")


class NumGenLogic(BaseLogic):
    def __init__(self, name: str):
        super().__init__(name)
        self.frame = NumGenFrame()

    def frames(self):
        return (self.frame,)


def main():
    app = QApplication(sys.argv)
    main_window = QMainWindow()

    # create a logic
    logic = NumGenLogic("numgen")

    # get frames from the logic and add them as dock widgets
    for frame in logic.frames():
        dock_widget = QDockWidget("random number generator", main_window)
        dock_widget.setWidget(frame)

        main_window.addDockWidget(Qt.LeftDockWidgetArea, dock_widget)

    main_window.showMaximized()
    app.exec_()


if __name__ == "__main__":
    main()
