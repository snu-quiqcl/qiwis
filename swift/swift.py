#!/usr/bin/env python3

"""
Swift is a main manager for swift system.

Using a set-up file created by an user, it sets up apps and buses.

Usage:
    python swift.py (-s <SETUP_PATH>)
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

    Brief procedure:
        1. Create buses.
        2. Create apps.
        3. Show frames of each app.
    """

    def __init__(self, setup_env: dict):
        """
        Args:
            setup_env: Set-up environment about app and bus.
        """
        super().__init__()
        self._buses = {}
        self._apps = {}
        self._subscribers = {}
        self._init_bus(setup_env["bus"])
        self._init_app(setup_env["app"])
        self._show_frame(setup_env["app"])

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
            app = cls(name)
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
        self._mainWindow = QMainWindow()
        pos_to_area = {
            "left": Qt.LeftDockWidgetArea,
            "right": Qt.RightDockWidgetArea,
            "top": Qt.TopDockWidgetArea,
            "bottom": Qt.BottomDockWidgetArea
        }
        for name, info in setup_app.items():
            # show frames if the 'show' option is true.
            if info["show"]:
                frames = self._apps[name].frames()
                for frame in frames:
                    dockWidget = QDockWidget(name, self._mainWindow)
                    dockWidget.setWidget(frame)
                    area = pos_to_area.get(info["pos"], Qt.AllDockWidgetAreas)
                    self._mainWindow.addDockWidget(area, dockWidget)
        self._mainWindow.show()

    @pyqtSlot(str, str)
    def _route_to_bus(self, bus_name: str, msg: str):
        """Routes a signal from an app to the desired bus.

        This is a slot for the broadcast signal of each app.

        Args:
            bus_name: A name of the desired bus that will transfer the signal.
            msg: An input message that will be transferred through the bus.
        """
        bus = self._buses[bus_name]
        bus.write(msg)

    @pyqtSlot(str)
    def _route_to_app(self, msg: str):
        """Routes a signal from a bus to the apps that subscribe to it.

        This is a slot for the received signal of each bus.

        Args:
            msg: An input message that be transferred through the bus.
        """
        bus_name = self.sender().name
        # Emit a signal of all apps that subscribe to the bus.
        for app in self._subscribers[bus_name]:
            app.received.emit(bus_name, msg)


@contextmanager
def _add_to_path(path):
    old_path = sys.path
    old_modules = sys.modules
    sys.modules = old_modules.copy()
    sys.path = sys.path[:]
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
    """
    with open(setup_path, encoding="utf-8") as setup_file:
        setup_data = json.load(setup_file)
        setup_app = setup_data["app"]
        setup_bus = setup_data["bus"]
    return {"app": setup_app, "bus": setup_bus}


def main():
    """Main function that runs when swift.py is called."""
    args = _get_argparser().parse_args()
    # read set-up information
    setup_env = _read_setup_file(args.setup_path)

    app = QApplication(sys.argv)
    _swift = Swift(setup_env)
    app.exec_()


if __name__ == "__main__":
    main()
