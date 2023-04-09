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
import dataclasses
from collections import defaultdict
from contextlib import contextmanager
from typing import (
    Dict, Any, Iterable, Mapping, Optional, TypeVar, Type
)

from PyQt5.QtCore import QObject, pyqtSlot, Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QDockWidget, QMessageBox


T = TypeVar("T")


@dataclasses.dataclass
class AppInfo:
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


def parse(cls: Type[T], kwargs: str) -> T:
    """Returns a new cls instance from a JSON string.

    This is a convenience function for just unpacking the JSON string and gives them
    as keyword arguments of the constructor of cls.
        
    Args:
        cls: A class object.
        kwargs: A JSON string of a dictionary that contains the keyword arguments of cls.
          Positional arguments should be given with the argument names, just like
          the other keyword arguments.
          There must not exist arguments which are not in cls constructor.
    """
    return cls(**json.loads(kwargs))


def strinfo(info: AppInfo) -> str:
    """Returns a JSON string converted from the given info.

    This is just a convenience function for users not to import dataclasses and json.
    
    Args:
        info: Dataclass object to convert to a JSON string.
    """
    return json.dumps(dataclasses.asdict(info))


@dataclasses.dataclass
class Result:
    """Result data of a swift-call.
    
    Fields:
        done: Whether the swift-call is done. True when the it has failed as well.
        success: True when the swift-call is done without any problems.
        value: Return value of the swift-call, if any. It must be converted to a JSON string.
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
        app.swiftcallRequested.connect(self._swiftcall, type=Qt.QueuedConnection)
        for channelName in info.channel:
            self._subscribers[channelName].add(app)
        for frame in app.frames():
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
        self._apps[name] = app

    def destroyApp(self, name: str):
        """Destroys an app.
        
        Args:
            name: A name of the app to destroy.
        """
        dockWidgets = self._dockWidgets.pop(name)
        for dockWidget in dockWidgets:
            self.mainWindow.removeDockWidget(dockWidget)
            dockWidget.deleteLater()
        app = self._apps.pop(name)
        for apps in self._subscribers.values():
            apps.discard(app)
        app.deleteLater()

    @pyqtSlot(str, str)
    def _broadcast(self, channelName: str, msg: str):
        """Broadcasts the message to the subscriber apps of the channel.

        Args:
            channelName: Target channel name.
            msg: Message to be broadcast.
        """
        for app in self._subscribers[channelName]:
            app.received.emit(channelName, msg)

    def _handleSwiftcall(self, sender: str, msg: str) -> Any:
        """Handles the swift-call.

        This can raise an exception if the arguments do not follow the valid API.
        The caller must obey the API and catch the possible exceptions.

        Args:
            sender: The name of the request sender app.
            msg: A JSON string of a message with two keys; "action" and "args".
              Possible actions are as follows.
              
              "create": Create an app.
                Its "args" is a dictionary with two keys; "name" and "info".
                The value of "name" is a name of app you want to create.
                The value of "info" is a dictionary that contains the keyword arguments of AppInfo.
              "destory": Destroy an app.
                Its "args" is a dictionary with a key; "name".
                The value of "name" is a name of app you want to destroy.
        
        Raises:
            RuntimeError: When the user rejects the request.
            NotImplementedError: When the given request action is not implemented.
        
        Returns:
            The returned value of the swift-call, if any.
        """
        msg = json.loads(msg)
        action, args = msg["action"], msg["args"]
        if action == "create":
            name, info = args["name"], args["info"]
            reply = QMessageBox.warning(
                None,
                "swift-call",
                f"The app {sender} requests for creating an app {name}",
                QMessageBox.Ok | QMessageBox.Cancel,
                QMessageBox.Cancel
            )
            if reply == QMessageBox.Ok:
                return self.createApp(name, AppInfo(**info))
            else:
                raise RuntimeError("user rejected the request.")
        elif action == "destroy":
            name = args["name"]
            reply = QMessageBox.warning(
                None,
                "swift-call",
                f"The app {sender} requests for destroying an app {name}",
                QMessageBox.Ok | QMessageBox.Cancel,
                QMessageBox.Cancel
            )
            if reply == QMessageBox.Ok:
                return self.destroyApp(name)
            else:
                raise RuntimeError("user rejected the request.")
        else:
            raise NotImplementedError(action)

    @pyqtSlot(str)
    def _swiftcall(self, msg: str):
        """Slot for the swiftcallRequested signal.

        Args:
            msg: See _handleSwiftcall().
        """
        sender = self.sender()
        try:
            value = self._handleSwiftcall(sender.name, msg)
        except Exception as error:
            result = Result(done=True, success=False, error=repr(error))
        else:
            result = Result(done=True, success=True, value=value)
        sender.swiftcallReturned.emit(msg, json.dumps(dataclasses.asdict(result)))


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
