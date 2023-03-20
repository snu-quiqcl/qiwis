"""
Module for testing swift package.
"""

import unittest
from collections.abc import Iterable

from swift.app import BaseApp

class AppTest(unittest.TestCase):
    """Unit test for app.py."""

    def setUp(self):
        """Create an app every time."""
        self.app = BaseApp("name")

    def test_frames(self):
        """Test BaseApp.frames()."""
        self.assertIsInstance(self.app.frames(), Iterable)


if __name__ == "__main__":
    unittest.main()
