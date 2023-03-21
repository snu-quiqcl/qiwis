"""
Module for testing swift package.
"""

import unittest
import sys
from collections.abc import Iterable

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QApplication

from swift.app import BaseApp
from swift.swift import Swift, AppInfo, BusInfo

class AppTest(unittest.TestCase):
    """Unit test for app.py."""

    def setUp(self):
        """Create an app every time."""
        self.app = BaseApp("name")

    def test_init(self):
        """Test if fields are initialized as constructor arguments."""
        self.assertEqual(self.app.name, "name")

    def test_set_parent(self):
        """Test if a parent constructor argument can be set as a QObject."""
        BaseApp("name", QObject())

    def test_frames(self):
        """Test BaseApp.frames()."""
        self.assertIsInstance(self.app.frames(), Iterable)


class SwiftTest(unittest.TestCase):
    """Unit test for swift.py"""

    appInfos = {
        "app1": AppInfo(
            module="module1",
            cls="cls1",
            path="path1",
            show="false",
            pos="left",
            bus=["bus1", "bus2"],
            args={"arg1": "value1"}
        ),
        "app2": AppInfo(
            module="module2",
            cls="cls2"
        )
    }

    busInfos = {
        "bus1": BusInfo(
            timeout=5.0
        ),
        "bus2": BusInfo()
    }

    def setUp(self):
        """Create a QApplication and Swift object every time."""
        self.qapp = QApplication(sys.argv)
        self.swift = Swift(SwiftTest.appInfos, SwiftTest.busInfos)

    def test_init(self):
        pass


if __name__ == "__main__":
    unittest.main()
