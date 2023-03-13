#!/usr/bin/env python3

"""
Swift is a main manager for swift system.

Using a set-up file written by a user, it sets up apps and buses.

Usage:
    python -m swift.swift (-s <SETUP_PATH>)
"""

import sys
import os
import argparse
import json
import importlib
import importlib.util
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from typing import Any, Iterable, Mapping, Self

from PyQt5.QtCore import QObject, pyqtSlot, Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QDockWidget

from swift.bus import Bus

@dataclass
class AppInfo:
    """Information required to create an app.
    
    Fields:
        module: Module name in which the app class resides.
        class_: App class name.
        path: System path for module importing. None if it is not necessary.
        show: Whether to show the app frames on creation.
        pos: Position on the main window; refer to Qt.DockWidgetArea enum.
          Should be one of "left", "right", "top", or "bottom", case-sensitive.
          Otherwise, defaults to Qt.AllDockWidgetAreas.
        bus: Buses which the app subscribes to.
        args: Keyword argument dictionary of the app class constructor.
          It must exclude name and parent arguments. Even if they exist, they will be ignored.
          None for initializing the app with default values,
          where only name and parent arguments will be passed.
    """
    module: str
    class_: str
    path: str | None = None
    show: bool = True
    pos: str = ""
    bus: Iterable[str] = ()
    args: Mapping[str, Any] | None = None

    @classmethod
    def parse(cls, info: str) -> Self:
        """Constructs an AppInfo object from a JSON string.
        
        Args:
            info: A JSON string of a dictionary that contains the information of an app.
              Its keys are field names of AppInfo and values are corresponding values.
              Exceptionally for "class_" field, "class" is also accepted.
              If both "class_" and "class" exist, then "class" is ignored.
              If both does not exist, a KeyError("class_") is raised.
        
        Raises:
            KeyError: When there is no mandatory fields in info.
        """
        info: dict[str, Any] = json.loads(info)
        class_ = info.pop("class", None)
        if info.setdefault("class_", class_) is None:
            raise KeyError("class_")
        return cls(**info)


@dataclass
class BusInfo:
    """Information required to create a bus.
    
    Fields:
        timeout: See bus.Bus.__init__(). None for the default value of __init__().
    """
    timeout: float | None = None

    @classmethod
    def parse(cls, info: str) -> Self:
        """Constructs a BusInfo object from a JSON string.
        
        Args:
            info: A JSON string of a dictionary that contains the information of a bus.
              Its keys are field names of BusInfo and values are corresponding values.
        
        Raises:
            KeyError: When there is no mandatory fields in info.
        """
        return cls(**json.loads(info))


