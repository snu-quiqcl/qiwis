#!/usr/bin/env python3
"""Swift is a main manager for swift system.

Using a set-up file created by an user, it sets up Buses and Frames.

1. Read a set-up file about Frame and Bus.
2. Create an instance of each Bus.
3. Create and show Frames.

Usage:
    python swift.py (-s <SETUP_PATH>)
"""

import sys
import argparse
import json
import importlib

<<<<<<< HEAD
=======
from PyQt5.QtCore import QObject, pyqtSlot, Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QDockWidget
>>>>>>> 2536c54 (Wrap frames around QDockWidget and show them)

class Swift:
    """The actual manager for swift system.

    Attributes:
        setup_frame: A set-up information about frames.
        setup_bus: A set-up information about buses.
    """

    def __init__(self, setup_path: str):
        """Constructor.

        Args:
            setup_path (str): A path of set-up file.
        """
        self.read_setup_file(setup_path)
        self.init_bus()
        self.init_frame()
        self.show_frame()

    def read_setup_file(self, setup_path: str):
        """Read set-up information from set-up file.

        Read set-up file and store information about frame and bus at fields.

        Args:
            setup_path (str): A path of set-up file.
        """
        with open(setup_path, encoding="utf-8") as setup_file:
            setup_data = json.load(setup_file)

            self.setup_frame = setup_data['frame']
            self.setup_bus = setup_data['bus']

    def init_bus(self):
        """Initialize global buses using set-up environment.

        Create the instance of each global bus and store them at dictionary field.
        """
        self.buses = {}

        for name, info in self.setup_bus.items():
            mod = importlib.import_module(info['module'])
            cls = getattr(mod, info['class'])

            self.buses[name] = cls(name)

    def init_frame(self):
        """Initialize frames using set-up environment.

        Create the instance of each frame (exactly, Logic class) and store them at dictionary field.
        """
        self.frames = {}

        for name, info in self.setup_frame.items():
            mod = importlib.import_module(info['module'])
            cls = getattr(mod, info['class'])

            frame = cls(name, info['show'], info['pos'])
            # Set a slot of broadcast signal of each frame
            # to the method receiving this signal in Bus.
            for bus_name in info['dest_bus']:
                bus = self.buses[bus_name]
                frame.broadcast_signal.connect(bus.write)

            # Set a slot of received signal of each global bus
            # to the method receiving this signal in Frame.
            for bus_name in info['subs_bus']:
                bus = self.buses[bus_name]
                bus.received.connect(frame.receive_bus_signal)

            self.frames[name] = frame

<<<<<<< HEAD
=======
    def show_frame(self):
        """Show frames using set-up environment.

        Show only frames of which 'show' option is true.
        """
        self.dock_widgets = {}

        self.main_window = QMainWindow()

        for name, info in self.setup_frame.items():
            if info['show']:  # Show the frame if the 'show' option is true.
                frame = self.frames[name].frame
                dock_widget = QDockWidget(name, self.main_window)
                dock_widget.setWidget(frame)

                self.main_window.addDockWidget(Qt.RightDockWidgetArea, dock_widget)

                self.dock_widgets[name] = dock_widget

        self.main_window.show()

    @pyqtSlot(str, str)
    def route_to_bus(self, bus_name: str, msg: str):
        """Route a signal from a frame to the destination bus.

        This is a slot for the broadcast signal of each frame.

        Args:
            bus_name (str): A name of the destination bus which will transfer the global signal.
            msg (str): An input message that will be transferred through the glboal signal.
        """
        bus = self.buses[bus_name]
        bus.write(msg)

    @pyqtSlot(str)
    def route_to_frame(self, msg: str):
        """Route a signal from a bus to the subscriber frames.

        This is a slot for the received signal of each bus.

        Args:
            msg (str): An input message that be transferred through the global bus.
        """
        bus_name = self.sender().name

        # Emit a signal of all subscriber frames.
        for frame in self.subs[bus_name]:
            frame.received.emit(bus_name, msg)

>>>>>>> 2536c54 (Wrap frames around QDockWidget and show them)

def get_argparser():
    """Parse command line arguments

    -s, --setup: A path of set-up file.

    Returns:
        argparse.ArgumentParser: A namespace containing arguments
    """
    parser = argparse.ArgumentParser(description="SNU widget integration framework for PyQt")

    parser.add_argument(
        "-s", "--setup", dest="setup_path", default="./setup.json",
        help="a path of set-up file containing the infomation about frame and bus"
    )

    return parser


def main():
    """Main function that runs when swift.py is called. 
    """
    args = get_argparser().parse_args()

    app = QApplication(sys.argv)
    _swift = Swift(args.setup_path)
    app.exec_()


if __name__ == "__main__":
    main()
