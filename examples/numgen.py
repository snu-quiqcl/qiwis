#!/usr/bin/env python3

"""
App module for generating and showing a random number.
"""

import os
from typing import Any, Optional, Tuple

from PyQt5.QtCore import QObject, pyqtSlot
from PyQt5.QtWidgets import QWidget, QComboBox, QPushButton, QLabel, QVBoxLayout

from swift import BaseApp
from examples.backend import generate, write

class GeneratorFrame(QWidget):
    """Frame for requesting generating a random number.
    
    Attributes:
        dbBox: A combobox for selecting a database 
          into which the generated number is saved.
        generateButton: A button for generating a new number.
    """
    def __init__(self, parent: Optional[QObject] = None):
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
    def __init__(self, parent: Optional[QObject] = None):
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
    def __init__(self, name: str, table: str = "number", parent: Optional[QObject] = None):
        """Extended.

        Args:
            table: A name of table to store the generated number.
        """
        super().__init__(name, parent=parent)
        self.table = table
        self.dbs = {"": ""}
        self.dbName = ""
        self.isGenerated = False
        self.generatorFrame = GeneratorFrame()
        self.generatorFrame.dbBox.addItem("")
        self.viewerFrame = ViewerFrame()
        # connect signals to slots
        self.generatorFrame.dbBox.currentIndexChanged.connect(self.setDB)
        self.generatorFrame.generateButton.clicked.connect(self.generateNumber)

    def frames(self) -> Tuple[GeneratorFrame, ViewerFrame]:
        """Overridden."""
        return (self.generatorFrame, self.viewerFrame) if self.isGenerated else (self.generatorFrame,)

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
                self.generatorFrame.dbBox.addItem(name)
        removingDBs = originalDBs - newDBs
        if self.generatorFrame.dbBox.currentText() in removingDBs:
            self.generatorFrame.dbBox.setCurrentText("")
        for name in removingDBs:
            self.dbs.pop(name)
            self.generatorFrame.dbBox.removeItem(self.generatorFrame.dbBox.findText(name))

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

    @pyqtSlot()
    def setDB(self):
        """Sets the database to store the number."""
        self.dbName = self.generatorFrame.dbBox.currentText()
        self.viewerFrame.statusLabel.setText("database updated")
        self.broadcast(
            "log", 
            f"Database to store is set as {self.dbName}." if self.dbName
            else "Database to store is not selected."
        )

    @pyqtSlot()
    def generateNumber(self):
        """Generates and shows a random number when the button is clicked."""
        # generate a random number
        num = generate()
        self.viewerFrame.numberLabel.setText(f"generated number: {num}")
        self.broadcast("log", f"Generated number: {num}.")
        # save the generated number
        dbPath = self.dbs[self.dbName]
        is_save_success = write(os.path.join(dbPath, self.dbName), self.table, num)
        if is_save_success:
            self.viewerFrame.statusLabel.setText("number saved successfully")
            self.broadcast("log", "Generated number saved.")
        else:
            self.viewerFrame.statusLabel.setText("failed to save number")
