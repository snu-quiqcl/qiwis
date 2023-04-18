"""
Base module for App.

Every App class should be a subclass of BaseApp.
"""

import json
from typing import Any, Dict, Optional, Callable, Iterable

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QWidget

from swift import swift

class BaseApp(QObject):
    """Base App class that all apps should inherit.

    Signals: 
        broadcastRequested(channel, message): The app can emit this signal to request
          broadcasting to a channel with the target channel name and the message.
        received(channel, message): A broadcast message is received from a channel.
        swiftcallRequested(request): The app can emit this signal to request
          a swift-call with a request message converted from a swift.SwiftcallInfo
          object by swift.dumps().
        swiftcallReturned(request, result): The result of the requested swift-call
          with the original requested message and the result message converted
          from a swift.SwiftcallResult object by swift.dumps().
    
    Attributes:
        name: The string identifier name of this app.
        swiftcall: A swift-call proxy for requesting swift-calls conveniently.
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
        self.swiftcall = SwiftcallProxy(self.swiftcallRequested)
        self.received.connect(self._receivedMessage)
        self.swiftcallReturned.connect(self._receivedSwiftcallResult)

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

    @pyqtSlot(str, str)
    def _receivedSwiftcallResult(self, request: str, msg: str):
        """This is connected to self.swiftcallReturned signal.

        Args:
            request: The request message that has been sent via 
              self.swiftcallRequested signal.
            msg: The received swift-call result message.
        """
        try:
            result = swift.loads(swift.SwiftcallResult, msg)
        except json.JSONDecodeError as e:
            print(f"{self}._receivedResult: {e}")
        else:
            self.swiftcall.update_result(request, result)


class SwiftcallProxy:  # pylint: disable=too-few-public-methods
    """A proxy for requesting swift-calls conveniently.
    
    Every attribute access is proxied, and if you try to call a method of this
    object, it will emit a swift-call requesting signal instead.
    If you get an attribute of this object, you will get a callable object which
    does the same thing as calling a method of this object.
    """

    def __init__(self, requested: QObject):
        """
        Args:
            requested: A pyqtSignal(str) which will be emitted when a proxied
              method call is invoked. See BaseApp.swiftcallRequested.
        """
        self.requested = requested
        self.results: Dict[str, swift.SwiftcallResult] = {}

    def __getattr__(self, call: str) -> Callable:
        """Returns a callable object which emits a swift-call requesting signal.

        Args:
            call: The name of the swift-call.
        """
        def proxy(**args: Any) -> swift.SwiftcallResult:
            """Emits a swift-call request signal with the given arguments.

            It saves the returned result to self.results dictionary, so when
            self.returned signal is emitted, i.e., the swift-call result is received,
            it will update the result object contents.

            Args:
                **args: The arguments for the swift-call, all as keyword arguments.
                  If an argument is a swift.Serializable instance, it will be
                  converted to a JSON string by swift.dumps().

            Returns:
                A swift-call result object to keep tracking the result.
            """
            for name, arg in args.items():
                if isinstance(arg, swift.Serializable):
                    args[name] = swift.dumps(arg)
            info = swift.SwiftcallInfo(call=call, args=args)
            result = swift.SwiftcallResult(done=False, success=False)
            msg = swift.dumps(info)
            self.results[msg] = result
            self.requested.emit(msg)
            return result
        return proxy

    def update_result(self, request: str, result: swift.SwiftcallResult):
        """Updates the result for the request parsing the received message.

        Args:
            request: The request message that has been sent to Swift.
            result: The received result object.
        """
        _result = self.results.get(request, None)
        if _result is None:
            print(f"SwiftcallProxy._update_result: Failed to find a result for {request}.")
            return
        _result.error = result.error
        _result.value = result.value
        _result.success = result.success
        _result.done = result.done
