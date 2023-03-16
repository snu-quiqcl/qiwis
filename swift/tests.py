import unittest
from collections.abc import Iterable

from swift.app import BaseApp

class AppTest(unittest.TestCase):
    def setUp(self):
        self.app = BaseApp("name")

    def test_frames(self):
        self.assertIsInstance(self.app.frames(), Iterable)


if __name__ == "__main__":
    unittest.main()
