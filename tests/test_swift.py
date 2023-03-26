"""
Module for testing swift package.
"""

import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import importlib
from collections.abc import Iterable

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel

from swift.app import BaseApp
from swift.swift import (
    Swift, AppInfo, parse, strinfo,
    _add_to_path, _get_argparser, _read_setup_file, main
)

APP_INFOS = {
    "app1": AppInfo(
        module="module1",
        cls="cls1",
        path="path1",
        show=False,
        pos="left",
        bus=["bus1", "bus2"],
        args={"arg1": "value1"}
    ),
    "app2": AppInfo(
        module="module2",
        cls="cls2"
    )
}

APP_DICTS = {
    "app1": {
        "module": "module1",
        "cls": "cls1",
        "path": "path1",
        "show": False,
        "pos": "left",
        "bus": ["bus1", "bus2"],
        "args": {"arg1": "value1"}
    },
    "app2": {
        "module": "module2",
        "cls": "cls2"
    }
}

APP_JSONS = {
    "app1": ('{"module": "module1", "cls": "cls1", "path": "path1", "show": false, '
             '"pos": "left", "bus": ["bus1", "bus2"], "args": {"arg1": "value1"}}'),
    "app2": ('{"module": "module2", "cls": "cls2", "path": ".", "show": true, '
             '"pos": "", "bus": [], "args": null}'),
    "app2_default": '{"module": "module2", "cls": "cls2"}'
}

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
    """Unit test for Swift class in swift.py"""

    def setUp(self):
        """Create a QApplication and a Swift object every time."""
        importlib.import_module = MagicMock()
        for name, appInfo in APP_INFOS.items():
            importlib.import_module.return_value.setattr(appInfo.cls, BaseApp(name))
        # start GUI
        self.qapp = QApplication(sys.argv)
        self.swift = Swift(APP_INFOS)

    def test_init(self):
        """Test if swift is initialized correctly."""
        self.assertIsInstance(self.swift.mainWindow, QMainWindow)
        self.assertIsInstance(self.swift.centralWidget, QLabel)
        buses = set()
        for name, appInfo in APP_INFOS.items():
            self.assertIn(name, self.swift._apps)
            buses.update(appInfo.bus)
        for bus in buses:
            self.assertIn(bus, self.swift._subscribers)

    def test_destroy_app(self):
        """Test destroyApp()."""
        name = list(APP_INFOS.keys())[0]
        self.swift.destroyApp(name)
        self.assertNotIn(name, self.swift._apps)


class SwiftFunctionTest(unittest.TestCase):
    """Unit test for functions in swift.py"""

    def test_parse(self):
        """Test parse()."""
        self.assertEqual(parse(AppInfo, APP_JSONS["app1"]), APP_INFOS["app1"])
        self.assertEqual(parse(AppInfo, APP_JSONS["app2_default"]), APP_INFOS["app2"])

    def test_strinfo(self):
        """Test strinfo()."""
        self.assertEqual(strinfo(APP_INFOS["app1"]), APP_JSONS["app1"])
        self.assertEqual(strinfo(APP_INFOS["app2"]), APP_JSONS["app2"])

    def test_add_to_path(self):
        """Test _add_to_path()."""
        old_path = sys.path.copy()
        with _add_to_path(os.path.dirname("test_dir")):
            self.assertNotEqual(old_path, sys.path)
        self.assertEqual(old_path, sys.path)

    @patch.object(sys, "argv", ["", "-s", "test_setup.json"])
    def test_get_argparser(self):
        """Test _get_argparser()."""
        parser = _get_argparser()
        args = parser.parse_args()
        self.assertEqual(parser.description, "SNU widget integration framework for PyQt")
        self.assertEqual(args.setup_path, "test_setup.json")

    @patch.object(sys, "argv", [""])
    def test_get_argparser_default(self):
        """Test _get_argparser() with default options."""
        args = _get_argparser().parse_args()
        self.assertEqual(args.setup_path, "./setup.json")

    @patch("builtins.open")
    @patch("json.load", return_value={"app": APP_DICTS})
    def test_read_setup_file(self, mock_open, mock_load):
        """Test _read_setup_file()."""
        self.assertEqual(_read_setup_file(""), APP_INFOS)
        mock_open.assert_called_once()
        mock_load.assert_called_once()

    @patch("swift.swift._get_argparser")
    @patch("swift.swift._read_setup_file", return_value=({}, {}))
    @patch("swift.swift.Swift")
    @patch("PyQt5.QtWidgets.QApplication.exec_")
    def test_main(self, mock_get_argparser, mock_read_setup_file, mock_swift, mock_exec_):
        """Test main()."""
        main()
        mock_get_argparser.assert_called_once()
        mock_read_setup_file.assert_called_once()
        mock_swift.assert_called_once()
        mock_exec_.assert_called_once()


if __name__ == "__main__":
    unittest.main()
