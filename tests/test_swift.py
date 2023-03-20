"""
Module for testing swift package.
"""

import unittest
from collections.abc import Iterable

from PyQt5.QtCore import QObject

from swift.app import BaseApp

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


if __name__ == "__main__":
    unittest.main()
