#!/usr/bin/env python3

"""
Swift is a main manager for swift system.

Using a set-up file written by an user, it sets up apps and buses.

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
from PyQt5.QtWidgets import QApplication, QMainWindow, QDockWidget

from swift.bus import Bus

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
          Otherwise, defaults to Qt.AllDockWidgetAreas.
        bus: Buses which the app subscribes to.
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
    bus: Iterable[str] = ()
    args: Mapping[str, Any] | None = None

    @classmethod
    def parse(cls, info: str) -> Self:
        """Constructs an AppInfo object from a JSON string.
        
        Args:
            info: A JSON string of a dictionary that contains the information of an app.
              Its keys are field names of AppInfo and values are corresponding values.
              Exceptionally for "cls" field, "class" is also accepted.
              If both "cls" and "class" exist, then "class" is ignored.
              If both does not exist, a KeyError("cls") is raised.
        
        Raises:
            KeyError: When there is no mandatory fields in info.
        """
        info: dict[str, Any] = json.loads(info)
        info_cls = info.pop("class", None)
        if info.setdefault("cls", info_cls) is None:
            raise KeyError("cls")
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

    def __init__(
        self,
        appInfos: Mapping[str, AppInfo] | None = None,
        busInfos: Mapping[str, BusInfo] | None = None,
        parent: QObject | None = None):
        """
        Args:
            appInfos: See Swift.load(). None or an empty dictionary for loading no apps.
            busInfos: See Swift.load(). None or an empty dictionary for loading no buses.
            parent: A parent object.
        """
        super().__init__(parent=parent)
        self.mainWindow = QMainWindow()
        self._buses = {}
        self._apps = {}
        self._subscribers = {}
        appInfos = appInfos if appInfos else {}
        busInfos = busInfos if busInfos else {}
        self.load(appInfos, busInfos)
        self.mainWindow.show()

    def load(self, appInfos: Mapping[str, AppInfo], busInfos: Mapping[str, BusInfo]):
        """Initializes swift system and loads the apps and buses.
        
        Args:
            appInfos: A dictionary whose keys are app names and the values are
              corresponding AppInfo objects. All the apps in the dictionary
              will be created, and if the show field is True, its frames will
              be shown.
            busInfos: A dictionary whose keys are bus names and the values are
              corresponding BusInfo objects. All the buses in the dictionary
              will be created and started.
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
        if info.timeout is not None:
            bus = Bus(name, info.timeout)
        else:
            bus = Bus(name)
        bus.received.connect(self._routeToApp)
        bus.start()
        self._buses[name] = bus
        self._subscribers.setdefault(name, set())

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
        app.broadcastRequested.connect(self._routeToBus)
        for busName in info.bus:
            self._subscribers[busName].add(app)
        if info.show:
            for frame in app.frames():
                dockWidget = QDockWidget(name, self.mainWindow)
                dockWidget.setWidget(frame)
                area = {
                    "left": Qt.LeftDockWidgetArea,
                    "right": Qt.RightDockWidgetArea,
                    "top": Qt.TopDockWidgetArea,
                    "bottom": Qt.BottomDockWidgetArea
                }.get(info.pos, Qt.AllDockWidgetAreas)
                self.mainWindow.addDockWidget(area, dockWidget)
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


def _read_setup_file(setup_path: str) -> tuple[Mapping[str, AppInfo], Mapping[str, BusInfo]]:
    """Reads set-up information about app and bus from a JSON file.

    The JSON file content should have the following structure:

      {
        "app": {
          "app_name_0": {app_info_0},
          ...
        },
        "bus": {
          "bus_name_0": {bus_info_0},
          ...
        }
      }

    See AppInfo and its parse() for app_info_* structure.
    See BusInfo and its parse() for bus_info_* structure.
      
    Args:
        setup_path: A path of set-up file.

    Returns:
        A tuple of two dictionaries of set-up information about app and bus.
          See appInfos and busInfos in Swift.load() for more details.
    """
    with open(setup_path, encoding="utf-8") as setup_file:
        setup_data: dict[str, dict] = json.load(setup_file)
    app_dict = setup_data.get("app", {})
    bus_dict = setup_data.get("bus", {})
    app_infos = {name: AppInfo.parse(json.dumps(info)) for (name, info) in app_dict.items()}
    bus_infos = {name: BusInfo.parse(json.dumps(info)) for (name, info) in bus_dict.items()}
    return app_infos, bus_infos


def main():
    """Main function that runs when swift module is executed rather than imported."""
    args = _get_argparser().parse_args()
    # read set-up information
    app_infos, bus_infos = _read_setup_file(args.setup_path)
    # start GUI
    qapp = QApplication(sys.argv)
    _swift = Swift(app_infos, bus_infos)
    qapp.exec_()


if __name__ == "__main__":
    main()
