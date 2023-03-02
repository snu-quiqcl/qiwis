"""
App module for adding and removing available databases.
"""

from PyQt5.QtWidgets import (QWidget, QLabel, QPushButton, QHBoxLayout,
                             QVBoxLayout, QListWidget, QListWidgetItem)

from swift.app import BaseApp

class DBItem(QWidget):
    """Item widget for showing a database.

    Attributes:
        nameLabel: A label for showing the file name.
        pathLabel: A label for showing the absolue path.
        removeButton: A button for removing (disconnecting) the database.
    """
    def __init__(self, name, path):
        """
        Args:
            name: A file name of the database.
            path: An absolute path of the database.
        """
        super().__init__()
        self.name = name
        self.path = path
        self.init_widget()

    def init_widget(self):
        """Initializes widgets in the item."""
        self.nameLabel = QLabel(self.name, self)
        self.pathLabel = QLabel(self.path, self)
        self.removeButton = QPushButton("remove", self)
        # set layout
        layout = QHBoxLayout(self)
        layout.addWidget(self.nameLabel)
        layout.addWidget(self.pathLabel)
        layout.addWidget(self.removeButton)

class ManagerFrame(QWidget):
    """Frame for managing available databases.

    Attributes:
        dbList: A list for storing available databases.
          Each element of which type is tuple represents a database.
          It has two elements; file name and absolute path.
        dbListWidget: A list widget for showing available databases.
          Each database can be removed (actually disconnected) 
          when removeButton (of each item) clicked.
        addButton: A button for adding (actually connecting) a database.
    """
    def __init__(self):
        super().__init__()
        self.dbList = [("name", "path")]
        self.init_widget()

    def init_widget(self):
        """Initializes widgets in the frame."""
        self.dbListWidget = QListWidget(self)
        for name, path in self.dbList:
            item = DBItem(name, path)
            listWidgetItem = QListWidgetItem(self.dbListWidget)
            listWidgetItem.setSizeHint(item.sizeHint())
            self.dbListWidget.addItem(listWidgetItem)
            self.dbListWidget.setItemWidget(listWidgetItem, item)
        self.addButton = QPushButton("add", self)
        # set layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.dbListWidget)
        layout.addWidget(self.addButton)

class DBMgrApp(BaseApp):
    """App for adding and removing available databases.

    Manage a manager frame.
    Send an updated database information to database bus.

    Attributes:
        managerFrame: A frame that manages and shows available databases.
    """
    def __init__(self, name: str):
        super().__init__(name)
        self.managerFrame = ManagerFrame()

    def frames(self):
        """Gets frames for which are managed by the app.

        Returns:
            A tuple containing frames for showing.
        """
        return (self.managerFrame,)
