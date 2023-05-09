"""
Module for testing swift module.
"""

import dataclasses
import sys
import importlib
import json
import unittest
from unittest.mock import MagicMock, patch, DEFAULT, call
from collections.abc import Iterable
from typing import Any, Optional, Mapping

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


qapp = QApplication(sys.argv)


class SwiftTest(unittest.TestCase):
    """Unit test for Swift class."""

    def setUp(self):
        importlib.import_module = MagicMock()
        for appInfo in APP_INFOS.values():
            app_ = MagicMock()
            app_.cls = appInfo.cls
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
        app_ = MagicMock()
        app_.cls = "cls3"
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
        """Tests for the case where a new frame is added in the return of frames()."""
        orgFramesSet = {dockWidget.widget() for dockWidget in self.swift._dockWidgets["app1"]}
        newFramesSet = orgFramesSet | {QWidget()}
        self.swift._apps["app1"].frames.return_value = tuple(newFramesSet)
        self.swift.updateFrames("app1")
        finalFramesSet = {dockWidget.widget() for dockWidget in self.swift._dockWidgets["app1"]}
        self.assertEqual(finalFramesSet, newFramesSet)

    def test_update_frames_exclusive(self):
        """Tests for the case where a new frame replaced the return of frames()."""
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

    def help_swiftcall(
        self,
        value: Any,
        result: swift.SwiftcallResult,
        error: Optional[Exception] = None):
        """Helper method for testing _swiftcall()."""
        msg = swift.dumps(swift.SwiftcallInfo(call="callForTest", args={}))
        with patch.multiple(self.swift, _handleSwiftcall=DEFAULT, _apps=DEFAULT):
            if error is None:
                self.swift._handleSwiftcall.return_value = value
            else:
                self.swift._handleSwiftcall.side_effect = error
            self.swift._swiftcall(sender="sender", msg=msg)
            mocked_signal = self.swift._apps["sender"].swiftcallReturned
            mocked_signal.emit.assert_called_once_with(msg, swift.dumps(result))

    def test_swiftcall_primitive(self):
        """The swiftcall returns a primitive type value, which can be JSONified.
        
        This assumes that swift.dumps() works correctly.
        """
        value = [1.5, True, None, "abc"]
        result = swift.SwiftcallResult(done=True, success=True, value=value)
        self.help_swiftcall(value, result)

    def test_swiftcall_serializable(self):
        """The swiftcall returns a Serializable type value.
        
        This assumes that swift.dumps() works correctly.
        """
        @dataclasses.dataclass
        class ClassForTest(swift.Serializable):
            a: str
        value = ClassForTest(a="abc")
        result = swift.SwiftcallResult(done=True, success=True, value=swift.dumps(value))
        self.help_swiftcall(value, result)

    def test_swiftcall_exception(self):
        """The swiftcall raises an exception."""
        class ExceptionForTest(Exception):
            ...
        value = None
        error = ExceptionForTest("test")
        result = swift.SwiftcallResult(done=True, success=False, error=repr(error))
        self.help_swiftcall(value, result, error)

    def test_broadcast(self):
        for channelName in self.channels:
            self.swift._broadcast(channelName, "test_msg")
        for name, app_ in self.swift._apps.items():
            self.assertEqual(len(APP_INFOS[name].channel), app_.received.emit.call_count)

    def test_parse_args_primitive(self):
        def call_for_test(
            arg_number: float,
            arg_bool: bool,
            arg_null: Any,
            arg_string: str
        ):  # pylint: disable=unused-argument
            """A dummy function for testing, which has only primitive type arguments."""
        args = {"arg_number": 1.5, "arg_bool": True, "arg_null": None, "arg_string": "abc"}
        parsed_args = self.swift._parseArgs(call_for_test, args)
        self.assertEqual(args, parsed_args)

    def test_parse_args_serializable(self):
        @dataclasses.dataclass
        class ClassForTest(swift.Serializable):
            field_number: float
            field_bool: bool
            field_null: None
            field_string: str
        def call_for_test(arg1: ClassForTest, arg2: ClassForTest):  # pylint: disable=unused-argument
            """A dummy function for testing, which has only Serializable type arguments."""
        fields1 = {
            "field_number": 1.5,
            "field_bool": True,
            "field_null": None,
            "field_string": "abc",
        }
        fields2 = {
            "field_number": 0,
            "field_bool": False,
            "field_null": None,
            "field_string": "",
        }
        args = {"arg1": ClassForTest(**fields1), "arg2": ClassForTest(**fields2)}
        json_args = {"arg1": json.dumps(fields1), "arg2": json.dumps(fields2)}
        parsed_args = self.swift._parseArgs(call_for_test, json_args)
        self.assertEqual(args, parsed_args)


