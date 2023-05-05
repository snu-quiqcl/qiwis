"""
Module for testing swift module.
"""

import sys
import importlib
import json
import unittest
from unittest.mock import MagicMock, patch
from collections.abc import Iterable

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QApplication, QMessageBox, QWidget

import swift

APP_INFOS = {
    "app1": swift.AppInfo(
        module="module1",
        cls="cls1",
        path="path1",
        show=False,
        pos="left",
        channel=["ch1", "ch2"],
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
        "channel": ["ch1", "ch2"],
        "args": {"arg1": "value1"}
    },
    "app2": {
        "module": "module2",
        "cls": "cls2"
    }
}

APP_JSONS = {
    "app1": ('{"module": "module1", "cls": "cls1", "path": "path1", "show": false, '
             '"pos": "left", "channel": ["ch1", "ch2"], "args": {"arg1": "value1"}}'),
    "app2": ('{"module": "module2", "cls": "cls2", "path": ".", "show": true, '
             '"pos": "", "channel": [], "args": null}'),
    "app2_default": '{"module": "module2", "cls": "cls2"}'
}


class SwiftTest(unittest.TestCase):
    """Unit test for Swift class."""

    def setUp(self):
        self.qapp = QApplication(sys.argv)
        importlib.import_module = MagicMock()
        for appInfo in APP_INFOS.values():
            app_ = MagicMock(**{"cls": appInfo.cls})
            app_.frames.return_value = (QWidget(),)
            cls = MagicMock(return_value=app_)
            setattr(importlib.import_module.return_value, appInfo.cls, cls)
        self.channels = set()
        for appInfo in APP_INFOS.values():
            self.channels.update(appInfo.channel)
        self.swift = swift.Swift(APP_INFOS)

    def test_init(self):
        self.assertEqual(self.swift.appInfos, APP_INFOS)
        for name, info in APP_INFOS.items():
            importlib.import_module.assert_any_call(info.module)
            self.assertEqual(self.swift._apps[name].cls, info.cls)
            self.assertIn(name, self.swift._dockWidgets)
        for channel in self.channels:
            self.assertIn(channel, self.swift._subscribers)

    def test_app_names(self):
        appNamesSet = set(self.swift.appNames())
        self.assertEqual(appNamesSet, set(APP_INFOS))

    def test_create_app(self):
        app_ = MagicMock(**{"cls": "cls3"})
        app_.frames.return_value = (QWidget(),)
        cls = MagicMock(return_value=app_)
        setattr(importlib.import_module.return_value, "cls3", cls)
        self.swift.createApp(
            "app3",
            swift.AppInfo(**{"module": "module3", "cls": "cls3", "channel": ["ch1"]})
        )
        importlib.import_module.assert_called_with("module3")
        self.assertEqual(self.swift._apps["app3"].cls, "cls3")
        self.assertIn("app3", self.swift._dockWidgets)
        self.assertIn("app3", self.swift._subscribers["ch1"])

    def test_destroy_app(self):
        for name, info in APP_INFOS.items():
            self.swift.destroyApp(name)
            self.assertNotIn(name, self.swift._apps)
            self.assertNotIn(name, self.swift._dockWidgets)
            for channel in info.channel:
                self.assertNotIn(name, self.swift._subscribers[channel])

    def test_update_frames_inclusive(self):
        orgFramesSet = {dockWidget.widget() for dockWidget in self.swift._dockWidgets["app1"]}
        newFramesSet = orgFramesSet | {QWidget()}
        self.swift._apps["app1"].frames.return_value = tuple(newFramesSet)
        self.swift.updateFrames("app1")
        finalFramesSet = {dockWidget.widget() for dockWidget in self.swift._dockWidgets["app1"]}
        self.assertFalse(finalFramesSet & (orgFramesSet - newFramesSet))
        self.assertEqual(finalFramesSet, newFramesSet)

    def test_update_frames_exclusive(self):
        orgFramesSet = {dockWidget.widget() for dockWidget in self.swift._dockWidgets["app1"]}
        newFramesSet = {QWidget()}
        self.swift._apps["app1"].frames.return_value = tuple(newFramesSet)
        self.swift.updateFrames("app1")
        finalFramesSet = {dockWidget.widget() for dockWidget in self.swift._dockWidgets["app1"]}
        self.assertFalse(finalFramesSet & orgFramesSet)
        self.assertEqual(finalFramesSet, newFramesSet)

    def test_channel_names(self):
        channelNamesSet = set(self.swift.channelNames())
        self.assertEqual(channelNamesSet, self.channels)

    def test_subscriber_names(self):
        for channel in self.channels:
            subscriberNamesSet = set(self.swift.subscriberNames(channel))
            self.assertEqual(
                subscriberNamesSet,
                {name for name, info in APP_INFOS.items() if channel in info.channel}
            )

    def test_unsubcribe(self):
        self.assertEqual(self.swift.unsubscribe("app1", "ch1"), True)
        self.assertNotIn("app1", self.swift._subscribers["ch1"])
        self.assertEqual(self.swift.unsubscribe("app2", "ch1"), False)

    def test_swiftcall(self):
        QMessageBox.warning = MagicMock(return_value=QMessageBox.Ok)
        self.swift._swiftcall("app1", json.dumps({"call": "appNames", "args": {}}))
        self.swift._swiftcall("app1", json.dumps({
            "call": "createApp",
            "args": {"name": "app3", "info": {"module": "module2", "cls": "cls2"}}
        }))
        self.swift.callWithSerializable = MagicMock()
        self.swift.getSerializable = MagicMock(return_value=APP_INFOS["app1"])
        self.swift._swiftcall("app1", json.dumps({"call": "getSerializable", "args": {}}))
        self.swift._swiftcall("app1", json.dumps({"call": "_broadcast", "args": {}}))
        QMessageBox.warning.return_value = QMessageBox.Cancel
        self.swift._swiftcall("app1", json.dumps({"call": "appNames", "args": {}}))

    def test_broadcast(self):
        for channelName in self.channels:
            self.swift._broadcast(channelName, "test_msg")
        for name, app_ in self.swift._apps.items():
            self.assertEqual(len(APP_INFOS[name].channel), app_.received.emit.call_count)


