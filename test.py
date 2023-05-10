"""
Module for testing swift module.
"""

import dataclasses
import sys
import importlib
import json
import unittest
from unittest import mock
from collections.abc import Iterable
from typing import Any, Optional, Mapping, Iterable

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


class SwiftTestWithApps(unittest.TestCase):
    """Unit test for Swift class with creating apps."""

    def setUp(self):
        self.import_module_patcher = mock.patch("importlib.import_module")
        self.mocked_import_module = self.import_module_patcher.start()
        for appInfo in APP_INFOS.values():
            app_ = mock.MagicMock()
            app_.cls = appInfo.cls
            app_.frames.return_value = (QWidget(),)
            cls = mock.MagicMock(return_value=app_)
            setattr(self.mocked_import_module.return_value, appInfo.cls, cls)
        self.channels = set()
        for appInfo in APP_INFOS.values():
            self.channels.update(appInfo.channel)
        self.swift = swift.Swift(APP_INFOS)
    
    def doCleanups(self):
        self.import_module_patcher.stop()

    def test_init(self):
        self.assertEqual(self.swift.appInfos, APP_INFOS)
        for name, info in APP_INFOS.items():
            self.mocked_import_module.assert_any_call(info.module)
            self.assertEqual(self.swift._apps[name].cls, info.cls)
            self.assertIn(name, self.swift._dockWidgets)
        for channel in self.channels:
            self.assertIn(channel, self.swift._subscribers)

    def test_app_names(self):
        appNamesSet = set(self.swift.appNames())
        self.assertEqual(appNamesSet, set(APP_INFOS))

    def test_create_app(self):
        app_ = mock.MagicMock()
        app_.cls = "cls3"
        app_.frames.return_value = (QWidget(),)
        cls = mock.MagicMock(return_value=app_)
        setattr(self.mocked_import_module.return_value, "cls3", cls)
        self.swift.createApp(
            "app3",
            swift.AppInfo(**{"module": "module3", "cls": "cls3", "channel": ["ch1"]})
        )
        self.mocked_import_module.assert_called_with("module3")
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

    def test_broadcast(self):
        for channelName in self.channels:
            self.swift._broadcast(channelName, "test_msg")
        for name, app_ in self.swift._apps.items():
            self.assertEqual(len(APP_INFOS[name].channel), app_.received.emit.call_count)


