"""
App module for showing the sum of two values from selected databases.
"""

import os
import json
from typing import Optional, Dict, Tuple

from PyQt5.QtCore import QObject, pyqtSlot
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QComboBox, QPushButton, QLabel

from swift.app import BaseApp
from examples.backend import read

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
        self.received.connect(self.updateDB)
        self.viewerFrame.dbBoxes["A"].currentIndexChanged.connect(lambda: self.setDB("A"))
        self.viewerFrame.dbBoxes["B"].currentIndexChanged.connect(lambda: self.setDB("B"))
        self.viewerFrame.calculateButton.clicked.connect(self.calculateSum)

    def frames(self) -> Tuple[ViewerFrame]:
        """Overridden."""
        return (self.viewerFrame,)

    @pyqtSlot(str, str)
    def updateDB(self, channelName: str, msg: str):
        """Updates the database list using the transferred message.

        This is a slot for received signal.

        Args:
            channelName: A name of the channel that transfered the signal.
            msg: An input message to be transferred through the channel.
              The structure follows the message protocol of DBMgrApp.
        """
        if channelName == "db":
            try:
                msg = json.loads(msg)
            except json.JSONDecodeError as e:
                print(f"apps.datacalc.updateDB(): {e!r}")
            else:
                originalDBs = set(self.dbs)
                newDBs = set([""])
                for db in msg.get("db", ()):
                    if all(key in db for key in ("name", "path")):
                        name, path = db["name"], db["path"]
                        newDBs.add(name)
                        if name not in self.dbs:
                            self.dbs[name] = path
                            for dbBox in self.viewerFrame.dbBoxes.values():
                                dbBox.addItem(name)
                    else:
                        print(f"The message was ignored because "
                              f"the database {db} has no such key; name or path.")
                removingDBs = originalDBs - newDBs
                for dbBox in self.viewerFrame.dbBoxes.values():
                    if dbBox.currentText() in removingDBs:
                        dbBox.setCurrentText("")
                for name in removingDBs:
                    self.dbs.pop(name)
                    for dbBox in self.viewerFrame.dbBoxes.values():
                        dbBox.removeItem(dbBox.findText(name))
        else:
            print(f"The message was ignored because "
                  f"the treatment for the channel {channelName} is not implemented.")

    @pyqtSlot(str)
    def setDB(self, name: str):
        """Sets the database to fetch the numbers."""
        dbBox = self.viewerFrame.dbBoxes[name]
        self.dbNames[name] = dbBox.currentText()
        self.broadcastRequested.emit(
            "log", 
            f"Database {name} is set as {self.dbNames[name]}."
            if self.dbNames[name]
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
            self.broadcastRequested.emit("log", f"Sum: {result}.")
