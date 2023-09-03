#!/usr/bin/env python3

"""
Qiwis is a main manager for qiwis system.

Using a set-up file written by a user, it sets up apps.

Usage:
    python -m qiwis (-s <CONFIG_PATH>)

Logging:
    The module-level logger name is __name__.
"""

import argparse
import dataclasses
import functools
import importlib
import importlib.util
import inspect
import json
import logging
import os
import sys
from collections import defaultdict, namedtuple
from contextlib import contextmanager
from types import MappingProxyType
from typing import (
    Dict, DefaultDict, Set, Any, Callable, Iterable, Mapping, Optional, Tuple,
    List, Union, TypeVar, Type
)

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication, QDockWidget, QMainWindow, QMdiArea, QMdiSubWindow, QMessageBox, QWidget
)

T = TypeVar("T")
JsonType = Union[None, float, bool, str, List["JsonType"], Dict[str, "JsonType"]]
# Generic MappingProxyType or GenericAlias is introduced in Python 3.9.
ImmutableJsonType = Union[None, float, bool, str, Tuple["ImmutableJsonType", ...], MappingProxyType]


logger = logging.getLogger(__name__)


class Serializable:  # pylint: disable=too-few-public-methods
    """A type for dataclasses that can be converted to a JSON string.
    
    The message protocols in qiwis use JSON strings to encode data.
    If a dataclass inherits this class, the dictionary yielded by asdict() must
      be able to converted to a JSON string, i.e., JSONifiable.
    Every argument of qiwiscalls must be JSONifiable by itself
      or an instance of Serializable.
    """


@dataclasses.dataclass
class AppInfo(Serializable):
    """Information required to create an app.
    
    Fields:
        module: The module name of the app class.
        cls: The name of the app class.
        path: The path for importing the module.
        show: Whether to show frames of the app.
        pos: The position of the frames on the GUI.
          It should be one of "center", "left", "right", "top", or "bottom", case-sensitive.
          Otherwise, it is set to "left".
          In the case "center", the frame is wrapped by QMdiSubWindow.
          In the other cases, the frame is wrapped by QDockWidget and
            its position follows Qt.DockWidgetArea.
        channel: The list of channels which the app subscribes to.
        args: The dictionary for the keyword arguments of the app class constructor.
          It should exclude the name and parent arguments.
          None for initializing the app with default values,
            where only the name and parent arguments will be passed.
    """
    module: str
    cls: str
    path: str = "."
    show: bool = True
    pos: str = ""
    channel: Iterable[str] = ()
    args: Optional[Mapping[str, Any]] = None


def loads(cls: Type[T], kwargs: str) -> T:
    """Returns a new cls instance from a JSON string.
    
    Args:
        cls: A class object.
        kwargs: A JSON string of a dictionary that contains the keyword arguments of cls.
          Positional arguments should be given with the argument names, just like
          the other keyword arguments.
          There must not exist arguments which are not in cls constructor.
    """
    return cls(**json.loads(kwargs))


def dumps(obj: Serializable) -> str:
    """Returns a JSON string converted from the given Serializable object.
    
    Args:
        obj: Dataclass object to convert to a JSON string.
    """
    return json.dumps(dataclasses.asdict(obj))


@dataclasses.dataclass
class QiwiscallInfo(Serializable):
    """Information of a qiwiscall request.
    
    Fields:
        call: The name of the qiwiscall feature, e.g., "createApp" for createApp().
          This is case-sensitive.
        args: The arguments of the qiwiscall as a dictionary of keyword arguements.
          The names of the arguements are case-sensitive.
          When an argument is Serializable, it must be given as a converted JSON string,
          e.g., not {"arg": QiwiscallInfo(call="call")},
          but {"arg": '{"call": "call", "args": {}}'}.
    """
    call: str
    args: Mapping[str, Any] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class QiwiscallResult(Serializable):
    """Result data of a qiwiscall.
    
    Fields:
        done: Whether the qiwiscall is done. Even when it failed, this is True as well.
        success: True when the qiwiscall is done without any problems.
        value: Return value of the qiwiscall, if any. It must be JSONifiable.
        error: Information about the problem that occurred during the qiwiscall.
    """
    done: bool
    success: bool
    value: Any = None
    error: Optional[str] = None


