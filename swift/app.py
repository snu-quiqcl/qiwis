"""
Base module for App.

Every App class should be a subclass of BaseApp.
"""

import json
from typing import Any, Optional, Iterable

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

    def broadcast(self, channelName: str, content: Any):
        """Broadcasts the content to the target channel.

        Args:
            channelName: Target channel name.
            content: Content to be broadcast.
        
        """
        try:
            content = json.dumps(content)
        except TypeError as e:
            print(f"swift.app.broadcast(): {e!r}")
            return
        self.broadcastRequested.emit(channelName, content)


    def receivedSlot(self, channelName: str, content: Any):
        """This will be overridden by child classes."""

    @pyqtSignal(str, str)
    def _receivedMessage(self, channelName: str, msg: str):
        """This is connected to self.received signal."""
        try:
            msg = json.loads(msg)
        except json.JSONDecodeError as e:
            print(f"swift.app._receivedMessage(): {e!r}")
            return
        self._receivedSlot(channelName, msg)
