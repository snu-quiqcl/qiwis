"""
Module for testing swift package.
"""

import unittest
from unittest.mock import MagicMock, patch
import sys
import importlib
from collections.abc import Iterable

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QLabel

from swift import app, swift

APP_INFOS = {
    "app1": swift.AppInfo(
        module="module1",
        cls="cls1",
        path="path1",
        show=False,
        pos="left",
        bus=["bus1", "bus2"],
        args={"arg1": "value1"}
    ),
    "app2": swift.AppInfo(
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
        self.app = app.BaseApp("name")

    def test_init(self):
        """Test if fields are initialized as constructor arguments."""
        self.assertEqual(self.app.name, "name")

    def test_set_parent(self):
        """Test if a parent constructor argument can be set as a QObject."""
        app.BaseApp("name", QObject())

    def test_frames(self):
        """Test BaseApp.frames()."""
        self.assertIsInstance(self.app.frames(), Iterable)


class SwiftTest(unittest.TestCase):
    """Unit test for Swift class in swift.py"""

    def setUp(self):
        """Create a QApplication and a Swift object every time."""
        self.qapp = QApplication(sys.argv)
        importlib.import_module = MagicMock()
        for appInfo in APP_INFOS.values():
            app_ = MagicMock()
            app_.frames.return_value = (QWidget(),)
            cls = MagicMock(return_value=app_)
            setattr(importlib.import_module.return_value, appInfo.cls, cls)
        self.buses = set()
        for appInfo in APP_INFOS.values():
            self.buses.update(appInfo.bus)
        self.buses = sorted(self.buses)
        self.swift = swift.Swift(APP_INFOS)

    def test_init(self):
        """Test if swift is initialized correctly."""
        self.assertIsInstance(self.swift.mainWindow, QMainWindow)
        self.assertIsInstance(self.swift.centralWidget, QLabel)
        for name in APP_INFOS:
            self.assertIn(name, self.swift._apps)
        for bus in self.buses:
            self.assertIn(bus, self.swift._subscribers)

    def test_destroy_app(self):
        """Test destroyApp()."""
        name = next(iter(APP_INFOS))
        self.swift.destroyApp(name)
        self.assertNotIn(name, self.swift._apps)

    def test_broadcast(self):
        """Test _broadcast()."""
        busName = next(iter(self.buses))
        self.swift._broadcast(busName, "test_msg")
        for app_ in self.swift._subscribers[busName]:
            app_.received.emit.assert_called_once()


class SwiftFunctionTest(unittest.TestCase):
    """Unit test for functions in swift.py"""

    def test_parse(self):
        """Test parse()."""
        self.assertEqual(swift.parse(swift.AppInfo, APP_JSONS["app1"]), APP_INFOS["app1"])

    def test_parse_default(self):
        """Test parse() about default fields."""
        self.assertEqual(swift.parse(swift.AppInfo, APP_JSONS["app2_default"]), APP_INFOS["app2"])

    def test_strinfo(self):
        """Test strinfo()."""
        self.assertEqual(swift.strinfo(APP_INFOS["app1"]), APP_JSONS["app1"])
        self.assertEqual(swift.strinfo(APP_INFOS["app2"]), APP_JSONS["app2"])

    def test_add_to_path(self):
        """Test _add_to_path()."""
        test_dir = "/test_dir"
        old_path = sys.path.copy()
        with swift._add_to_path(test_dir):
            self.assertNotEqual(old_path, sys.path)
            self.assertIn(test_dir, sys.path)
        self.assertEqual(old_path, sys.path)

    @patch.object(sys, "argv", ["", "-s", "test_setup.json"])
    def test_get_argparser(self):
        """Test _get_argparser()."""
        parser = swift._get_argparser()
        args = parser.parse_args()
        self.assertEqual(args.setup_path, "test_setup.json")

    @patch.object(sys, "argv", [""])
    def test_get_argparser_default(self):
        """Test _get_argparser() with default options."""
        args = swift._get_argparser().parse_args()
        self.assertEqual(args.setup_path, "./setup.json")

    @patch("builtins.open")
    @patch("json.load", return_value={"app": APP_DICTS})
    def test_read_setup_file(self, mock_open, mock_load):
        """Test _read_setup_file()."""
        self.assertEqual(swift._read_setup_file(""), APP_INFOS)
        mock_open.assert_called_once()
        mock_load.assert_called_once()

    @patch("swift.swift._get_argparser")
    @patch("swift.swift._read_setup_file", return_value={})
    @patch("swift.swift.Swift")
    @patch("PyQt5.QtWidgets.QApplication.exec_")
    def test_main(self, mock_get_argparser, mock_read_setup_file, mock_swift, mock_exec_):
        """Test main()."""
        swift.main()
        mock_get_argparser.assert_called_once()
        mock_read_setup_file.assert_called_once()
        mock_swift.assert_called_once()
        mock_exec_.assert_called_once()


if __name__ == "__main__":
    unittest.main()
