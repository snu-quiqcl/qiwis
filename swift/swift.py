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
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from typing import (
    Dict, Any, Iterable, Mapping, Optional, TypeVar, Type
)

from PyQt5.QtCore import QObject, pyqtSlot, Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QDockWidget


T = TypeVar("T")


@dataclass
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
    return json.dumps(asdict(info))


class Swift(QObject):
    """Actual manager for swift system.

    Note that QApplication instance must be created before instantiating Swift object.

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
        self._dockWidgets = {}
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
        for channelName in info.channel:
            self._subscribers[channelName].add(app)
        if info.show:
            for frame in app.frames():
                dockWidget = QDockWidget(name, self.mainWindow)
                dockWidget.setWidget(frame)
                area = {
                    "left": Qt.LeftDockWidgetArea,
                    "right": Qt.RightDockWidgetArea,
                    "top": Qt.TopDockWidgetArea,
                    "bottom": Qt.BottomDockWidgetArea
                }.get(info.pos, Qt.LeftDockWidgetArea)
                self.mainWindow.addDockWidget(area, dockWidget)
                self._dockWidgets[name] = dockWidget
        self._apps[name] = app

    def destroyApp(self, name: str):
        """Destroys an app.
        
        Args:
            name: A name of the app to destroy.
        """
        dockWidget = self._dockWidgets.pop(name)
        self.mainWindow.removeDockWidget(dockWidget)
        app = self._apps.pop(name)
        for apps in self._subscribers.values():
            apps.discard(app)
        app.deleteLater()

    @pyqtSlot(str, str)
    def _broadcast(self, channelName: str, msg: str):
        """Broadcasts the message to the subscriber apps of the channel.

        If channelName is "swift", the message is for system call.

        Args:
            channelName: Target channel name.
            msg: Message to be broadcast.
        """
        if channelName == "swift":
            self._call_system(msg)
        for app in self._subscribers[channelName]:
            app.received.emit(channelName, msg)

    def _call_system(self, msg: str):
        """Handles the system call.

        Args:
            msg: A JSON string of a message about a system call.
              Its keys represent an action. 
              All requested actions are performed sequentially.
              Possible actions are as follows.
              
              "create": create an app.
                its value is a name of app you want to create.
              "destroy": destroy an app.
                its value is a dictionary with two keys; "name" and "info".
                The value of "name" is a name of app you want to destroy.
                The value of "info" is a JSON string of a dictionary 
                  that contains the keyword arguments of AppInfo.
        """
        msg = json.loads(msg)
        for action, contents in msg.items():
            if action == "create":
                self.createApp(contents["name"], AppInfo(**contents["info"]))
            elif action == "destroy":
                self.destroyApp(contents)
            else:
                print(f"The system call was ignored because "
                      f"the treatment for the action {action} is not implemented.")


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