class BaseAppTest(unittest.TestCase):
    """Unit test for BaseApp class."""

    def setUp(self):
        self.app = swift.BaseApp("name")

    def test_init(self):
        self.assertEqual(self.app.name, "name")

    def test_set_parent(self):
        swift.BaseApp("name", QObject())

    def test_frames(self):
        self.assertIsInstance(self.app.frames(), Iterable)

    def test_broadcast(self):
        self.app.broadcastRequested = MagicMock()
        self.app.broadcast("ch1", "msg")
        self.app.broadcastRequested.emit.assert_called_once_with("ch1", '"msg"')

    def test_broadcast_exception(self):
        self.app.broadcastRequested = MagicMock()
        self.app.broadcast("ch1", lambda: None)
        self.app.broadcastRequested.emit.assert_not_called()

    def test_received_message(self):
        self.app.receivedSlot = MagicMock()
        self.app._receivedMessage("ch1", '"msg"')
        self.app.receivedSlot.assert_called_once_with("ch1", "msg")

    def test_received_message_exception(self):
        self.app.receivedSlot = MagicMock()
        self.app._receivedMessage("ch1", '"msg1" "msg2"')
        self.app.receivedSlot.assert_not_called()

    def test_received_swiftcall_result(self):
        self.app.swiftcall.update_result = MagicMock()
        self.app._receivedSwiftcallResult(
            "request", '{"done": true, "success": true, "value": null, "error": null}'
        )
        self.app.swiftcall.update_result.assert_called_once_with(
            "request",
            swift.SwiftcallResult(done=True, success=True)
        )

    def test_received_swiftcall_result_exception(self):
        self.app.swiftcall.update_result = MagicMock()
        self.app._receivedSwiftcallResult(
            "request", '{"done": "tr" "ue", "success": true, "value": null, "error": null}'
        )
        self.app.swiftcall.update_result.assert_not_called()


class SwiftcallProxyTest(unittest.TestCase):
    """Unit test for SwiftcallProxy class."""

    def setUp(self):
        self.swiftcall = swift.SwiftcallProxy(MagicMock())

    def test_getattr(self):
        self.swiftcall.call()
        self.swiftcall.call(name=APP_INFOS["app1"])
        self.swiftcall.call()

    def test_update_result(self):
        self.swiftcall.results = {
            "request1": swift.SwiftcallResult(done=False, success=False), "request2": None
        }
        self.swiftcall.update_result(
            "request1", swift.SwiftcallResult(done=True, success=True), discard=False
        )
        self.swiftcall.update_result(
            "request2", swift.SwiftcallResult(done=True, success=True)
        )


class SwiftFunctionTest(unittest.TestCase):
    """Unit test for functions."""

    def test_loads(self):
        self.assertEqual(swift.loads(swift.AppInfo, APP_JSONS["app1"]), APP_INFOS["app1"])
        self.assertEqual(swift.loads(swift.AppInfo, APP_JSONS["app2_default"]), APP_INFOS["app2"])

    def test_dumps(self):
        self.assertEqual(swift.dumps(APP_INFOS["app1"]), APP_JSONS["app1"])
        self.assertEqual(swift.dumps(APP_INFOS["app2"]), APP_JSONS["app2"])

    def test_add_to_path(self):
        test_dir = "/test_dir"
        old_path = sys.path.copy()
        with swift._add_to_path(test_dir):
            self.assertNotEqual(old_path, sys.path)
            self.assertIn(test_dir, sys.path)
        self.assertEqual(old_path, sys.path)

    @patch.object(sys, "argv", ["", "-s", "test_setup.json"])
    def test_get_argparser(self):
        parser = swift._get_argparser()
        args = parser.parse_args()
        self.assertEqual(args.setup_path, "test_setup.json")

    @patch.object(sys, "argv", [""])
    def test_get_argparser_default(self):
        args = swift._get_argparser().parse_args()
        self.assertEqual(args.setup_path, "./setup.json")

    @patch("builtins.open")
    @patch("json.load", return_value={"app": APP_DICTS})
    def test_read_setup_file(self, mock_open, mock_load):
        self.assertEqual(swift._read_setup_file(""), APP_INFOS)
        mock_open.assert_called_once()
        mock_load.assert_called_once()

    @patch("swift._get_argparser")
    @patch("swift._read_setup_file", return_value={})
    @patch("swift.Swift")
    @patch("PyQt5.QtWidgets.QApplication.exec_")
    def test_main(self, mock_get_argparser, mock_read_setup_file, mock_swift, mock_exec_):
        swift.main()
        mock_get_argparser.assert_called_once()
        mock_read_setup_file.assert_called_once()
        mock_swift.assert_called_once()
        mock_exec_.assert_called_once()


if __name__ == "__main__":
    unittest.main()
