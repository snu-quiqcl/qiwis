#!/usr/bin/env python3

"""
App module for generating and showing a random number.
"""

import os
import json

from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QWidget, QComboBox, QPushButton, QLabel, QVBoxLayout

from swift.app import BaseApp
from apps.backend import generate, write

class GeneratorFrame(QWidget):
    """Frame for requesting generating a random number.
    
    Attributes:
        dbBox: A combobox for selecting a database 
          into which the generated number is saved.
        generateButton: A button for generating a new number.
    """
    def __init__(self, parent=None):
        """Extended."""
        super().__init__(parent=parent)
        # widgets
        self.dbBox = QComboBox(self)
        self.generateButton = QPushButton("generate number", self)
        # layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.dbBox)
        layout.addWidget(self.generateButton)


class ViewerFrame(QWidget):
    """Frame for showing the generated number.

    Attributes:
        statusLabel: A label for showing the current status.
          (database updated, random number generated, etc.)
        numberLabel: A label for showing the recently generated number.
    """
    def __init__(self, parent=None):
        """Extended."""
        super().__init__(parent=parent)
        # widgets
        self.statusLabel = QLabel("initialized", self)
        self.numberLabel = QLabel("not generated", self)
        # layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.statusLabel)
        layout.addWidget(self.numberLabel)


class NumGenApp(BaseApp):
    """App for generating and showing a random number.

    Manage a generator frame and a viewer frame.
    Communicate with the backend.

    Attributes:
        table: A name of table to store the generated number.
        dbs: A dictionary for storing available databases.
          Each element represents a database.
          A key is a file name and its value is an absolute path.
        dbName: A name of the selected database.
        generatorFrame: A frame that requests generating a random number.
        viewerFrame: A frame that shows the generated number.
    """
    def __init__(self, name: str, parent=None, table: str = "number"):
        """Extended.

        Args:
            table: A name of table to store the generated number.
        """
        super().__init__(name, parent)
        self.table = table
        self.dbs = {"": ""}
        self.dbName = ""
        self.generatorFrame = GeneratorFrame()
        self.viewerFrame = ViewerFrame()
        # connect signals to slots
        self.received.connect(self.updateDB)
        self.generatorFrame.dbBox.currentIndexChanged.connect(self.setDB)
        self.generatorFrame.generateButton.clicked.connect(self.generateNumber)

    def frames(self):
        """Overridden."""
        return (self.generatorFrame, self.viewerFrame)

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
                print(f"apps.numgen.updateDB(): {e!r}")
            else:
                orgDbName = self.dbName
                self.dbs = {"": ""}
                self.generatorFrame.dbBox.clear()
                self.generatorFrame.dbBox.addItem("")
                for db in msg.get("db", ()):
                    if all(key in db for key in ("name", "path")):
                        name, path = db["name"], db["path"]
                        self.dbs[name] = path
                        self.generatorFrame.dbBox.addItem(name)
                    else:
                        print(f"The message was ignored because "
                              f"the database {db} has no such key; name or path.")
                if orgDbName in self.dbs:
                    self.generatorFrame.dbBox.setCurrentText(orgDbName)
        else:
            print(f"The message was ignored because "
                  f"the treatment for the bus {busName} is not implemented.")

    @pyqtSlot()
    def setDB(self):
        """Sets the database to store the number."""
        self.dbName = self.generatorFrame.dbBox.currentText()
        self.viewerFrame.statusLabel.setText("database updated")
        self.broadcastRequested.emit(
            "logbus", 
            f"Database to store is set as {self.dbName}." if self.dbName
            else "Database to store is not selected."
        )

    @pyqtSlot()
    def generateNumber(self):
        """Generates and shows a random number when the button is clicked."""
        # generate a random number
        num = generate()
        self.viewerFrame.numberLabel.setText(f"generated number: {num}")
        self.broadcastRequested.emit("logbus", f"Generate a random number: {num}.")
        # save the generated number
        dbPath = self.dbs[self.dbName]
        is_save_success = write(os.path.join(dbPath, self.dbName), self.table, num)
        if is_save_success:
            self.viewerFrame.statusLabel.setText("number saved successfully")
            self.broadcastRequested.emit("logbus", f"Save the generated number: {num}.")
        else:
            self.viewerFrame.statusLabel.setText("failed to save number")
