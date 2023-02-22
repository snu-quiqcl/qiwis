#!/usr/bin/env python3

"""
Swift is a main manager for swift system.

Using a set-up file created by an user, it sets up apps and buses.

Usage:
    python swift.py (-s <SETUP_PATH>)
"""

import sys, os
import argparse
import json
import importlib.util

from PyQt5.QtCore import QObject, pyqtSlot, Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QDockWidget

from swift.bus import Bus

class Swift(QObject):
    """Actual manager for swift system.

    Brief procedure:
        1. Read a set-up file about app and bus.
        2. Create buses.
        3. Create apps.
        4. Show frames of each app.

    Attributes:
        setup_app: A set-up information about apps.
        setup_bus: A set-up information about buses.
    """

    def __init__(self, setup_path: str):
        """
        Args:
            setup_path: A path of set-up file.
        """
        super().__init__()
        self.read_setup_file(setup_path)
        self.init_bus()
        self.init_app()
        self.show_frame()

    def read_setup_file(self, setup_path: str):
        """Reads set-up information from set-up file.

        Read set-up file and store information about app and bus.

        Args:
            setup_path: A path of set-up file.
        """
        with open(setup_path, encoding="utf-8") as setup_file:
            setup_data = json.load(setup_file)

            self.setup_app = setup_data['app']
            self.setup_bus = setup_data['bus']

    def init_bus(self):
        """Initializes global buses using set-up environment.

        Create the instance of each global bus and store them at self.buses.
        """
        self.buses = {}

        for name, info in self.setup_bus.items():
            bus = None

            # create a bus
            if "timeout" in info:
                timeout = info['timeout']
                bus = Bus(name, timeout)
            else:
                bus = Bus(name)

            # set a slot of received signal to router
            bus.received.connect(self.route_to_app)

            self.buses[name] = bus

    def init_app(self):
        """Initializes apps using set-up environment.

        Create the instance of each app and store them at self.apps.
        """
        self.apps = {}

        for name, info in self.setup_app.items():
            # import app
            file_path, cls_name = info['path'], info['class']

            module_name = os.path.basename(file_path)
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # create an app
            cls = getattr(module, cls_name)
            app = cls(name)

            # set a slot of broadcast signal to router
            app.broadcastRequested.connect(self.route_to_bus)

            # add the app to the list of subscribers on each bus
            for bus_name in info['bus']:
                self.subs[bus_name].append(app)

            self.apps[name] = app

    def show_frame(self):
        """Shows frames of each app."""
        self.main_window = QMainWindow()

        for name, info in self.setup_app.items():
            # show frames if the 'show' option is true.
            if info['show']:
                frames = self.apps[name].frames()

                for frame in frames:
                    dock_widget = QDockWidget(name, self.main_window)
                    dock_widget.setWidget(frame)

                    self.main_window.addDockWidget(Qt.RightDockWidgetArea, dock_widget)

        self.main_window.show()

    @pyqtSlot(str, str)
    def route_to_bus(self, bus_name: str, msg: str):
        """Routes a signal from an app to the desired bus.

        This is a slot for the broadcast signal of each app.

        Args:
            bus_name: A name of the desired bus that will transfer the signal.
            msg: An input message that will be transferred through the bus.
        """
        bus = self.buses[bus_name]
        bus.write(msg)

    @pyqtSlot(str)
    def route_to_app(self, msg: str):
        """Routes a signal from a bus to the apps that subscribe to it.

        This is a slot for the received signal of each bus.

        Args:
            msg: An input message that be transferred through the bus.
        """
        bus_name = self.sender().name

        # Emit a signal of all apps that subscribe to the bus.
        for app in self.subs[bus_name]:
            app.received.emit(bus_name, msg)


def get_argparser():
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


def main():
    """Main function that runs when swift.py is called."""
    args = get_argparser().parse_args()

    app = QApplication(sys.argv)
    _swift = Swift(args.setup_path)
    app.exec_()


if __name__ == "__main__":
    main()
