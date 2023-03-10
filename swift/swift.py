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

from PyQt5.QtCore import QObject, pyqtSlot, Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QDockWidget

from swift.bus import Bus

class Swift(QObject):
    """Actual manager for swift system.

    Note that QApplication instance must be created before instantiating Swift object.

    Brief procedure:
        1. Load setup environment.
        2. Create buses.
        3. Create apps and show their frames.

    Attributes:
        _buses: A dictionary for storing buses.
          Each element represents a bus.
          A key is a bus name and its value is a Bus object.
        _apps: A dictionary for storing apps.
          Each element represents an app.
          A key is an app name and its value is an App object.
    """

    def __init__(self, setupEnv: dict, parent=None):
        """
        Args:
            setupEnv: A dictionary containing set-up environment about app and bus.
              It has two keys; "app" and "bus".
              In "app", there may be keys below; 
                "path", "module", "class", "show", "pos", "bus", and "args".
              In "bus", there may be keys below;
                "timeout".
              For details, see setup.json.
            parent: A parent object.
        """
        super().__init__(parent=parent)
        self.mainWindow = QMainWindow()
        self._setupEnv = setupEnv
        self._buses = {}
        self._apps = {}
        self._subscribers = {}
        self.load()

    def load(self):
        """Initializes swift system and loads the apps and buses."""
        for name in self._setupEnv["bus"]:
            self.createBus(name)
        for name, info in self._setupEnv["app"].items():
            self.createApp(name, info["show"], info["pos"])
        self.mainWindow.show()

    def createBus(self, name: str):
        """Creates a global bus using set-up environment.
        
        Args:
            name: A string that indicates the name of the bus.
              It should be defined in the set-up file.
        """
        info = self._setupEnv["bus"][name]
        # create a bus
        if "timeout" in info:
            bus = Bus(name, info["timeout"])
        else:
            bus = Bus(name)
        # set a slot of received signal to router
        bus.received.connect(self._routeToApp)
        bus.start()
        # store the bus
        self._buses[name] = bus
        self._subscribers.setdefault(name, set())

    def createApp(self, name: str, show: str = True, pos: str = ""):
        """Creates an app and shows their frames using set-up environment.
        
        Args:
            name: A string that indicates the name of the app.
              It should be defined in the set-up file.
            show: True if you want to show the frames, otherwise False.
            pos: A string that indicates the position of the frames.
              It should be one of "left", "right", "top", or "bottom"; and is case-sensitive.
              Otherwise, it will be regarded as default (AllDockWidgetAreas).
        """
        info = self._setupEnv["app"][name]
        # import the app module
        path = info.get("path", ".")
        mod_name, cls_name = info["module"], info["class"]
        with _add_to_path(os.path.dirname(path)):
            module = importlib.import_module(mod_name)
        # create an app
        cls = getattr(module, cls_name)
        args = info.get("args", {})
        app = cls(name, self, **args)
        # set a slot of broadcast signal to router
        app.broadcastRequested.connect(self._routeToBus)
        # add the app to the list of subscribers on each bus
        for bus_name in info["bus"]:
            self._subscribers[bus_name].add(app)
        # show frames if the "show" option is true
        if show:
            for frame in app.frames():
                dockWidget = QDockWidget(name, self.mainWindow)
                dockWidget.setWidget(frame)
                area = {
                    "left": Qt.LeftDockWidgetArea,
                    "right": Qt.RightDockWidgetArea,
                    "top": Qt.TopDockWidgetArea,
                    "bottom": Qt.BottomDockWidgetArea
                }.get(pos, Qt.AllDockWidgetAreas)
                self.mainWindow.addDockWidget(area, dockWidget)
        # store the app
        self._apps[name] = app

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
def _add_to_path(path):
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


def _get_argparser():
    """Parses command line arguments

    -s, --setup: A path of set-up file.

    Returns:
        argparse.ArgumentParser: A namespace containing arguments
    """
    parser = argparse.ArgumentParser(
        description="SNU widget integration framework for PyQt"
    )
    parser.add_argument(
        "-s", "--setup", dest="setup_path", default="./setup.json",
        help="a path of set-up file containing the infomation about app and bus"
    )
    return parser


def _read_setup_file(setup_path: str):
    """Reads set-up information about app and bus from set-up file.

    Args:
        setup_path: A path of set-up file.

    Returns:
        dict: A dictionary containing set-up environment about app and bus.
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
