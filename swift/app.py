"""
Base module for App.

Every App class should be a subclass of BaseApp.
"""

from typing import Optional, Iterable

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QWidget

class BaseApp(QObject):
    """Base App class that all apps should inherit.

    Signals: 
        broadcastRequested(str, str): A signal for broadcasting to a channel 
          which contains the target channel name and the message.
        received(str, str): A signal for receiving a global signal from a channel
          which contains the source channel name and the message.
    """

    broadcastRequested = pyqtSignal(str, str)
    received = pyqtSignal(str, str)

    def __init__(self, name: str, parent: Optional[QObject] = None):
        """
        Args:
            name: A string that indicates the name of App.
            parent: A parent object.
        """
        super().__init__(parent=parent)
        self.name = name

    def frames(self) -> Iterable[QWidget]:
        """Gets frames for which are managed by the App.

        Returns:
            An iterable object of Frame objects for showing.
        """
        return ()
