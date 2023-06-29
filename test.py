"""
Module for testing qiwis module.
"""

import collections.abc
import dataclasses
import sys
import json
import unittest
from unittest import mock
from types import MappingProxyType
from typing import Any, Optional, Mapping, Iterable

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QApplication, QMessageBox, QWidget

import qiwis

APP_INFOS = {
    "app1": qiwis.AppInfo(
        module="module1",
        cls="cls1",
        path="path1",
        show=False,
        pos="left",
        channel=["ch1", "ch2"],
        args={"arg1": "value1"}
    ),
    "app2": qiwis.AppInfo(
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


class QiwisTestWithApps(unittest.TestCase):
    """Unit test for Qiwis class with creating apps."""

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
        self.qiwis = qiwis.Qiwis(APP_INFOS)

    def doCleanups(self):
        self.import_module_patcher.stop()

    def test_init(self):
        self.assertEqual(self.qiwis.appInfos, APP_INFOS)
        for name, info in APP_INFOS.items():
            self.mocked_import_module.assert_any_call(info.module)
            self.assertEqual(self.qiwis._apps[name].cls, info.cls)
            self.assertIn(name, self.qiwis._dockWidgets)
        for channel in self.channels:
            self.assertIn(channel, self.qiwis._subscribers)

    def test_app_names(self):
        appNamesSet = set(self.qiwis.appNames())
        self.assertEqual(appNamesSet, set(APP_INFOS))

    def test_create_app(self):
        app_ = mock.MagicMock()
        app_.cls = "cls3"
        app_.frames.return_value = (QWidget(),)
        cls = mock.MagicMock(return_value=app_)
        setattr(self.mocked_import_module.return_value, "cls3", cls)
        self.qiwis.createApp(
            "app3",
            qiwis.AppInfo(**{"module": "module3", "cls": "cls3", "channel": ["ch1"]})
        )
        self.mocked_import_module.assert_called_with("module3")
        self.assertEqual(self.qiwis._apps["app3"].cls, "cls3")
        self.assertIn("app3", self.qiwis._dockWidgets)
        self.assertIn("app3", self.qiwis._subscribers["ch1"])

    def test_destroy_app(self):
        for name, info in APP_INFOS.items():
            self.qiwis.destroyApp(name)
            self.assertNotIn(name, self.qiwis._apps)
            self.assertNotIn(name, self.qiwis._dockWidgets)
            for channel in info.channel:
                self.assertNotIn(name, self.qiwis._subscribers[channel])

    def test_update_frames_inclusive(self):
        """Tests for the case where a new frame is added in the return of frames()."""
        orgFramesSet = {dockWidget.widget() for dockWidget in self.qiwis._dockWidgets["app1"]}
        newFramesSet = orgFramesSet | {QWidget()}
        self.qiwis._apps["app1"].frames.return_value = tuple(newFramesSet)
        self.qiwis.updateFrames("app1")
        finalFramesSet = {dockWidget.widget() for dockWidget in self.qiwis._dockWidgets["app1"]}
        self.assertEqual(finalFramesSet, newFramesSet)

    def test_update_frames_exclusive(self):
        """Tests for the case where a new frame replaced the return of frames()."""
        orgFramesSet = {dockWidget.widget() for dockWidget in self.qiwis._dockWidgets["app1"]}
        newFramesSet = {QWidget()}
        self.qiwis._apps["app1"].frames.return_value = tuple(newFramesSet)
        self.qiwis.updateFrames("app1")
        finalFramesSet = {dockWidget.widget() for dockWidget in self.qiwis._dockWidgets["app1"]}
        self.assertFalse(finalFramesSet & orgFramesSet)
        self.assertEqual(finalFramesSet, newFramesSet)

    def test_channel_names(self):
        channelNamesSet = set(self.qiwis.channelNames())
        self.assertEqual(channelNamesSet, self.channels)

    def test_subscriber_names(self):
        for channel in self.channels:
            subscriberNamesSet = set(self.qiwis.subscriberNames(channel))
            self.assertEqual(
                subscriberNamesSet,
                {name for name, info in APP_INFOS.items() if channel in info.channel}
            )

    def test_unsubcribe(self):
        self.assertEqual(self.qiwis.unsubscribe("app1", "ch1"), True)
        self.assertNotIn("app1", self.qiwis._subscribers["ch1"])
        self.assertEqual(self.qiwis.unsubscribe("app2", "ch1"), False)

    def test_broadcast(self):
        for channelName in self.channels:
            self.qiwis._broadcast(channelName, "test_msg")
        for name, app_ in self.qiwis._apps.items():
            self.assertEqual(len(APP_INFOS[name].channel), app_.received.emit.call_count)


class QiwisTestWithoutApps(unittest.TestCase):
    """Unit test for Qiwis class without apps."""

    def setUp(self):
        self.qiwis = qiwis.Qiwis()

    def help_qiwiscall(
        self,
        value: Any,
        result_string: str,
        error: Optional[Exception] = None,
        dumps: Iterable = (),
    ):
        """Helper method for testing _qiwiscall().
        
        Args:
            value: The actual return value of the qiwiscall.
            result_string: The qiwis.dumps()-ed string of the result object that should be
              generated after the qiwiscall.
            error: The Exception instance that should have occurred during the qiwiscall.
              None if no exception is expected.
            dumps: A sequence of return values of the mocked qiwis.dumps().
              It will be given as side_effect. Moreover, the number of calls of
              qiwis.dumps() should be the same as the lenght of the given iterable.
        """
        msg = json.dumps({"call": "callForTest", "args": {}})
        with mock.patch.multiple(self.qiwis, _handleQiwiscall=mock.DEFAULT, _apps=mock.DEFAULT):
            if error is None:
                self.qiwis._handleQiwiscall.return_value = value
            else:
                self.qiwis._handleQiwiscall.side_effect = error
            with mock.patch("qiwis.dumps") as mocked_dumps:
                mocked_dumps.side_effect = dumps
                self.qiwis._qiwiscall(sender="sender", msg=msg)
                self.assertEqual(len(mocked_dumps.mock_calls), len(dumps))
            mocked_signal = self.qiwis._apps["sender"].qiwiscallReturned
            mocked_signal.emit.assert_called_once_with(msg, result_string)

    def test_qiwiscall_primitive(self):
        """The qiwiscall returns a primitive type value, which can be JSONified."""
        value = [1.5, True, None, "abc"]
        result_string = json.dumps({"done": True, "success": True, "value": value, "error": None})
        dumps = (result_string,)
        self.help_qiwiscall(value, result_string, dumps=dumps)

    def test_qiwiscall_serializable(self):
        """The qiwiscall returns a Serializable type value."""
        @dataclasses.dataclass
        class ClassForTest(qiwis.Serializable):
            a: str
        value = ClassForTest(a="abc")
        value_string = json.dumps({"a": "abc"})
        result_string = json.dumps({
            "done": True,
            "success": True,
            "value": value_string,
            "error": None,
        })
        dumps = (value_string, result_string)
        self.help_qiwiscall(value, result_string, dumps=dumps)

    def test_qiwiscall_exception(self):
        """The qiwiscall raises an exception."""
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
        self.help_qiwiscall(None, result_string, error, dumps=dumps)

    def test_parse_args_primitive(self):
        def call_for_test(number: float, boolean: bool, string: str):  # pylint: disable=unused-argument
            """A dummy function for testing, which has only primitive type arguments."""
        args = {"number": 1.5, "boolean": True, "string": "abc"}
        parsed_args = self.qiwis._parseArgs(call_for_test, args)
        self.assertEqual(args, parsed_args)

    def test_parse_args_serializable(self):
        @dataclasses.dataclass
        class ClassForTest(qiwis.Serializable):
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
        parsed_args = self.qiwis._parseArgs(call_for_test, json_args)
        self.assertEqual(args, parsed_args)

@mock.patch("qiwis.loads")
@mock.patch("qiwis.QMessageBox.warning")
class HandleQiwiscallTest(unittest.TestCase):
    """Unit test for Qiwis._handleQiwiscall()."""

    def setUp(self):
        self.qiwis = qiwis.Qiwis()

    def test_ok(self, mocked_warning, mocked_loads):
        args = {"a": 123, "b": "ABC"}
        info = qiwis.QiwiscallInfo(call="callForTest", args=args)
        msg = json.dumps({"call": "callForTest", "args": args})
        mocked_loads.return_value = info
        mocked_warning.return_value = QMessageBox.Ok
        with mock.patch.multiple(self.qiwis, create=True,
                                 callForTest=mock.DEFAULT, _parseArgs=mock.DEFAULT):
            self.qiwis._parseArgs.return_value = args
            self.qiwis._handleQiwiscall(sender="sender", msg=msg)
            self.qiwis.callForTest.assert_called_once_with(**args)
            self.qiwis._parseArgs.assert_called_once_with(self.qiwis.callForTest, args)
        mocked_loads.assert_called_once()
        mocked_warning.assert_called_once()

    def test_cancel(self, mocked_warning, mocked_loads):
        args = {"a": 123, "b": "ABC"}
        info = qiwis.QiwiscallInfo(call="callForTest", args=args)
        msg = json.dumps({"call": "callForTest", "args": args})
        mocked_loads.return_value = info
        mocked_warning.return_value = QMessageBox.Cancel
        with mock.patch.multiple(self.qiwis, create=True,
                                 callForTest=mock.DEFAULT, _parseArgs=mock.DEFAULT):
            self.qiwis._parseArgs.return_value = args
            with self.assertRaises(RuntimeError):
                self.qiwis._handleQiwiscall(sender="sender", msg=msg)
            self.qiwis.callForTest.assert_not_called()
            self.qiwis._parseArgs.assert_called_once_with(self.qiwis.callForTest, args)
        mocked_loads.assert_called_once()
        mocked_warning.assert_called_once()

    def test_non_public(self, mocked_warning, mocked_loads):
        args = {"a": 123, "b": "ABC"}
        info = qiwis.QiwiscallInfo(call="_callForTest", args=args)
        msg = json.dumps({"call": "_callForTest", "args": args})
        mocked_loads.return_value = info
        with mock.patch.multiple(self.qiwis, create=True,
                                 _callForTest=mock.DEFAULT, _parseArgs=mock.DEFAULT):
            with self.assertRaises(ValueError):
                self.qiwis._handleQiwiscall(sender="sender", msg=msg)
            self.qiwis._callForTest.assert_not_called()
            self.qiwis._parseArgs.assert_not_called()
        mocked_loads.assert_called_once()
        mocked_warning.assert_not_called()

    def test_not_existing_method(self, mocked_warning, mocked_loads):
        args = {"a": 123, "b": "ABC"}
        info = qiwis.QiwiscallInfo(call="callForTest", args=args)
        msg = json.dumps({"call": "callForTest", "args": args})
        mocked_loads.return_value = info
        with mock.patch.multiple(self.qiwis, create=True, _parseArgs=mock.DEFAULT):
            with self.assertRaises(AttributeError):
                self.qiwis._handleQiwiscall(sender="sender", msg=msg)
            self.qiwis._parseArgs.assert_not_called()
        mocked_loads.assert_called_once()
        mocked_warning.assert_not_called()


class BaseAppTest(unittest.TestCase):
    """Unit test for BaseApp class."""

    def setUp(self):
        self.app = qiwis.BaseApp("name")

    def test_init(self):
        self.assertEqual(self.app.name, "name")

    def test_set_parent(self):
        qiwis.BaseApp("name", QObject())

    def test_constants_default(self):
        self.assertFalse(self.app.constants._fields)

    @mock.patch("qiwis.BaseApp._constants")
    def test_constants(self, mocked_constants):
        self.assertIs(self.app.constants, mocked_constants)

    def test_frames(self):
        self.assertIsInstance(self.app.frames(), collections.abc.Iterable)

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

    def test_received_qiwiscall_result(self):
        self.app.qiwiscall.update_result = mock.MagicMock()
        self.app._receivedQiwiscallResult(
            "request", '{"done": true, "success": true, "value": null, "error": null}'
        )
        self.app.qiwiscall.update_result.assert_called_once_with(
            "request",
            qiwis.QiwiscallResult(done=True, success=True)
        )

    def test_received_qiwiscall_result_exception(self):
        self.app.qiwiscall.update_result = mock.MagicMock()
        self.app._receivedQiwiscallResult(
            "request", '{"done": "tr" "ue", "success": true, "value": null, "error": null}'
        )
        self.app.qiwiscall.update_result.assert_not_called()


class QiwiscallProxyTest(unittest.TestCase):
    """Unit test for QiwiscallProxy class."""

    def setUp(self):
        self.qiwiscall = qiwis.QiwiscallProxy(mock.MagicMock())

    def help_proxy(self, msg: str, args: Mapping[str, Any], dumps: Iterable):
        """Helper method for testing proxy.
        
        Args:
            msg: The qiwiscall request message.
            args: A keyword argument mapping for calling the proxy.
            dumps: Expected return values of qiwis.dumps() during the proxied qiwiscall.
              It will be given as side_effect. The number of calls should be the same as
              the length of the given iterable.
        """
        with mock.patch.object(self.qiwiscall, "results", {}):
            with mock.patch("qiwis.dumps") as mocked_dumps:
                mocked_dumps.side_effect = dumps
                result = self.qiwiscall.callForTest(**args)
                self.assertEqual(len(mocked_dumps.mock_calls), len(dumps))
            self.qiwiscall.requested.emit.assert_called_once_with(msg)
            self.assertIs(result, self.qiwiscall.results[msg])
            self.assertEqual(result, qiwis.QiwiscallResult(done=False, success=False))

    def test_proxy_primitive(self):
        """Tests a proxied qiwiscall with primitive type arguments."""
        args = {"number": 1.5, "boolean": True, "string": "abc"}
        msg = json.dumps({"call": "callForTest", "args": args})
        dumps = (msg,)
        self.help_proxy(msg, args, dumps)

    def test_proxy_serializable(self):
        """Tests a proxied qiwiscall with Serializable type arguments."""
        @dataclasses.dataclass
        class ClassForTest(qiwis.Serializable):
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
        """Tests a duplicate proxied qiwiscall.
        
        The new one should be accepted and the previous one should be discarded.
        """
        args = {"a": 123}
        msg = json.dumps({"call": "callForTest", "args": args})
        with mock.patch.object(self.qiwiscall, "results", {}):
            with mock.patch("qiwis.dumps") as mocked_dumps:
                mocked_dumps.side_effect = (msg, msg)
                result1 = self.qiwiscall.callForTest(**args)
                result2 = self.qiwiscall.callForTest(**args)
                self.assertEqual(len(mocked_dumps.mock_calls), 2)
            self.assertSequenceEqual(
                self.qiwiscall.requested.emit.mock_calls,
                (mock.call(msg), mock.call(msg)),
            )
            self.assertIs(result2, self.qiwiscall.results[msg])
            self.assertEqual(result2, qiwis.QiwiscallResult(done=False, success=False))
            self.assertEqual(result1, result2)

    def test_update_result_success(self):
        old_result = qiwis.QiwiscallResult(done=False, success=False)
        new_result = qiwis.QiwiscallResult(done=True, success=True, value=0)
        with mock.patch.object(self.qiwiscall, "results", {"request": old_result}):
            self.qiwiscall.update_result("request", new_result)
            self.assertEqual(old_result, new_result)
            self.assertNotIn("request", self.qiwiscall.results)

    def test_update_result_error(self):
        old_result = qiwis.QiwiscallResult(done=False, success=False)
        new_result = qiwis.QiwiscallResult(done=True, success=False, error=RuntimeError("test"))
        with mock.patch.object(self.qiwiscall, "results", {"request": old_result}):
            self.qiwiscall.update_result("request", new_result)
            self.assertEqual(old_result, new_result)
            self.assertNotIn("request", self.qiwiscall.results)

    def test_update_result_no_discard(self):
        old_result = qiwis.QiwiscallResult(done=False, success=False)
        new_result = qiwis.QiwiscallResult(done=True, success=True, value=0)
        with mock.patch.object(self.qiwiscall, "results", {"request": old_result}):
            self.qiwiscall.update_result("request", new_result, discard=False)
            self.assertEqual(old_result, new_result)
            self.assertIs(old_result, self.qiwiscall.results["request"])

    def test_update_result_not_exist(self):
        """When the request is not in the results dictionary, it is ignored."""
        new_result = qiwis.QiwiscallResult(done=True, success=True, value=0)
        with mock.patch.object(self.qiwiscall, "results", {}):
            self.qiwiscall.update_result("request", new_result)
            self.assertNotIn("request", self.qiwiscall.results)


class QiwisFunctionTest(unittest.TestCase):
    """Unit test for functions."""

    def test_loads(self):
        self.assertEqual(qiwis.loads(qiwis.AppInfo, APP_JSONS["app1"]), APP_INFOS["app1"])
        self.assertEqual(qiwis.loads(qiwis.AppInfo, APP_JSONS["app2_default"]), APP_INFOS["app2"])

    def test_dumps(self):
        self.assertEqual(qiwis.dumps(APP_INFOS["app1"]), APP_JSONS["app1"])
        self.assertEqual(qiwis.dumps(APP_INFOS["app2"]), APP_JSONS["app2"])

    @mock.patch("qiwis.namedtuple")
    @mock.patch("qiwis._immutable")
    @mock.patch("qiwis.BaseApp")
    def test_set_global_constant_namespace(
        self,
        mocked_base_app_cls,
        mocked_immutable,
        mocked_namedtuple
    ):
        source = {"C0": 0, "C1": True, "C2": "str"}
        mocked_immutable_values = ("M0", "M1", "M2")
        mocked_namespace = mocked_namedtuple.return_value
        mocked_constants = mocked_namespace.return_value
        mocked_immutable.side_effect = mocked_immutable_values
        constants = qiwis.set_global_constant_namespace(source)
        self.assertIs(constants, mocked_constants)
        self.assertIs(mocked_base_app_cls._constants, mocked_constants)
        mocked_namedtuple.assert_called_once_with("ConstantNamespace", source.keys())
        _args, _kwargs = mocked_namespace.call_args
        self.assertSequenceEqual(_args, mocked_immutable_values)
        mocked_immutable.assert_has_calls((mock.call(value) for value in source.values()))

    def test_immutable(self):
        sources = (
            None,
            0,
            True,
            "str",
            [None, 1.2, False, "test"],
            {"k1": 0, "k2": True},
        )
        results = (
            None,
            0,
            True,
            "str",
            (None, 1.2, False, "test"),
            MappingProxyType({"k1": 0, "k2": True}),
        )
        for source, result in zip(sources, results):
            self.assertEqual(qiwis._immutable(source), result)

    def test_immutable_recursive(self):
        source = {
            "LIST": [None, 0, True, "list"],
            "LIST_LIST": [0, [1, 2, [3, 4, 5]]],
            "DICT": {"A": True, "B": False},
            "DICT_DICT": {"A": 0, "B": {"C": 1, "D": 2}},
            "LIST_DICT": [0, {"A": 1, "B": [2, 3]}],
        }
        result = MappingProxyType({
            "LIST": (None, 0, True, "list"),
            "LIST_LIST": (0, (1, 2, (3, 4, 5))),
            "DICT": MappingProxyType({"A": True, "B": False}),
            "DICT_DICT": MappingProxyType({"A": 0, "B": MappingProxyType({"C": 1, "D": 2})}),
            "LIST_DICT": (0, MappingProxyType({"A": 1, "B": (2, 3)})),
        })
        self.assertEqual(qiwis._immutable(source), result)
        # when the root-type is list
        self.assertEqual(qiwis._immutable(source["LIST_DICT"]), result["LIST_DICT"])

    def test_add_to_path(self):
        test_dir = "/test_dir"
        old_path = sys.path.copy()
        with qiwis._add_to_path(test_dir):
            self.assertNotEqual(old_path, sys.path)
            self.assertIn(test_dir, sys.path)
        self.assertEqual(old_path, sys.path)

    @mock.patch.object(sys, "argv", ["", "-s", "test_setup.json"])
    def test_get_argparser(self):
        parser = qiwis._get_argparser()
        args = parser.parse_args()
        self.assertEqual(args.setup_path, "test_setup.json")

    @mock.patch.object(sys, "argv", [""])
    def test_get_argparser_default(self):
        args = qiwis._get_argparser().parse_args()
        self.assertEqual(args.setup_path, "./setup.json")

    @mock.patch("builtins.open")
    @mock.patch("json.load", return_value={"app": APP_DICTS, "constant": {"C0": 0}})
    def test_read_setup_file(self, mock_load, mock_open):
        app_infos, constants = qiwis._read_setup_file("")
        self.assertEqual(constants, {"C0": 0})
        self.assertEqual(app_infos, APP_INFOS)
        mock_open.assert_called_once()
        mock_load.assert_called_once()

    @mock.patch("qiwis.set_global_constant_namespace")
    @mock.patch("qiwis._get_argparser")
    @mock.patch("qiwis._read_setup_file", return_value=({}, {}))
    @mock.patch("qiwis.Qiwis")
    @mock.patch("qiwis.QApplication")
    def test_main(
        self,
        mock_qapp,
        mock_qiwis,
        mock_read_setup_file,
        mock_get_argparser,
        mock_set_global_constant_namespace,
    ):
        qiwis.main()
        mock_set_global_constant_namespace.assert_called_once()
        mock_get_argparser.assert_called_once()
        mock_read_setup_file.assert_called_once()
        mock_qiwis.assert_called_once()
        mock_qapp.return_value.exec_.assert_called_once()


if __name__ == "__main__":
    unittest.main()
