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
    """

    def __init__(self, setup_env: dict, parent=None):
        """
        Args:
            setup_env: A dictionary containing set-up environment about app and bus.
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
        self._buses = {}
        self._apps = {}
        self._subscribers = {}
        self._init_bus(setup_env["bus"])
        self._init_app(setup_env["app"])
        self._show_frame(setup_env["app"])

    def load(self, appInfos: dict, busInfos: dict):
        pass

    def createBus(self, name: str):
        """Creates a global bus using set-up environment.
        
        Args:
            name: A string that indicates the name of the bus.
              It should be defined in the set-up file.
        """
        info = self.setup_bus[name]
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
        self._subscribers[name] = []

    def createApp(self, name: str, show: str = True, pos: str = ""):
        info = self.setup_app[name]
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
            self._subscribers[bus_name].append(app)
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

    def _init_bus(self, setup_bus: dict):
        """Initializes global buses using set-up environment.
        
        Args:
            setup_bus: Set-up environment about bus.
        """
        for name, info in setup_bus.items():
            # create a bus
            if "timeout" in info:
                timeout = info["timeout"]
                bus = Bus(name, timeout)
            else:
                bus = Bus(name)
            # set a slot of received signal to router
            bus.received.connect(self._route_to_app)
            bus.start()
            # store the bus
            self._buses[name] = bus
            self._subscribers[name] = []

    def _init_app(self, setup_app: dict):
        """Initializes apps using set-up environment.
        
        Args:
            setup_app: Set-up environment about app.
        """
        for name, info in setup_app.items():
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
            app.broadcastRequested.connect(self._route_to_bus)
            # add the app to the list of subscribers on each bus
            for bus_name in info["bus"]:
                self._subscribers[bus_name].append(app)
            # store the app
            self._apps[name] = app

    def _show_frame(self, setup_app: dict):
        """Shows frames of each app.
        
        Args:
            setup_app: Set-up environment about app.
        """
        pos_to_area = {
            "left": Qt.LeftDockWidgetArea,
            "right": Qt.RightDockWidgetArea,
            "top": Qt.TopDockWidgetArea,
            "bottom": Qt.BottomDockWidgetArea
        }
        for name, info in setup_app.items():
            # show frames if the 'show' option is true
            if info["show"]:
                for frame in self._apps[name].frames():
                    dockWidget = QDockWidget(name, self.mainWindow)
                    dockWidget.setWidget(frame)
                    area = pos_to_area.get(info["pos"], Qt.AllDockWidgetAreas)
                    self.mainWindow.addDockWidget(area, dockWidget)
        self.mainWindow.show()

    @pyqtSlot(str, str)
    def _routeToBus(self, bus_name: str, msg: str):
        """Routes a signal from an app to the desired bus.

        This is a slot for the broadcast signal of each app.

        Args:
            bus_name: A name of the desired bus that will transfer the signal.
            msg: An input message to be transferred through the bus.
        """
        bus = self._buses[bus_name]
        bus.write(msg)

    @pyqtSlot(str)
    def _routeToApp(self, msg: str):
        """Routes a signal from a bus to the apps that subscribe to it.

        This is a slot for the received signal of each bus.

        Args:
            msg: An input message transferred through the bus.
        """
        bus_name = self.sender().name
        # emit a signal of all apps that subscribe to the bus
        for app in self._subscribers[bus_name]:
            app.received.emit(bus_name, msg)


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
    setup_env = _read_setup_file(args.setup_path)

    app = QApplication(sys.argv)
    _swift = Swift(setup_env)
    app.exec_()


if __name__ == "__main__":
    main()
