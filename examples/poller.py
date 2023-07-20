"""
App module for polling a number and saving it into the selected database.
"""

import os
import json
import logging
from typing import Any, Optional, Tuple

from PyQt5.QtCore import QObject, pyqtSlot, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QComboBox, QSpinBox, QLabel

from qiwis import BaseApp
from examples.backend import poll, write

logger = logging.getLogger(__name__)


class ViewerFrame(QWidget):
    """Frame for selecting a database and period, and showing the polled number.
    
    Attributes:
        dbBox: A combobox for selecting a database into which the polled number is saved.
        periodBox: A spinbox for adjusting the polling period.
        countLabel: A label for showing the polled count (how many numbers have been polled).
          This will confidently show when the polling occurs.
        numberLabel: A label for showing the recently polled number.
    """
    def __init__(self, parent: Optional[QObject] = None):
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
    def __init__(self, name: str, table: str = "B", parent: Optional[QObject] = None):
        """Extended.

        Args:
            table: See PollerApp.table.
        """
        super().__init__(name, parent=parent)
        self.table = table
        self.dbs = {"": ""}
        self.dbName = ""
        self.viewerFrame = ViewerFrame()
        self.viewerFrame.dbBox.addItem("")
        # connect signals to slots
        self.viewerFrame.dbBox.currentIndexChanged.connect(self.setDB)
        self.viewerFrame.periodBox.valueChanged.connect(self.setPeriod)
        # start timer
        self.count = 0
        self.timer = QTimer(self)
        self.timer.start(1000 * self.viewerFrame.periodBox.value())
        self.timer.timeout.connect(self.poll)

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
                logger.error("The message was ignored because "
                            "the database %s has no such key; name or path.", json.dumps(db))
                continue
            name, path = db["name"], db["path"]
            newDBs.add(name)
            if name not in self.dbs:
                self.dbs[name] = path
                self.viewerFrame.dbBox.addItem(name)
        removingDBs = originalDBs - newDBs
        if self.viewerFrame.dbBox.currentText() in removingDBs:
            self.viewerFrame.dbBox.setCurrentText("")
        for name in removingDBs:
            self.dbs.pop(name)
            self.viewerFrame.dbBox.removeItem(self.viewerFrame.dbBox.findText(name))

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
                logger.error("The message for the channel db should be a dictionary.")
        else:
            logger.error("The message was ignored because "
                        "the treatment for the channel %s is not implemented.", channelName)

    @pyqtSlot()
    def setPeriod(self):
        """Sets the polling period."""
        period = self.viewerFrame.periodBox.value()
        self.timer.start(1000 * period)
        logger.info("Period is set as %ds.", period)

    @pyqtSlot()
    def setDB(self):
        """Sets the database to store the polled number."""
        self.dbName = self.viewerFrame.dbBox.currentText()
        if self.dbName:
            logger.info("Database to store is set as %s.", self.dbName)
        else: logger.warning("Database to store is not selected.")

    @pyqtSlot()
    def poll(self):
        """Polls and store a number with the selected period."""
        num = poll()
        self.count += 1
        self.viewerFrame.countLabel.setText(f"polled count: {self.count}")
        self.viewerFrame.numberLabel.setText(f"polled number: {num}")
        logger.info("Polled number: %d.", num)
        # save the polled number
        dbPath = self.dbs[self.dbName]
        if write(os.path.join(dbPath, self.dbName), self.table, num):
            logger.info("Polled number saved.")
        else:
            logger.error("Failed to save polled number.")
