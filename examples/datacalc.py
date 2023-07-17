"""
App module for showing the sum of two values from selected databases.
"""

import os
import logging
import functools
from typing import Any, Optional, Dict, Tuple

from PyQt5.QtCore import QObject, pyqtSlot
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QComboBox, QPushButton, QLabel

from qiwis import BaseApp
from examples.backend import read

logger = logging.getLogger(__name__)


class ViewerFrame(QWidget):
    """Frame of for selecting databases and showing the calculated number.
    
    Attributes:
        dbBoxes: A dictionary containing two comboboxes for selecting the database 
          from which the value of A and B is fetched.
        calculateButton: A button for calculating the sum of recently fetched 'A' and 'B'.
        numberLabel: A label showing the sum, or an error message if something goes wrong.
    """
    def __init__(self, parent: Optional[QObject] = None):
        """Extended."""
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
    """App for showing the sum of two values from selected databases.

    Manage a viewer frame.
    Communicate with the backend.

    Attributes:
        tables: A dictionary containing table names of databases for using calculation.
          It has two elements which represent tables.
          A key is "A" or "B" and its value is a table name of each database.
          It is offered as the constructor argument.
        dbs: A dictionary for storing available databases.
          Each element represents a database.
          A key is a file name and its value is an absolute path.
        dbNames: A dictionary for storing names of the selected databases.
        viewerFrame: A frame that selects databases and shows the calculated number.
    """
    def __init__(self, name: str, tables: Dict[str, str], parent: Optional[QObject] = None):
        """Extended.

        Args:
            tables: See DataCalcApp.tables.
        """
        super().__init__(name, parent=parent)
        self.tables = tables
        self.dbs = {"": ""}
        self.dbNames = {"A": "", "B": ""}
        self.viewerFrame = ViewerFrame()
        for dbBox in self.viewerFrame.dbBoxes.values():
            dbBox.addItem("")
        # connect signals to slots
        for dbName, dbBox in self.viewerFrame.dbBoxes.items():
            dbBox.currentIndexChanged.connect(functools.partial(self.setDB, dbName))
        self.viewerFrame.calculateButton.clicked.connect(self.calculateSum)

    def frames(self) -> Tuple[ViewerFrame]:
        """Overridden."""
        return (self.viewerFrame,)

    def updateDB(self, content: dict):
        """Updates the database list using the transferred message.

        It assumes that:
            The new database is always added at the end.
            Changing the order of the databases is not allowed.

        Args:
            content: Received content.
              The structure follows the message protocol of DBMgrApp.
        """
        originalDBs = set(self.dbs)
        newDBs = set([""])
        for db in content.get("db", ()):
            if any(key not in db for key in ("name", "path")):
                print(f"The message was ignored because "
                        f"the database {db} has no such key; name or path.")
                continue
            name, path = db["name"], db["path"]
            newDBs.add(name)
            if name not in self.dbs:
                self.dbs[name] = path
                for dbBox in self.viewerFrame.dbBoxes.values():
                    dbBox.addItem(name)
        removingDBs = originalDBs - newDBs
        for dbBox in self.viewerFrame.dbBoxes.values():
            if dbBox.currentText() in removingDBs:
                dbBox.setCurrentText("")
        for name in removingDBs:
            self.dbs.pop(name)
            for dbBox in self.viewerFrame.dbBoxes.values():
                dbBox.removeItem(dbBox.findText(name))

    def receivedSlot(self, channelName: str, content: Any):
        """Overridden.

        Possible channels are as follows.

        "db": Database channel.
            See self.updateDB().
        """
        if channelName == "db":
            if isinstance(content, dict):
                self.updateDB(content)
            else:
                print("The message for the channel db should be a dictionary.")
        else:
            print(f"The message was ignored because "
                  f"the treatment for the channel {channelName} is not implemented.")

    @pyqtSlot(str)
    def setDB(self, name: str):
        """Sets the database to fetch the numbers.
        
        Args:
            name: A name of the selected combobox.
        """
        dbBox = self.viewerFrame.dbBoxes[name]
        self.dbNames[name] = dbBox.currentText()
        if self.dbNames[name]:
            logger.info("Database %s is set as %s.", name, self.dbNames[name])
        else: logger.info("Database %s is not selected.", name)

    @pyqtSlot()
    def calculateSum(self):
        """Calculates and shows the sum of two values when the button is clicked."""
        result = 0
        for name, dbName in self.dbNames.items():
            dbPath = self.dbs[dbName]
            table = self.tables[name]
            value = read(os.path.join(dbPath, dbName), table)
            if value is None:
                self.viewerFrame.numberLabel.setText(f"failed to fetch number from {name}")
                break
            if not isinstance(value, int):
                self.viewerFrame.numberLabel.setText(f"The type of value from {name} "
                                                     f"should be an integer")
                break
            result += value
        else:
            self.viewerFrame.numberLabel.setText(f"sum: {result}")
            logger.log("Sum: %f.", result)
