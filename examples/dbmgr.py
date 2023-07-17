"""
App module for adding and removing available databases.
"""

import os
import logging
from collections import namedtuple
from typing import Optional, Tuple

from PyQt5.QtCore import QObject, pyqtSlot
from PyQt5.QtWidgets import (QWidget, QLabel, QPushButton, QFileDialog,
                             QHBoxLayout, QVBoxLayout, QListWidget, QListWidgetItem)

from qiwis import AppInfo, BaseApp

logger = logging.getLogger(__name__)


class DBWidget(QWidget):
    """Widget for showing a database.

    Attributes:
        name: A file name of the database.
        path: An absolute path of the database.
        nameLabel: A label for showing the file name.
        pathLabel: A label for showing the absolue path.
        removeButton: A button for removing (disconnecting) the database.
    """
    def __init__(self, name: str, path: str, parent: Optional[QObject] = None):
        """"Extended.

        Args:
            path: An absolute path of the database.
        """
        super().__init__(parent=parent)
        self.name = name
        self.path = path
        self._initWidget()

    def _initWidget(self):
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
        openCloseDatacalcButton: A button for opening or closing a datacalc app.
    """
    def __init__(self, parent: Optional[QObject] = None):
        """Extended."""
        super().__init__(parent=parent)
        # widgets
        self.dbListWidget = QListWidget(self)
        self.addButton = QPushButton("add", self)
        self.openCloseDatacalcButton = QPushButton("open or close datacalc", self)
        # layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.dbListWidget)
        layout.addWidget(self.addButton)
        layout.addWidget(self.openCloseDatacalcButton)


class DBMgrApp(BaseApp):
    """App for adding and removing available databases.

    Manage a manager frame.
    Send an updated database information to database channel.

    Protocol:
        A broadcastRequested signal is emitted 
          when the available databases are changed (added or removed).
        It is a json object converted to string using json.dumps().
        On the receiving end, it can be interpreted using json.loads().

        The json object has one key; db. In db, there is a list of databases.  
        Each database has two keys; name and path.
          name: A file name of the database.
          path: An absolute path of the database.

    Attributes:
        dbList: A list for storing available databases.
          Each element is a namedtuple which represents a database.
          It has two elements; file name and absolute path.
        isDatacalcOpen: True if a datacalc app is open, and False if it is close.
        openCloseDatacalcResult: The latest qiwiscall result 
          which requests for opening or closing a datacalc app.
        managerFrame: A frame that manages and shows available databases.
    """
    DB = namedtuple("DB", ["path", "name"])

    def __init__(self, name: str, parent: Optional[QObject] = None):
        """Extended."""
        super().__init__(name, parent=parent)
        self.dbList = []
        self.isDatacalcOpen = False
        self.openCloseDatacalcResult = None
        self.managerFrame = ManagerFrame()
        # connect signals to slots
        self.managerFrame.addButton.clicked.connect(self.addDB)
        self.managerFrame.openCloseDatacalcButton.clicked.connect(self.openCloseDatacalc)

    def frames(self) -> Tuple[ManagerFrame]:
        """Overridden."""
        return (self.managerFrame,)

    def sendDB(self, isAdded: bool, name: str):
        """Emits a broadcastRequested signal with the database list and a logging message.
        
        Args:
            isAdded: True if a database is added, and False if a databse is removed.
            name: A file name of the updated database.
        """
        msg = {"db": [db._asdict() for db in self.dbList]}
        self.broadcast("db", msg)
        logger.info(
            f"Database {name} is added." if isAdded
            else f"Database {name} is removed."
        )

    @pyqtSlot()
    def addDB(self):
        """Selects a database and adds to dbList.
        
        Show the database at dbListWidget in ManagerFrame.
        Emit a broadcastRequested signal containing an added database information.
        """
        dbPath, _ = QFileDialog.getOpenFileName(
            self.managerFrame,
            "Select a database file",
            "./"
        )
        if not dbPath:
            return
        db = DBMgrApp.DB._make(os.path.split(dbPath))
        self.dbList.append(db)
        # create a database widget
        widget = DBWidget(db.name, db.path, self.managerFrame.dbListWidget)
        widget.removeButton.clicked.connect(self.removeDB)
        item = QListWidgetItem(self.managerFrame.dbListWidget)
        item.setSizeHint(widget.sizeHint())
        self.managerFrame.dbListWidget.addItem(item)
        self.managerFrame.dbListWidget.setItemWidget(item, widget)
        # send the database list and a logging message
        self.sendDB(True, db.name)

    @pyqtSlot()
    def removeDB(self):
        """Selects a database and removes from dbList.
        
        Show the database at dbListWidget in ManagerFrame.
        Emit a broadcastRequested signal containing an added database information.
        """
        # find the selected database
        widget = self.sender().parent()
        db = DBMgrApp.DB(name=widget.name, path=widget.path)
        row = self.dbList.index(db)
        # remove the database widget
        item = self.managerFrame.dbListWidget.takeItem(row)
        del self.dbList[row]
        del item
        widget.deleteLater()
        # send the database list and a logging message
        self.sendDB(False, db.name)

    @pyqtSlot()
    def openCloseDatacalc(self):
        """Opens or closes a datacalc app.

        If the dataclac app is open, close it.
        Otherwise, open a new datacalc app.
        """
        if self.openCloseDatacalcResult is not None:
            if not self.openCloseDatacalcResult.done:
                print("DBMgrApp.openCloseDatacalc(): The previous qiwiscall must be done.")
                return
            if self.openCloseDatacalcResult.success:
                self.isDatacalcOpen = not self.isDatacalcOpen
        if self.isDatacalcOpen:
            self.openCloseDatacalcResult = self.qiwiscall.destroyApp(name="datacalc")
        else:
            self.openCloseDatacalcResult = self.qiwiscall.createApp(
                name="datacalc",
                info=AppInfo(
                    module="examples.datacalc",
                    cls="DataCalcApp",
                    show=True,
                    pos="top",
                    channel=["db"],
                    args={
                        "tables": {
                            "A": "number",
                            "B": "B"
                        }
                    }
                )
            )
