"""
App module for adding and removing available databases.
"""

import os
import json

from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import (QWidget, QLabel, QPushButton, QFileDialog,
                             QHBoxLayout, QVBoxLayout, QListWidget, QListWidgetItem)

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
        dbListWidget: A list widget for showing available databases.
          Each database can be removed (actually disconnected) 
          when removeButton (of each item) clicked.
        addButton: A button for adding (actually connecting) a database.
    """
    def __init__(self):
        super().__init__()
        self.init_widget()

    def init_widget(self):
        """Initializes widgets in the frame."""
        self.dbListWidget = QListWidget(self)
        self.addButton = QPushButton("add", self)
        # set layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.dbListWidget)
        layout.addWidget(self.addButton)

    def add_db(self, name, path):
        """Adds a database to dbListWidget.
        
        Args:
            name: A file name of the database.
            path: An absolute path of the database.
        """
        item = DBItem(name, path)
        listWidgetItem = QListWidgetItem(self.dbListWidget)
        listWidgetItem.setSizeHint(item.sizeHint())
        self.dbListWidget.addItem(listWidgetItem)
        self.dbListWidget.setItemWidget(listWidgetItem, item)


class DBMgrApp(BaseApp):
    """App for adding and removing available databases.

    Manage a manager frame.
    Send an updated database information to database bus.

    Protocol:
        A broadcastRequested signal is a json object converted to string using json.dumps().
        On the receiving end, it can be interpreted using json.loads().

        The json object has one key; db. In db, there is a list of databases.  
        Each database has two keys; name and path.
          name: A file name of the database.
          path: An absolute path of the database.

    Attributes:
        dbList: A list for storing available databases.
          Each element of which type is tuple represents a database.
          It has two elements; file name and absolute path.
        managerFrame: A frame that manages and shows available databases.
    """
    def __init__(self, name: str):
        super().__init__(name)
        self.db_list = []
        self.managerFrame = ManagerFrame()
        # connect signals to slots
        self.managerFrame.addButton.clicked.connect(self.addDB)

    def frames(self):
        """Gets frames for which are managed by the app.

        Returns:
            A tuple containing frames for showing.
        """
        return (self.managerFrame,)

    @pyqtSlot()
    def addDB(self):
        """Selects a database and adds to dbList.
        
        Show the database at dbListWidget in ManagerFrame.
        Emit a broadcastRequested signal containing an added database information.
        """
        db_path, _ = QFileDialog.getOpenFileName(
            self.managerFrame,
            "Select a database file",
            "./"
        )
        name, path = reversed(os.path.split(db_path))
        self.db_list.append((name, path))
        self.managerFrame.add_db(name, path)
        # emit a broadcastRequested signal
        msg = {"db": [{"name": db[0], "path": db[1]} for db in self.db_list]}
        self.broadcastRequested.emit("dbbus", json.dumps(msg))