class Qiwis(QObject):
    """Actual manager for qiwis system.

    Note that QApplication instance must be created before instantiating Qiwis object.

    A qiwiscall is a request for the qiwis system such as creating an app.
    Messages emitted from "qiwiscallRequested" signal are considered as qiwiscall.
    For details, see _qiwiscall().

    Brief procedure:
        1. Load the configuration information.
        2. Create apps and show their frames.
    """

    def __init__(
        self,
        appInfos: Optional[Mapping[str, AppInfo]] = None,
        constants: Optional[Tuple] = None,
        parent: Optional[QObject] = None):
        """
        Args:
            appInfos: See Qiwis.load(). None or an empty dictionary for loading no apps.
            parent: A parent object.
        """
        super().__init__(parent=parent)
        self.appInfos = appInfos
        self.constants = constants
        self.mainWindow = QMainWindow()
        self.centralWidget = QMdiArea()
        self.mainWindow.setCentralWidget(self.centralWidget)
        self._wrapperWidgets = defaultdict(list)
        self._apps: Dict[str, BaseApp] = {}
        self._subscribers: DefaultDict[str, Set[str]] = defaultdict(set)
        appInfos = appInfos if appInfos else {}
        constants = appInfos if constants else {}
        self.setIconBackground()
        self.load(appInfos)
        self.mainWindow.show()

    def setIconBackground(self):
        """Sets the icon and background images."""
        if hasattr(self.constants, "icon_path"):
            icon = QIcon(self.constants.icon_path)
            self.mainWindow.setWindowIcon(icon)

    def load(self, appInfos: Mapping[str, AppInfo]):
        """Initializes qiwis system and loads the apps.
        
        Args:
            appInfos: A dictionary whose keys are app names and the values are
              corresponding AppInfo objects. All the apps in the dictionary
              will be created, and if the show field is True, its frames will
              be shown.
        """
        for name, info in appInfos.items():
            self.createApp(name, info)
        logger.info("Loaded %d app(s)", len(appInfos))

    def addFrame(self, name: str, frame: QWidget, info: AppInfo):
        """Adds the given frame and wraps it with a wrapper widget.

        This is not a qiwiscall because QWidget is not Serializable.
        
        Args:
            name: A name of app.
            frame: A frame to show.
            info: An AppInfo object describing the app.
        """
        if info.pos == "center":
            wrapperWidget = QMdiSubWindow(self.centralWidget)
            wrapperWidget.setWindowTitle(name)
            wrapperWidget.setWidget(frame)
            wrapperWidget.show()
        else:
            wrapperWidget = QDockWidget(name, self.mainWindow)
            wrapperWidget.setWidget(frame)
            area = {
                "left": Qt.LeftDockWidgetArea,
                "right": Qt.RightDockWidgetArea,
                "top": Qt.TopDockWidgetArea,
                "bottom": Qt.BottomDockWidgetArea
            }.get(info.pos, Qt.LeftDockWidgetArea)
            if info.show:
                areaDockWidgets = [
                    dockWidget for dockWidget in self.mainWindow.findChildren(QDockWidget)
                    if self.mainWindow.dockWidgetArea(dockWidget) == area
                ]
                if areaDockWidgets:
                    self.mainWindow.tabifyDockWidget(areaDockWidgets[-1], wrapperWidget)
                else:
                    self.mainWindow.addDockWidget(area, wrapperWidget)
        self._wrapperWidgets[name].append(wrapperWidget)
        logger.info("Added a frame to the app %s: %s", name, info)

    def removeFrame(self, name: str, wrapperWidget: Union[QMdiSubWindow, QDockWidget]):
        """Removes the frame from the main window.
        
        This is not a qiwiscall because QMdiSubWindow and QDockWidget are not Serializable.
        
        Args:
            name: The name of the app.
            wrapperWidget: The wrapper widget to remove.
        """
        frameName = wrapperWidget.widget().__class__.__name__
        if isinstance(wrapperWidget, QMdiSubWindow):
            self.centralWidget.removeSubWindow(wrapperWidget)
        else:
            self.mainWindow.removeDockWidget(wrapperWidget)
        self._wrapperWidgets[name].remove(wrapperWidget)
        wrapperWidget.deleteLater()
        logger.info("Removed a frame %s from the app %s", frameName, name)

    def appNames(self) -> Tuple[str]:
        """Returns the names of the apps including whose frames are hidden."""
        return tuple(self._apps.keys())

    def createApp(self, name: str, info: AppInfo, replace: bool = False):
        """Creates an app and shows their frames using set-up environment.
        
        Args:
            name: The name of the app to be added.
            info: The AppInfo object describing the app.
            replace: It describes the behavior when trying to create an existing app.
              If True, the original app will be replaced. Otherwise, it will be ignored.
        """
        if name in self._apps:
            if replace:
                self.destroyApp(name)
            else:
                logger.error("The app %s already exists.", name)
                return
        with _add_to_path(os.path.dirname(info.path)):
            module = importlib.import_module(info.module)
        cls = getattr(module, info.cls)
        if info.args is not None:
            app = cls(name, parent=self, **info.args)
        else:
            app = cls(name, parent=self)
        app.broadcastRequested.connect(self._broadcast, type=Qt.QueuedConnection)
        app.qiwiscallRequested.connect(
            functools.partial(self._qiwiscall, name),
            type=Qt.QueuedConnection,
        )
        for channelName in info.channel:
            self.subscribe(name, channelName)
        for frame in app.frames():
            self.addFrame(name, frame, info)
        self._apps[name] = app
        logger.info("Created an app %s: %s", name, info)

    def destroyApp(self, name: str):
        """Destroys an app.
        
        Args:
            name: A name of the app to destroy.
        """
        wrapperWidgets = self._wrapperWidgets[name]
        for wrapperWidget in wrapperWidgets:
            self.removeFrame(name, wrapperWidget)
        del self._wrapperWidgets[name]
        for apps in self._subscribers.values():
            apps.discard(name)
        self._apps.pop(name).deleteLater()
        logger.info("Destroyed the app %s", name)

    def updateFrames(self, name: str):
        """Updates the frames of an app.
        
        Args:
            name: A name of the app to update its frames.
        """
        app = self._apps[name]
        info = self.appInfos[name]
        orgFrames = {
            wrapperWidget.widget(): wrapperWidget
            for wrapperWidget in self._wrapperWidgets[name]
        }
        newFrames = app.frames()
        orgFramesSet = set(orgFrames)
        newFramesSet = set(newFrames)
        for frame in orgFramesSet - newFramesSet:
            self.removeFrame(name, orgFrames[frame])
        for frame in newFramesSet - orgFramesSet:
            self.addFrame(name, frame, info)
        logger.info("Updated frames: %d -> %d", len(orgFramesSet), len(newFramesSet))

    def channelNames(self) -> Tuple[str]:
        """Returns the names of the channels."""
        return tuple(self._subscribers.keys())

    def subscriberNames(self, channel: str) -> Set[str]:
        """Returns the names of the subscriber apps of the channel.
        
        Args:
            channel: The name of the channel of interest.
              If it has no subscribers or does not exist, an empty set is returned.
        """
        return self._subscribers[channel].copy()

    def subscribe(self, app: str, channel: str):
        """Starts a subscription of the app to the channel.
        
        Args:
            app: The name of the app which wants to subscribe to the channel.
            channel: The target channel name.
        """
        if app in self._subscribers[channel]:
            logger.warning("The app %s already subscribes to %s", app, channel)
        else:
            self._subscribers[channel].add(app)
            logger.info("The app %s now subscribes to %s", app, channel)

    def unsubscribe(self, app: str, channel: str) -> bool:
        """Cancels the subscription of the app to the channel.
        
        Args:
            app: The name of the app which wants to unsubscribe from the channel.
            channel: The target channel name.
        
        Returns:
            False when the app was not subscribing to the channel.
        """
        subscribers = self._subscribers[channel]
        try:
            subscribers.remove(app)
        except KeyError:
            logger.error("The app %s tried to unsubscribe from %s, "
                         "which it does not subscribe to", app, channel)
            return False
        logger.info("The app %s unsubscribed from %s", app, channel)
        return True

    @pyqtSlot(str, str)
    def _broadcast(self, channelName: str, msg: str):
        """Broadcasts the message to the subscriber apps of the channel.

        Args:
            channelName: Target channel name.
            msg: Message to be broadcast.
        """
        for name in self._subscribers[channelName]:
            self._apps[name].received.emit(channelName, msg)

    def _parseArgs(self, call: Callable, args: Mapping[str, Any]) -> Dict[str, Any]:
        """Converts all Serializable arguments to dataclass objects from strings.

        It checks the function signature of the call and converts the JSON string
        arguments to concrete dataclass instances if the parameter type is Serializable.

        The limitation of this implementation is that it can only support a single
        concrete type for each method parameter, i.e., it does not support union types,
        inheritance, etc.

        Args:
            call: Function object to inspect its signature.
            args: See QiwiscallInfo.args.
        
        Returns:
            A dictionary of the same arguments as args, but with concrete Serializable
            dataclass instances instead of JSON strings.
        """
        signature = inspect.signature(call)
        parsedArgs = {}
        for name, arg in args.items():
            cls = signature.parameters[name].annotation
            parsedArgs[name] = loads(cls, arg) if issubclass(cls, Serializable) else arg
        logger.debug("Parsed arguments %s to %s", args, parsedArgs)
        return parsedArgs

    def _handleQiwiscall(self, sender: str, msg: str) -> Any:
        """Handles the qiwiscall.

        This can raise an exception if the arguments do not follow the valid API.
        The caller must obey the API and catch the possible exceptions.
        Calling non-public methods are prohibitted.

        Args:
            sender: The name of the request sender app.
            msg: A JSON string that can be converted to QiwiscallInfo,
              i.e., the same form as the returned string of dumps().
              See QiwiscallInfo for details.
        
        Raises:
            ValueError: When the requested call is not public, i.e., starts with
              an underscore (_).
            RuntimeError: When the user rejects the request.
        
        Returns:
            The returned value of the qiwiscall, if any.
        """
        info = loads(QiwiscallInfo, msg)
        if info.call.startswith("_"):
            raise ValueError("Only public method calls are allowed.")
        call = getattr(self, info.call)
        args = self._parseArgs(call, info.args)
        reply = QMessageBox.warning(
            None,
            "qiwiscall",
            f"The app {sender} requests for a qiwiscall {info.call} with {args}.",
            QMessageBox.Ok | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if reply == QMessageBox.Ok:
            return call(**args)
        raise RuntimeError("The user rejected the request.")

    def _qiwiscall(self, sender: str, msg: str):
        """Will be connected to the qiwiscallRequested signal.

        Note that qiwiscallRequested signal only has one str argument.
        In fact the partial method will be connected using functools.partial().

        Args:
            sender: See _handleQiwiscall().
            msg: See _handleQiwiscall().
        """
        try:
            value = self._handleQiwiscall(sender, msg)
        except Exception as error:  # pylint: disable=broad-exception-caught
            result = QiwiscallResult(done=True, success=False, error=repr(error))
            logger.exception("Qiwiscall failed")
        else:
            if isinstance(value, Serializable):
                value = dumps(value)
            result = QiwiscallResult(done=True, success=True, value=value)
            logger.info("Qiwiscall success")
        self._apps[sender].qiwiscallReturned.emit(msg, dumps(result))
        logger.info("Qiwiscall result is reported")


class BaseApp(QObject):
    """Base App class that all apps should inherit.

    Signals: 
        broadcastRequested(channel, message): The app can emit this signal to request
          broadcasting to a channel with the target channel name and the message.
        received(channel, message): A broadcast message is received from a channel.
        qiwiscallRequested(request): The app can emit this signal to request
          a qiwiscall with a request message converted from a qiwis.QiwiscallInfo
          object by qiwis.dumps().
        qiwiscallReturned(request, result): The result of the requested qiwiscall
          with the original requested message and the result message converted
          from a qiwis.QiwiscallResult object by qiwis.dumps().
    
    Attributes:
        name: The string identifier name of this app.
        qiwiscall: A qiwiscall proxy for requesting qiwiscalls conveniently.
    """

    broadcastRequested = pyqtSignal(str, str)
    received = pyqtSignal(str, str)
    qiwiscallRequested = pyqtSignal(str)
    qiwiscallReturned = pyqtSignal(str, str)

    _constants = namedtuple("EmptyNamespace", ())()

    def __init__(self, name: str, parent: Optional[QObject] = None):
        """
        Args:
            name: A string that indicates the name of App.
            parent: A parent object.
        """
        super().__init__(parent=parent)
        self.name = name
        self.qiwiscall = QiwiscallProxy(self.qiwiscallRequested)
        self.received.connect(self._receivedMessage)
        self.qiwiscallReturned.connect(self._receivedQiwiscallResult)

    @property
    def constants(self) -> Tuple:
        """The global constant namespace."""
        return BaseApp._constants

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
        except TypeError:
            logger.exception("Failed to broadcast the content: %s", content)
        else:
            logger.debug("Broadcast a message to %s: %s converted from %s",
                         channelName, msg, content)
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
        except json.JSONDecodeError:
            logger.exception("Failed to receive the message: %s", msg)
        else:
            logger.debug("Received a content from %s: %s converted from %s",
                         channelName, content, msg)
            self.receivedSlot(channelName, content)

    @pyqtSlot(str, str)
    def _receivedQiwiscallResult(self, request: str, msg: str):
        """This is connected to self.qiwiscallReturned signal.

        Args:
            request: The request message that has been sent via 
              self.qiwiscallRequested signal.
            msg: The received qiwiscall result message.
        """
        try:
            result = loads(QiwiscallResult, msg)
        except json.JSONDecodeError:
            logger.exception("Failed to received the qiwiscall result message: %s", msg)
        else:
            logger.debug("Received a qiwiscall result %s for the request %s, "
                         "converted from the message %s", result, request, msg)
            self.qiwiscall.update_result(request, result)


class QiwiscallProxy:  # pylint: disable=too-few-public-methods
    """A proxy for requesting qiwiscalls conveniently.
    
    Every attribute access is proxied, and if you try to call a method of this
    object, it will emit a qiwiscall requesting signal instead.
    If you get an attribute of this object, you will get a callable object which
    does the same thing as calling a method of this object.
    """

    def __init__(self, requested: QObject):
        """
        Args:
            requested: A pyqtSignal(str) which will be emitted when a proxied
              method call is invoked. See BaseApp.qiwiscallRequested.
        """
        self.requested = requested
        self.results: Dict[str, QiwiscallResult] = {}

    def __getattr__(self, call: str) -> Callable:
        """Returns a callable object which emits a qiwiscall requesting signal.

        Args:
            call: The name of the qiwiscall.
        """
        def proxy(**args: Any) -> QiwiscallResult:
            """Emits a qiwiscall request signal with the given arguments.

            It saves the returned result to self.results dictionary, so when
            self.returned signal is emitted, i.e., the qiwiscall result is received,
            it will update the result object contents.

            Args:
                **args: The arguments for the qiwiscall, all as keyword arguments.
                  If an argument is a qiwis.Serializable instance, it will be
                  converted to a JSON string by qiwis.dumps().

            Returns:
                A qiwiscall result object to keep tracking the result.
            """
            for name, arg in args.items():
                if isinstance(arg, Serializable):
                    args[name] = dumps(arg)
            info = QiwiscallInfo(call=call, args=args)
            result = QiwiscallResult(done=False, success=False)
            msg = dumps(info)
            if msg in self.results:
                logger.warning("Duplicate qiwiscall request: %s, "
                               "the new result overwrites the previous one", msg)
            self.results[msg] = result
            self.requested.emit(msg)
            logger.debug("Requested a qiwiscall: %s converted from %s", msg, info)
            return result
        return proxy

    def update_result(self, request: str, result: QiwiscallResult, discard: bool = True):
        """Updates the result for the request parsing the received message.

        Args:
            request: The request message that has been sent to Qiwis.
            result: The received result object.
            discard: If True, the result object is removed from self.results.
              In most cases, it will be updated only once and never be looked up again.
              Therefore, it is efficient to discard it after updating the result.
              If you want to find the result from self.results later again, give False.
        """
        _get_result = self.results.pop if discard else self.results.get
        _result = _get_result(request, None)
        if _result is None:
            logger.error("Failed to find a result for request: %s", request)
            return
        _result.error = result.error
        _result.value = result.value
        _result.success = result.success
        _result.done = result.done
        logger.debug("Qiwiscall result is updated: %s", _result)


def set_global_constant_namespace(constants: Mapping[str, JsonType]) -> Tuple:
    """Creates an immutable namedtuple and sets it as the global constant namespace.

    Args:
        constants: A mapping source for the global constant namespace.
          The key-values become the constant name-values and hence the keys
          should be a valid namedtuple field name.

    Returns:
        The created namedtuple, which is the global constant namespace.
    """
    ConstantNamespace = namedtuple("ConstantNamespace", constants.keys())
    constants_ = ConstantNamespace(*map(_immutable, constants.values()))
    BaseApp._constants = constants_  # pylint: disable=protected-access
    return constants_


@contextmanager
def _add_to_path(path: str):
    """Adds a path temporarily.

    Using a 'with' statement, you can import a module without changing sys.path.

    Args:
        path: A desired path to be added. 
    """
    old_path = sys.path
    sys.path = old_path.copy()
    sys.path.insert(0, path)
    try:
        yield
    finally:
        sys.path = old_path


def _get_argparser() -> argparse.ArgumentParser:
    """Parses command line arguments.

    -c, --config: A path of set-up file.

    Returns:
        A namespace containing arguments.
    """
    parser = argparse.ArgumentParser(
        description="QuIqcl Widget Integration Software"
    )
    parser.add_argument(
        "-c", "--config", dest="config_path", default="./config.json",
        help="a path of set-up file containing the infomation about app"
    )
    return parser


def _read_config_file(config_path: str) -> Tuple[Dict[str, AppInfo], Dict[str, JsonType]]:
    """Reads the configuration information from a JSON file.

    The JSON file content should have the following structure:

      {
        "app": {
          "app_name_0": {app_info_0},
          ...
        },
        "constant": {
          "CONSTANT_0": ...,
          ...
        }
      }

    See AppInfo for app_info_* structure.
      
    Args:
        config_path: The path of the configuration file.

    Returns:
        Two dictionaries: (app_infos, constants). See appInfos in Qiwis.load().
    """
    with open(config_path, encoding="utf-8") as config_file:
        config_data: Dict[str, Dict[str, JsonType]] = json.load(config_file)
    app_dict = config_data.get("app", {})
    app_infos = {name: AppInfo(**info) for (name, info) in app_dict.items()}
    logger.info("Loaded %d app infos from %s", len(app_infos), config_path)
    constants = config_data.get("constant", {})
    logger.info("Loaded %d constants from %s", len(constants), config_path)
    return app_infos, constants


def _immutable(source: JsonType) -> ImmutableJsonType:
    """Returns the immutable version of the given JSON object.

    Args:
        source: An object which is decoded from a JSON. Every list or dict
          are converted to a tuple or types.MappingProxyType, respectively.
          The other types, e.g., float, str, etc., stay the same.
    """
    if isinstance(source, list):
        return tuple(map(_immutable, source))
    if isinstance(source, dict):
        return MappingProxyType({key: _immutable(value) for key, value in source.items()})
    return source


def main():
    """Main function that runs when qiwis module is executed rather than imported."""
    args = _get_argparser().parse_args()
    logger.info("Parsed arguments: %s", args)
    # read set-up information
    app_infos, constants = _read_config_file(args.config_path)
    # start GUI
    qapp = QApplication(sys.argv)
    constants_ = set_global_constant_namespace(constants)
    _qiwis = Qiwis(app_infos, constants_)
    logger.info("Now the QApplication starts")
    qapp.exec_()


if __name__ == "__main__":
    main()
