"""
App module for showing the sum of two values from selected databases.
"""

import os
import json

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
    def __init__(self, name: str, parent=None, tables: dict=None):
        """Extended.

        Args:
            tables: See DataCalcApp.tables.
        """
        super().__init__(name, parent)
        self.tables = tables
        self.dbs = {"": ""}
        self.dbNames = {"A": "", "B": ""}
        self.viewerFrame = ViewerFrame()
        # connect signals to slots
        self.received.connect(self.updateDB)
        for dbBox in self.viewerFrame.dbBoxes.values():
            dbBox.currentIndexChanged.connect(self.setDB)
        self.viewerFrame.calculateButton.clicked.connect(self.calculateSum)

    def frames(self):
        """Overridden."""
        return (self.viewerFrame,)

    @pyqtSlot(str, str)
    def updateDB(self, busName: str, msg: str):
        """Updates the database list using the transferred message.

        This is a slot for received signal.

        Args:
            busName: A name of the bus that transfered the signal.
            msg: An input message to be transferred through the bus.
              The structure follows the message protocol of DBMgrApp.
        """
        if busName == "dbbus":
            try:
                msg = json.loads(msg)
            except json.JSONDecodeError as e:
                print(f"apps.datacalc.updateDB(): {e!r}")
            else:
                orgDbNames = self.dbNames.copy()
                self.dbs = {"": ""}
                for dbBox in self.viewerFrame.dbBoxes.values():
                    dbBox.clear()
                    dbBox.addItem("")
                for db in msg.get("db", ()):
                    if all(key in db for key in ("name", "path")):
                        name, path = db["name"], db["path"]
                        self.dbs[name] = path
                        for dbBox in self.viewerFrame.dbBoxes.values():
                            dbBox.addItem(name)
                    else:
                        print(f"The message was ignored because "
                              f"the database {db} has no such key; name or path.")
                for name, orgDbName in orgDbNames.items():
                    if orgDbName in self.dbs:
                        self.viewerFrame.dbBoxes[name].setCurrentText(orgDbName)
        else:
            print(f"The message was ignored because "
                  f"the treatment for the bus {busName} is not implemented.")

    @pyqtSlot()
    def setDB(self):
        """Sets the databases to fetch the numbers."""
        for name, dbBox in self.viewerFrame.dbBoxes.items():
            self.dbNames[name] = dbBox.currentText()
            self.broadcastRequested.emit(
                "logbus", 
                f"Database {name} is set as {self.dbNames[name]}." if self.dbNames[name]
                else f"Database {name} is not selected."
            )

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
            self.broadcastRequested.emit("logbus", f"Calculate the sum: {result}.")