class HandleSwiftcallTest(unittest.TestCase):
    """Unit test for Swift._handleSwiftcall()."""

    def setUp(self):
        self.swift = swift.Swift()
        self.args = {
            "a": 1.5,
            "b": None,
        }
        self.call = swift.SwiftcallInfo(call="callForTest", args=self.args)
        self.msg = json.dumps(dataclasses.asdict(self.call))
        self.swift.callForTest = MagicMock()
        self.swift._parseArgs = MagicMock(return_value=self.args)
        QMessageBox.warning = MagicMock(return_value=QMessageBox.Ok)
        self._stashed_swift_loads = swift.loads
        swift.loads = MagicMock(return_value=self.call)

    def doCleanups(self):
        swift.loads = self._stashed_swift_loads

    def test_ok(self):
        self.swift._handleSwiftcall(sender="sender", msg=self.msg)
        self.swift.callForTest.assert_called_once_with(**self.args)

    def test_cancel(self):
        QMessageBox.warning.return_value = QMessageBox.Cancel
        with self.assertRaises(RuntimeError):
            self.swift._handleSwiftcall(sender="sender", msg=self.msg)
        self.swift.callForTest.assert_not_called()

    def test_non_public(self):
        self.call.call = "_callForTest"
        self.msg = json.dumps(dataclasses.asdict(self.call))
        self.swift._callForTest = MagicMock()
        with self.assertRaises(ValueError):
            self.swift._handleSwiftcall(sender="sender", msg=self.msg)
        self.swift._callForTest.assert_not_called()


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

    def help_proxy(self, info: swift.SwiftcallInfo, args: Mapping[str, Any]):
        """Helper method for testing proxy.
        
        Args:
            info: SwiftcallInfo object for requesting a swiftcall.
            args: A keyword argument mapping for calling the proxy.
        """
        msg = swift.dumps(info)
        with patch.object(self.swiftcall, "results", {}):
            result = self.swiftcall.callForTest(**args)
            self.swiftcall.requested.emit.assert_called_once_with(msg)
            self.assertIs(result, self.swiftcall.results[msg])
            self.assertEqual(result, swift.SwiftcallResult(done=False, success=False))

    def test_proxy_primitive(self):
        """Tests a proxied swiftcall with primitive type arguments.
        
        This assumes that swift.dumps() works correctly.
        """
        args = {"number": 1.5, "boolean": True, "string": "abc"}
        info = swift.SwiftcallInfo(call="callForTest", args=args)
        self.help_proxy(info, args)

    def test_proxy_serializable(self):
        """Tests a proxied swiftcall with Serializable type arguments.
        
        This assumes that swift.dumps() works correctly.
        """
        @dataclasses.dataclass
        class ClassForTest(swift.Serializable):
            number: float
            boolean: bool
            string: str
        args = {
            "arg1": ClassForTest(number=1.5, boolean=True, string="abc"),
            "arg2": ClassForTest(number=0, boolean=False, string=""),
        }
        json_args = {name: swift.dumps(arg) for name, arg in args.items()}
        info = swift.SwiftcallInfo(call="callForTest", args=json_args)
        self.help_proxy(info, args)

    def test_proxy_duplicate(self):
        """Tests a duplicate proxied swiftcall.
        
        The new one should be accepted and the previous one should be discarded.
        This assuems that swift.dumps() works correctly.
        """
        args = {"a": 123}
        info = swift.SwiftcallInfo(call="callForTest", args=args)
        msg = swift.dumps(info)
        with patch.object(self.swiftcall, "results", {}):
            result1 = self.swiftcall.callForTest(**args)
            result2 = self.swiftcall.callForTest(**args)
            self.assertSequenceEqual(
                self.swiftcall.requested.emit.mock_calls,
                (call(msg), call(msg)),
            )
            self.assertIs(result2, self.swiftcall.results[msg])
            self.assertEqual(result2, swift.SwiftcallResult(done=False, success=False))
            self.assertEqual(result1, result2)

    def test_update_result_success(self):
        old_result = swift.SwiftcallResult(done=False, success=False)
        new_result = swift.SwiftcallResult(done=True, success=True, value=0)
        with patch.object(self.swiftcall, "results", {"request": old_result}):
            self.swiftcall.update_result("request", new_result)
            self.assertEqual(old_result, new_result)
            self.assertFalse(self.swiftcall.results)

    def test_update_result_error(self):
        old_result = swift.SwiftcallResult(done=False, success=False)
        new_result = swift.SwiftcallResult(done=True, success=False, error=RuntimeError("test"))
        with patch.object(self.swiftcall, "results", {"request": old_result}):
            self.swiftcall.update_result("request", new_result)
            self.assertEqual(old_result, new_result)
            self.assertFalse(self.swiftcall.results)

    def test_update_result_no_discard(self):
        old_result = swift.SwiftcallResult(done=False, success=False)
        new_result = swift.SwiftcallResult(done=True, success=True, value=0)
        with patch.object(self.swiftcall, "results", {"request": old_result}):
            self.swiftcall.update_result("request", new_result, discard=False)
            self.assertEqual(old_result, new_result)
            self.assertIs(old_result, self.swiftcall.results["request"])


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
    @patch("swift.QApplication")
    def test_main(self, mock_qapp, mock_swift, mock_read_setup_file, mock_get_argparser):
        swift.main()
        mock_get_argparser.assert_called_once()
        mock_read_setup_file.assert_called_once()
        mock_swift.assert_called_once()
        mock_qapp.return_value.exec_.assert_called_once()


if __name__ == "__main__":
    unittest.main()
