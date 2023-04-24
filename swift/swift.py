#!/usr/bin/env python3

"""
Swift is a main manager for swift system.

Using a set-up file written by a user, it sets up apps.

Usage:
    python -m swift.swift (-s <SETUP_PATH>)
"""

import sys
import os
import argparse
import json
import importlib
import importlib.util
import inspect
import dataclasses
import functools
from collections import defaultdict
from contextlib import contextmanager
from typing import (
    Dict, Any, Callable, Iterable, Mapping, Optional, TypeVar, Type
)

from PyQt5.QtCore import QObject, pyqtSlot, Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QDockWidget, QMessageBox, QWidget


T = TypeVar("T")


class Serializable:  # pylint: disable=too-few-public-methods
    """A type for dataclasses that can be converted to a JSON string.
    
    The message protocols in swift use JSON strings to encode data.
    If a dataclass inherits this class, the dictionary yielded by asdict() must
      be able to converted to a JSON string, i.e., JSONifiable.
    Every argument of swift-calls must be JSONifiable by itself
      or an instance of Serializable.
    """


@dataclasses.dataclass
class AppInfo(Serializable):
    """Information required to create an app.
    
    Fields:
        module: Module name in which the app class resides.
        cls: App class name.
        path: System path for module importing.
        show: Whether to show the app frames on creation.
        pos: Position on the main window; refer to Qt.DockWidgetArea enum.
          Should be one of "left", "right", "top", or "bottom", case-sensitive.
          Otherwise, defaults to Qt.LeftDockWidgetArea.
        channel: Channels which the app subscribes to.
        args: Keyword argument dictionary of the app class constructor.
          It must exclude name and parent arguments. Even if they exist, they will be ignored.
          None for initializing the app with default values,
          where only name and parent arguments will be passed.
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
class SwiftcallInfo(Serializable):
    """Information of a swift-call request.
    
    Fields:
        call: The name of the swift-call feature, e.g., "createApp" for createApp().
          This is case-sensitive.
        args: The arguments of the swift-call as a dictionary of keyword arguements.
          The names of the arguements are case-sensitive.
          When an argument is Serializable, it must be given as a converted JSON string,
          e.g., not {"arg": SwiftcallInfo(call="call")},
          but {"arg": '{"call": "call", "args": {}}'}.
    """
    call: str
    args: Mapping[str, Any] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class SwiftcallResult(Serializable):
    """Result data of a swift-call.
    
    Fields:
        done: Whether the swift-call is done. Even when it failed, this is True as well.
        success: True when the swift-call is done without any problems.
        value: Return value of the swift-call, if any. It must be JSONifiable.
        error: Information about the problem that occurred during the swift-call.
    """
    done: bool
    success: bool
    value: Any = None
    error: Optional[str] = None


class Swift(QObject):
    """Actual manager for swift system.

    Note that QApplication instance must be created before instantiating Swift object.

    A swift-call is a request for the swift system such as creating an app.
    Messages emitted from "swiftcallRequested" signal are considered as swift-call.
    For details, see _swiftcall().

    Brief procedure:
        1. Load setup environment.
        2. Create apps and show their frames.
    """

    def __init__(
        self,
        appInfos: Optional[Mapping[str, AppInfo]] = None,
        parent: Optional[QObject] = None):
        """
        Args:
            appInfos: See Swift.load(). None or an empty dictionary for loading no apps.
            parent: A parent object.
        """
        super().__init__(parent=parent)
        self.appInfos = appInfos
        self.mainWindow = QMainWindow()
        self.centralWidget = QLabel("Swift")
        self.centralWidget.setAlignment(Qt.AlignCenter)
        self.centralWidget.setStyleSheet("background-color: gray;")
        self.mainWindow.setCentralWidget(self.centralWidget)
        self._dockWidgets = defaultdict(list)
        self._apps = {}
        self._subscribers = defaultdict(set)
        appInfos = appInfos if appInfos else {}
        self.load(appInfos)
        self.mainWindow.show()

    def load(self, appInfos: Mapping[str, AppInfo]):
        """Initializes swift system and loads the apps.
        
        Args:
            appInfos: A dictionary whose keys are app names and the values are
              corresponding AppInfo objects. All the apps in the dictionary
              will be created, and if the show field is True, its frames will
              be shown.
        """
        for name, info in appInfos.items():
            self.createApp(name, info)

    def addFrame(self, name: str, frame: QWidget, info: AppInfo):
        """Adds a frame of the app and wraps it with a dock widget.

        This is not a swift-call because QWidget is not Serializable.
        
        Args:
            name: A name of app.
            frame: A frame to show.
            info: An AppInfo object describing the app.
        """
        dockWidget = QDockWidget(name, self.mainWindow)
        dockWidget.setWidget(frame)
        area = {
            "left": Qt.LeftDockWidgetArea,
            "right": Qt.RightDockWidgetArea,
            "top": Qt.TopDockWidgetArea,
            "bottom": Qt.BottomDockWidgetArea
        }.get(info.pos, Qt.LeftDockWidgetArea)
        if info.show:
            self.mainWindow.addDockWidget(area, dockWidget)
        self._dockWidgets[name].append(dockWidget)

    def removeFrame(self, dockWidget: QDockWidget):
        """Removes the frame from the main window.
        
        This is not a swift-call because QDockWidget is not Serializable.
        
        Args:
            dockWidget: A dock widget to remove.
        """
        self.mainWindow.removeDockWidget(dockWidget)
        dockWidget.deleteLater()

    def createApp(self, name: str, info: AppInfo):
        """Creates an app and shows their frames using set-up environment.
        
        Args:
            name: A name of app.
            info: An AppInfo object describing the app.
        """
        with _add_to_path(os.path.dirname(info.path)):
            module = importlib.import_module(info.module)
        cls = getattr(module, info.cls)
        if info.args is not None:
            app = cls(name, parent=self, **info.args)
        else:
            app = cls(name, parent=self)
        app.broadcastRequested.connect(self._broadcast, type=Qt.QueuedConnection)
        app.swiftcallRequested.connect(
            functools.partial(self._swiftcall, name),
            type=Qt.QueuedConnection,
        )
        for channelName in info.channel:
            self._subscribers[channelName].add(app)
        for frame in app.frames():
            self.addFrame(name, frame, info)
        self._apps[name] = app

    def destroyApp(self, name: str):
        """Destroys an app.
        
        Args:
            name: A name of the app to destroy.
        """
        dockWidgets = self._dockWidgets.pop(name)
        for dockWidget in dockWidgets:
            self.removeFrame(dockWidget)
        app = self._apps.pop(name)
        for apps in self._subscribers.values():
            apps.discard(app)
        app.deleteLater()

    def updateFrames(self, name: str):
        """Updates the frames of an app.
        
        Args:
            name: A name of the app to update its frames.
        """
        app = self._apps[name]
        info = self.appInfos[name]
        orgFrames = {dockWidget.widget(): dockWidget for dockWidget in self._dockWidgets[name]}
        newFrames = app.frames()
        orgFramesSet = set(orgFrames)
        newFramesSet = set(newFrames)
        for frame in orgFramesSet - newFramesSet:
            self.removeFrame(orgFrames[frame])
        for frame in newFramesSet - orgFramesSet:
            self.addFrame(name, frame, info)

    @pyqtSlot(str, str)
    def _broadcast(self, channelName: str, msg: str):
        """Broadcasts the message to the subscriber apps of the channel.

        Args:
            channelName: Target channel name.
            msg: Message to be broadcast.
        """
        for app in self._subscribers[channelName]:
            app.received.emit(channelName, msg)

    def _parseArgs(self, call: Callable, args: Mapping[str, Any]) -> Dict[str, Any]:
        """Converts all Serializable arguments to dataclass objects from strings.

        It checks the function signature of the call and converts the JSON string
        arguments to concrete dataclass instances if the parameter type is Serializable.

        The limitation of this implementation is that it can only support a single
        concrete type for each method parameter, i.e., it does not support union types,
        inheritance, etc.

        Args:
            call: Function object to inspect its signature.
            args: See SwiftcallInfo.args.
        
        Returns:
            A dictionary of the same arguments as args, but with concrete Serializable
            dataclass instances instead of JSON strings.
        """
        signature = inspect.signature(call)
        parsedArgs = {}
        for name, arg in args.items():
            cls = signature.parameters[name].annotation
            parsedArgs[name] = loads(cls, arg) if issubclass(cls, Serializable) else arg
        return parsedArgs

    def _handleSwiftcall(self, sender: str, msg: str) -> Any:
        """Handles the swift-call.

        This can raise an exception if the arguments do not follow the valid API.
        The caller must obey the API and catch the possible exceptions.

        Args:
            sender: The name of the request sender app.
            msg: A JSON string that can be converted to SwiftcallInfo,
              i.e., the same form as the returned string of strinfo().
              See SwiftcallInfo for details.
        
        Raises:
            RuntimeError: When the user rejects the request.
        
        Returns:
            The returned value of the swift-call, if any.
        """
        info = loads(SwiftcallInfo, msg)
        if info.call.startswith("_"):
            raise ValueError("Only public method calls are allowed.")
        call = getattr(self, info.call)
        args = self._parseArgs(call, info.args)
        reply = QMessageBox.warning(
            None,
            "swift-call",
            f"The app {sender} requests for a swift-call {info.call} with {args}.",
            QMessageBox.Ok | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if reply == QMessageBox.Ok:
            return call(**args)
        raise RuntimeError("The user rejected the request.")

    def _swiftcall(self, sender: str, msg: str):
        """Will be connected to the swiftcallRequested signal.

        Note that swiftcallRequested signal only has one str argument.
        In fact the partial method will be connected using functools.partial().

        Args:
            sender: See _handleSwiftcall().
            msg: See _handleSwiftcall().
        """
        try:
            value = self._handleSwiftcall(sender, msg)
        except Exception as error:  # pylint: disable=broad-exception-caught
            result = SwiftcallResult(done=True, success=False, error=repr(error))
        else:
            if isinstance(value, Serializable):
                value = dumps(value)
            result = SwiftcallResult(done=True, success=True, value=value)
        self._apps[sender].swiftcallReturned.emit(msg, dumps(result))


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

    -s, --setup: A path of set-up file.

    Returns:
        A namespace containing arguments.
    """
    parser = argparse.ArgumentParser(
        description="SNU widget integration framework for PyQt"
    )
    parser.add_argument(
        "-s", "--setup", dest="setup_path", default="./setup.json",
        help="a path of set-up file containing the infomation about app"
    )
    return parser


def _read_setup_file(setup_path: str) -> Mapping[str, AppInfo]:
    """Reads set-up information from a JSON file.

    The JSON file content should have the following structure:

      {
        "app": {
          "app_name_0": {app_info_0},
          ...
        }
      }

    See AppInfo for app_info_* structure.
      
    Args:
        setup_path: A path of set-up file.

    Returns:
        A dictionary of set-up information about apps. See appInfos in Swift.load().
    """
    with open(setup_path, encoding="utf-8") as setup_file:
        setup_data: Dict[str, Dict[str, dict]] = json.load(setup_file)
    app_dict = setup_data.get("app", {})
    app_infos = {name: AppInfo(**info) for (name, info) in app_dict.items()}
    return app_infos


def main():
    """Main function that runs when swift module is executed rather than imported."""
    args = _get_argparser().parse_args()
    # read set-up information
    app_infos = _read_setup_file(args.setup_path)
    # start GUI
    qapp = QApplication(sys.argv)
    _swift = Swift(app_infos)
    qapp.exec_()


if __name__ == "__main__":
    main()