def strinfo(info: AppInfo | BusInfo) -> str:
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
        2. Create buses.
        3. Create apps and show their frames.
    """

    def __init__(self, setupEnv: Mapping[str, Mapping], parent: QObject | None = None):
        """
        Args:
            setupEnv: A dictionary containing set-up environment about app and bus.
              It has two keys; "app" and "bus".
              In "app", there are apps containing keys as below; 
                "path" (optional), "module", "class", "show", "pos", "bus", and "args" (optional).
              In "bus", there are buses containing keys as below;
                "timeout" (optional).
              For details, see setup.json.
            parent: A parent object.
        """
        super().__init__(parent=parent)
        self.mainWindow = QMainWindow()
        self.centralWidget = QLabel("Swift")
        self.centralWidget.setAlignment(Qt.AlignCenter)
        self.centralWidget.setStyleSheet("background-color: gray;")
        self.mainWindow.setCentralWidget(self.centralWidget)
        self._buses = {}
        self._apps = {}
        self._subscribers = {}
        self.load(setupEnv["app"], setupEnv["bus"])
        self.mainWindow.show()

    def load(self, appInfos: Mapping[str, Mapping], busInfos: Mapping[str, Mapping]):
        """Initializes swift system and loads the apps and buses.
        
        Args:
            appInfos: See "app" part of setupEnv in self.__init__().
            busInfos: See "bus" part of setupEnv in self.__init__().
        """
        for name, info in busInfos.items():
            self.createBus(name, info)
        for name, info in appInfos.items():
            self.createApp(name, info)

    def createBus(self, name: str, info: BusInfo):
        """Creates a bus from the given information.
        
        Args:
            name: A name of the bus.
            info: A BusInfo object describing the bus.
        """
        # create a bus
        if info.timeout is not None:
            bus = Bus(name, info.timeout)
        else:
            bus = Bus(name)
        # set a slot of received signal to router
        bus.received.connect(self._routeToApp)
        bus.start()
        # store the bus
        self._buses[name] = bus
        self._subscribers.setdefault(name, set())

    def createApp(self, name: str, info: Mapping[str, Any]):
        """Creates an app and shows their frames using set-up environment.
        
        Args:
            name: A name of app.
            info: A dictionary containing app info. Each element is like below:
              path: A path desired to be added for importing app.
              module: A name of app module.
              class: A name of app class.
              show: Whether its frames are shown at the beginning.
                True if you want to show the frames, otherwise False.
              pos: A string that indicates the position of the frames.
                It should be one of "left", "right", "top", or "bottom"; and is case-sensitive.
                Otherwise, it will be regarded as default (AllDockWidgetAreas).
              bus: A list of buses which the app subscribes to.
              args: Additional arguments for app class constructor.
                If there is no additional arguments, set None.
        """
        # import the app module
        with _add_to_path(os.path.dirname(info.get("path", "."))):
            module = importlib.import_module(info["module"])
        # create an app
        cls = getattr(module, info["class"])
        if "args" in info:
            app = cls(name, parent=self, **info["args"])
        else:
            app = cls(name, parent=self)
        # set a slot of broadcast signal to router
        app.broadcastRequested.connect(self._routeToBus)
        # add the app to the list of subscribers on each bus
        for busName in info["bus"]:
            self._subscribers[busName].add(app)
        # show frames if the "show" option is true
        if info["show"]:
            for frame in app.frames():
                dockWidget = QDockWidget(name, self.mainWindow)
                dockWidget.setWidget(frame)
                area = {
                    "left": Qt.LeftDockWidgetArea,
                    "right": Qt.RightDockWidgetArea,
                    "top": Qt.TopDockWidgetArea,
                    "bottom": Qt.BottomDockWidgetArea
                }.get(info["pos"], Qt.AllDockWidgetAreas)
                self.mainWindow.addDockWidget(area, dockWidget)
        # store the app
        self._apps[name] = app

    def destroyBus(self, name: str):
        """Destroys a global bus.
        
        Args:
            name: A name of the bus to destroy.
        """
        bus = self._buses.pop(name)
        bus.stop()
        bus.deleteLater()

    def destroyApp(self, name: str):
        """Destroys an app.
        
        Args:
            name: A name of the app to destroy.
        """
        app = self._apps.pop(name)
        for apps in self._subscribers.values():
            apps.discard(app)
        app.deleteLater()

    @pyqtSlot(str, str)
    def _routeToBus(self, busName: str, msg: str):
        """Routes a signal from an app to the desired bus.

        This is a slot for the broadcast signal of each app.

        Args:
            busName: A name of the desired bus that will transfer the signal.
            msg: An input message to be transferred through the bus.
        """
        bus = self._buses[busName]
        bus.write(msg)

    @pyqtSlot(str)
    def _routeToApp(self, msg: str):
        """Routes a signal from a bus to the apps that subscribe to it.

        This is a slot for the received signal of each bus.

        Args:
            msg: An input message transferred through the bus.
        """
        busName = self.sender().name
        # emit a signal of all apps that subscribe to the bus
        for app in self._subscribers[busName]:
            app.received.emit(busName, msg)


@contextmanager
def _add_to_path(path: str):
    """Adds a path temporarily.

    Using a 'with' statement, you can import a module without changing sys.path.

    Args:
        path: A desired path to be added. 
    """
    old_modules = sys.modules
    sys.modules = old_modules.copy()
    old_path = sys.path
    sys.path = old_path.copy()
    sys.path.insert(0, path)
    try:
        yield
    finally:
        sys.path = old_path
        sys.modules = old_modules


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
        help="a path of set-up file containing the infomation about app and bus"
    )
    return parser


def _read_setup_file(setup_path: str) -> dict[str, dict]:
    """Reads set-up information about app and bus from set-up file.

    Args:
        setup_path: A path of set-up file.

    Returns:
        A dictionary containing set-up environment about app and bus.
          For details, see Swift.__init__().
    """
    with open(setup_path, encoding="utf-8") as setup_file:
        setup_data = json.load(setup_file)
    return {key: setup_data[key] for key in ("app", "bus")}


def main():
    """Main function that runs when swift module is executed rather than imported."""
    args = _get_argparser().parse_args()
    # read set-up information
    setupEnv = _read_setup_file(args.setup_path)
    # start GUI
    app = QApplication(sys.argv)
    _swift = Swift(setupEnv)
    app.exec_()


if __name__ == "__main__":
    main()
