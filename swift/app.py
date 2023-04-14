"""
Base module for App.

Every App class should be a subclass of BaseApp.
"""

import json
from typing import Any, Optional, Callable, Iterable

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QWidget

class BaseApp(QObject):
    """Base App class that all apps should inherit.

    Signals: 
        broadcastRequested(str, str): The app requested broadcasting to a channel 
          with the target channel name and the message.
        received(str, str): A message is received from a channel which contains
          the source channel name and the message.
        swiftcallRequested(str): The app requested a swiftcall with a string
          message converted from a swift.SwiftcallInfo object by swift.dumps().
        swiftcallReturned(str, str): The result of the requested swift-call
          with the original requested message and the result message converted
          from a swift.SwiftcallResult object by swift.dumps().
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


class SwiftcallProxy:
    """A proxy for requesting swift-calls conveniently.
    
    Every attribute access is proxied, and if you try to call a method of this
    object, it will emit a swift-call requesting signal instead.
    If you get an attribute of this object, you will get a callable object which
    does the same thing as calling a method of this object.
    """

    def __init__(self, requested: QObject, returned: QObject):
        """
        Args:
            requested: A pyqtSignal(str) which will be emitted when a proxied
              method call is invoked. See BaseApp.swiftcallRequested.
            returned: A pyqtSignal(str, str) to which slots will be connected.
              See BaseApp.swiftcallReturned.
        """
        self.requested = requested
        self.returned = returned

    def __getattribute__(self, call: str) -> Callable:
        """Returns a callable object which emits a swift-call requesting signal.

        Args:
            call: The name of the swift-call.
        """