class SwiftTestWithoutApps(unittest.TestCase):
    """Unit test for Swift class without apps."""

    def setUp(self):
        self.swift = swift.Swift()

    def help_swiftcall(
        self,
        value: Any,
        result_string: str,
        error: Optional[Exception] = None,
        dumps: Iterable = (),
    ):
        """Helper method for testing _swiftcall().
        
        Args:
            value: The actual return value of the swift-call.
            result_string: The swift.dumps()-ed string of the result object that should be
              generated after the swift-call.
            error: The Exception instance that should have occurred during the swift-call.
              None if no exception is expected.
            dumps: A sequence of return values of the mocked swift.dumps().
              It will be given as side_effect. Moreover, the number of calls of
              swift.dumps() should be the same as the lenght of the given iterable.
        """
        msg = json.dumps({"call": "callForTest", "args": {}})
        with mock.patch.multiple(self.swift, _handleSwiftcall=mock.DEFAULT, _apps=mock.DEFAULT):
            if error is None:
                self.swift._handleSwiftcall.return_value = value
            else:
                self.swift._handleSwiftcall.side_effect = error
            with mock.patch("swift.dumps") as mocked_dumps:
                mocked_dumps.side_effect = dumps
                self.swift._swiftcall(sender="sender", msg=msg)
                self.assertEqual(len(mocked_dumps.mock_calls), len(dumps))
            mocked_signal = self.swift._apps["sender"].swiftcallReturned
            mocked_signal.emit.assert_called_once_with(msg, result_string)

    def test_swiftcall_primitive(self):
        """The swiftcall returns a primitive type value, which can be JSONified."""
        value = [1.5, True, None, "abc"]
        result_string = json.dumps({"done": True, "success": True, "value": value, "error": None})
        dumps = (result_string,)
        self.help_swiftcall(value, result_string, dumps=dumps)

    def test_swiftcall_serializable(self):
        """The swiftcall returns a Serializable type value."""
        @dataclasses.dataclass
        class ClassForTest(swift.Serializable):
            a: str
        value = ClassForTest(a="abc")
        value_string = json.dumps({"a": "abc"})
        result = swift.SwiftcallResult(done=True, success=True, value=value_string)
        result_string = json.dumps({
            "done": True,
            "success": True,
            "value": value_string,
            "error": None,
        })
        dumps = (value_string, result_string)
        self.help_swiftcall(value, result_string, dumps=dumps)

    def test_swiftcall_exception(self):
        """The swiftcall raises an exception."""
        class ExceptionForTest(Exception):
            """Temporary exception only for this test."""
        error = ExceptionForTest("test")
        result_string = json.dumps({
            "done": True,
            "success": False,
            "value": None,
            "error": repr(error),
        })
        dumps = (result_string,)
        self.help_swiftcall(None, result_string, error, dumps=dumps)

    def test_parse_args_primitive(self):
        def call_for_test(number: float, boolean: bool, string: str):  # pylint: disable=unused-argument
            """A dummy function for testing, which has only primitive type arguments."""
        args = {"number": 1.5, "boolean": True, "string": "abc"}
        parsed_args = self.swift._parseArgs(call_for_test, args)
        self.assertEqual(args, parsed_args)

    def test_parse_args_serializable(self):
        @dataclasses.dataclass
        class ClassForTest(swift.Serializable):
            number: float
            boolean: bool
            string: str
        def call_for_test(arg1: ClassForTest, arg2: ClassForTest):  # pylint: disable=unused-argument
            """A dummy function for testing, which has only Serializable type arguments."""
        fields1 = {
            "number": 1.5,
            "boolean": True,
            "string": "abc",
        }
        fields2 = {
            "number": 0,
            "boolean": False,
            "string": "",
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
        self.swift.callForTest = mock.MagicMock()
        self.swift._parseArgs = mock.MagicMock(return_value=self.args)
        QMessageBox.warning = mock.MagicMock(return_value=QMessageBox.Ok)
        self._stashed_swift_loads = swift.loads
        swift.loads = mock.MagicMock(return_value=self.call)

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
        self.swift._callForTest = mock.MagicMock()
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
        self.app.broadcastRequested = mock.MagicMock()
        self.app.broadcast("ch1", "msg")
        self.app.broadcastRequested.emit.assert_called_once_with("ch1", '"msg"')

    def test_broadcast_exception(self):
        self.app.broadcastRequested = mock.MagicMock()
        self.app.broadcast("ch1", lambda: None)
        self.app.broadcastRequested.emit.assert_not_called()

    def test_received_message(self):
        self.app.receivedSlot = mock.MagicMock()
        self.app._receivedMessage("ch1", '"msg"')
        self.app.receivedSlot.assert_called_once_with("ch1", "msg")

    def test_received_message_exception(self):
        self.app.receivedSlot = mock.MagicMock()
        self.app._receivedMessage("ch1", '"msg1" "msg2"')
        self.app.receivedSlot.assert_not_called()

    def test_received_swiftcall_result(self):
        self.app.swiftcall.update_result = mock.MagicMock()
        self.app._receivedSwiftcallResult(
            "request", '{"done": true, "success": true, "value": null, "error": null}'
        )
        self.app.swiftcall.update_result.assert_called_once_with(
            "request",
            swift.SwiftcallResult(done=True, success=True)
        )

    def test_received_swiftcall_result_exception(self):
        self.app.swiftcall.update_result = mock.MagicMock()
        self.app._receivedSwiftcallResult(
            "request", '{"done": "tr" "ue", "success": true, "value": null, "error": null}'
        )
        self.app.swiftcall.update_result.assert_not_called()


class SwiftcallProxyTest(unittest.TestCase):
    """Unit test for SwiftcallProxy class."""

    def setUp(self):
        self.swiftcall = swift.SwiftcallProxy(mock.MagicMock())

    def help_proxy(self, msg: str, args: Mapping[str, Any], dumps: Iterable):
        """Helper method for testing proxy.
        
        Args:
            msg: The swift-call request message.
            args: A keyword argument mapping for calling the proxy.
            dumps: Expected return values of swift.dumps() during the proxied swift-call.
              It will be given as side_effect. The number of calls should be the same as
              the length of the given iterable.
        """
        with mock.patch.object(self.swiftcall, "results", {}):
            with mock.patch("swift.dumps") as mocked_dumps:
                mocked_dumps.side_effect = dumps
                result = self.swiftcall.callForTest(**args)
                self.assertEqual(len(mocked_dumps.mock_calls), len(dumps))
            self.swiftcall.requested.emit.assert_called_once_with(msg)
            self.assertIs(result, self.swiftcall.results[msg])
            self.assertEqual(result, swift.SwiftcallResult(done=False, success=False))

    def test_proxy_primitive(self):
        """Tests a proxied swiftcall with primitive type arguments."""
        args = {"number": 1.5, "boolean": True, "string": "abc"}
        msg = json.dumps({"call": "callForTest", "args": args})
        dumps = (msg,)
        self.help_proxy(msg, args, dumps)

    def test_proxy_serializable(self):
        """Tests a proxied swiftcall with Serializable type arguments."""
        @dataclasses.dataclass
        class ClassForTest(swift.Serializable):
            number: float
            boolean: bool
            string: str
        args = {
            "arg1": ClassForTest(number=1.5, boolean=True, string="abc"),
            "arg2": ClassForTest(number=0, boolean=False, string=""),
        }
        json_args = {
            "arg1": json.dumps({"number": 1.5, "boolean": True, "string": "abc"}),
            "arg2": json.dumps({"number": 0, "boolean": False, "string": ""}),
        }
        msg = json.dumps({"call": "callForTest", "args": json_args})
        dumps = (json_args["arg1"], json_args["arg2"], msg)
        self.help_proxy(msg, args, dumps)

    def test_proxy_duplicate(self):
        """Tests a duplicate proxied swiftcall.
        
        The new one should be accepted and the previous one should be discarded.
        This assuems that swift.dumps() works correctly.
        """
        args = {"a": 123}
        msg = json.dumps({"call": "callForTest", "args": args})
        with mock.patch.object(self.swiftcall, "results", {}):
            result1 = self.swiftcall.callForTest(**args)
            result2 = self.swiftcall.callForTest(**args)
            self.assertSequenceEqual(
                self.swiftcall.requested.emit.mock_calls,
                (mock.call(msg), mock.call(msg)),
            )
            self.assertIs(result2, self.swiftcall.results[msg])
            self.assertEqual(result2, swift.SwiftcallResult(done=False, success=False))
            self.assertEqual(result1, result2)

    def test_update_result_success(self):
        old_result = swift.SwiftcallResult(done=False, success=False)
        new_result = swift.SwiftcallResult(done=True, success=True, value=0)
        with mock.patch.object(self.swiftcall, "results", {"request": old_result}):
            self.swiftcall.update_result("request", new_result)
            self.assertEqual(old_result, new_result)
            self.assertNotIn("request", self.swiftcall.results)

    def test_update_result_error(self):
        old_result = swift.SwiftcallResult(done=False, success=False)
        new_result = swift.SwiftcallResult(done=True, success=False, error=RuntimeError("test"))
        with mock.patch.object(self.swiftcall, "results", {"request": old_result}):
            self.swiftcall.update_result("request", new_result)
            self.assertEqual(old_result, new_result)
            self.assertNotIn("request", self.swiftcall.results)

    def test_update_result_no_discard(self):
        old_result = swift.SwiftcallResult(done=False, success=False)
        new_result = swift.SwiftcallResult(done=True, success=True, value=0)
        with mock.patch.object(self.swiftcall, "results", {"request": old_result}):
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

    @mock.patch.object(sys, "argv", ["", "-s", "test_setup.json"])
    def test_get_argparser(self):
        parser = swift._get_argparser()
        args = parser.parse_args()
        self.assertEqual(args.setup_path, "test_setup.json")

    @mock.patch.object(sys, "argv", [""])
    def test_get_argparser_default(self):
        args = swift._get_argparser().parse_args()
        self.assertEqual(args.setup_path, "./setup.json")

    @mock.patch("builtins.open")
    @mock.patch("json.load", return_value={"app": APP_DICTS})
    def test_read_setup_file(self, mock_load, mock_open):
        self.assertEqual(swift._read_setup_file(""), APP_INFOS)
        mock_open.assert_called_once()
        mock_load.assert_called_once()

    @mock.patch("swift._get_argparser")
    @mock.patch("swift._read_setup_file", return_value={})
    @mock.patch("swift.Swift")
    @mock.patch("swift.QApplication")
    def test_main(self, mock_qapp, mock_swift, mock_read_setup_file, mock_get_argparser):
        swift.main()
        mock_get_argparser.assert_called_once()
        mock_read_setup_file.assert_called_once()
        mock_swift.assert_called_once()
        mock_qapp.return_value.exec_.assert_called_once()


if __name__ == "__main__":
    unittest.main()
