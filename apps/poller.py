"""
App module for polling a number and saving it into the selected database.
"""

import os
import json

from PyQt5.QtCore import pyqtSlot, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QComboBox, QSpinBox, QLabel

from swift.app import BaseApp
from apps.backend import poll, write

class ViewerFrame(QWidget):
    """Frame for selecting a database and period, and showing the polled number.
    
    Attributes:
        dbBox: A combobox for selecting a database into which the polled number is saved.
        periodBox: A spinbox for adjusting the polling period.
        countLabel: A label for showing the polled count (how many numbers have been polled).
          This will confidently show when the polling occurs.
        numberLabel: A label for showing the recently polled number.
    """
    def __init__(self, parent=None):
        """Extended."""
        super().__init__(parent=parent)
        # widgets
        self.dbBox = QComboBox(self)
        self.periodBox = QSpinBox(self)
        self.periodBox.setMinimum(1)
        self.periodBox.setMaximum(10)
        self.countLabel = QLabel("not initiated", self)
        self.numberLabel = QLabel("not initiated", self)
        # layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.dbBox)
        layout.addWidget(self.periodBox)
        layout.addWidget(self.countLabel)
        layout.addWidget(self.numberLabel)


class PollerApp(BaseApp):
    """App for polling a number and saving it into the selected database.

    Manage a viewer frame.
    Communicate with the backend.

    Attributes:
        table: A name of table to store the polled number.
        dbs: A dictionary for storing available databases.
          Each element represents a database.
          A key is a file name and its value is an absolute path.
        dbName: A name of the selected database.
        viewerFrame: A frame that selects a database and period, and shows the polled number.
        count: The polled count. It starts from 0.
        timer: A QTimer object for polling. The initial interval is a second.
    """
    def __init__(self, name: str, parent=None, table: str = "B"):
        """Extended.

        Args:
            table: See PollerApp.table.
        """
        super().__init__(name, parent)
        self.table = table
        self.dbs = {"": ""}
        self.dbName = ""
        self.viewerFrame = ViewerFrame()
        # connect signals to slots
        self.received.connect(self.updateDB)
        self.viewerFrame.dbBox.currentIndexChanged.connect(self.setDB)
        self.viewerFrame.periodBox.valueChanged.connect(self.setPeriod)
        # start timer
        self.count = 0
        self.timer = QTimer(self)
        self.timer.start(1000 * self.viewerFrame.periodBox.value())
        self.timer.timeout.connect(self.poll)

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
                print(f"apps.numgen.updateDB(): {e!r}")
            else:
                orgDbName = self.dbName
                self.dbs = {"": ""}
                self.viewerFrame.dbBox.clear()
                self.viewerFrame.dbBox.addItem("")
                for db in msg.get("db", ()):
                    if all(key in db for key in ("name", "path")):
                        name, path = db["name"], db["path"]
                        self.dbs[name] = path
                        self.viewerFrame.dbBox.addItem(name)
                    else:
                        print(f"The message was ignored because "
                              f"the database {db} has no such key; name or path.")
                if orgDbName in self.dbs:
                    self.viewerFrame.dbBox.setCurrentText(orgDbName)
        else:
            print(f"The message was ignored because "
                  f"the treatment for the bus {busName} is not implemented.")

    @pyqtSlot()
    def setPeriod(self):
        """Sets the polling period."""
        period = self.viewerFrame.periodBox.value()
        self.timer.start(1000 * period)
        self.broadcastRequested.emit("logbus", f"Period is set as {period}s.")

    @pyqtSlot()
    def setDB(self):
        """Sets the database to store the polled number."""
        self.dbName = self.viewerFrame.dbBox.currentText()
        self.broadcastRequested.emit(
            "logbus", 
            f"Polled database is set as {self.dbName}." if self.dbName
            else "Polled database is not selected."
        )

    @pyqtSlot()
    def poll(self):
        """Polls and store a number with the selected period."""
        num = poll()
        self.count += 1
        self.viewerFrame.countLabel.setText(f"polled count: {self.count}")
        self.viewerFrame.numberLabel.setText(f"polled number: {num}")
        self.broadcastRequested.emit("logbus", f"Poll a number: {num}.")
        # save the polled number
        dbPath = self.dbs[self.dbName]
        if write(os.path.join(dbPath, self.dbName), self.table, num):
            self.broadcastRequested.emit("logbus", f"Save the polled number: {num}.")
