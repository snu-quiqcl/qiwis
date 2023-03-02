from swift.app import BaseApp

from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QHBoxLayout

class DBItem(QWidget):
    def __init__(self, name, path):
        super().__init__()
        self.name = name
        self.path = path
        self.init_widget()

    def init_widget(self):
        self.nameLabel = QLabel(self.name, self)
        self.pathLabel = QLabel(self.path, self)
        self.removeButton = QPushButton("remove", self)
        # set layout
        layout = QHBoxLayout(self)
        layout.addWidget(self.nameLabel)
        layout.addWidget(self.pathLabel)
        layout.addWidget(self.removeButton)

class ManagerFrame(QWidget):
    def __init__(self):
        super().__init__()
        self.dbList = []
        self.init_widget()

    def init_widget(self):
        pass

class DBMgrApp(BaseApp):
    def __init__(self, name: str):
        super().__init__(name)
        