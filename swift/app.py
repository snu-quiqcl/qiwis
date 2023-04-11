"""
Base module for App.

Every App class should be a subclass of BaseApp.
"""

import json
from typing import Any, Optional, Iterable

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QWidget

class BaseApp(QObject):
    """Base App class that all apps should inherit.

    Signals: 
        broadcastRequested(str, str): A signal for broadcasting to a channel 
          which contains the target channel name and the message.
        received(str, str): A signal for receiving a global signal from a channel
          which contains the source channel name and the message.
        TODO(kangz12345): docstring for swiftcallRequested and swiftcallReturned.
          They should be written when the swiftcall protocol is finally determined.
    """

    broadcastRequested = pyqtSignal(str, str)
    received = pyqtSignal(str, str)
    swiftcallRequested = pyqtSignal(str)
    swiftcallReturned = pyqtSignal(str, str)

    def __init__(self, name: str, parent: Optional[QObject] = None):
        """
        Args:
            name: A string that indicates the name of App.
            parent: A parent object.
        """
        super().__init__(parent=parent)
        self.name = name
        self.received.connect(self._receivedMessage)

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
            content: Content to be broadcast. It should be able to be converted to JSON object.
        """
        try:
            msg = json.dumps(content)
        except TypeError as e:
            print(f"swift.app.broadcast(): {e!r}")
        else:
            self.broadcastRequested.emit(channelName, msg)

    def receivedSlot(self, channelName: str, content: Any):
        """Handles the received broadcast message.
        
        This is called when self.received signal is emitted.
        This will be overridden by child classes.

        Args:
            channelName: Channel name that transferred the message.
            content: Received content.
        """

    @pyqtSlot(str, str)
    def _receivedMessage(self, channelName: str, msg: str):
        """This is connected to self.received signal.
        
        Args:
            channelName: Channel name that transferred the message.
            msg: Received JSON string.
        """
        try:
            content = json.loads(msg)
        except json.JSONDecodeError as e:
            print(f"swift.app._receivedMessage(): {e!r}")
        else:
            self.receivedSlot(channelName, content)
