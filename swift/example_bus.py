"""Example bus module for testing Swift class.
"""

from collections import deque

from PyQt5.QtCore import QObject, pyqtSignal


class BaseBus(QObject):
    """Base Bus class.
    """

    received = pyqtSignal(str)

    def __init__(self, name: str):
        QObject.__init__(self)
        self.name = name
        self.queue = deque()

    def write(self, msg: str):
        """Push an input message in the queue.

        Args:
            msg (str): An input message to transfer through the global bus.
        """
        self.queue.append(msg)

    def pub(self):
        """Public method for meeting Pylint condition.
        """


class ExampleBus(BaseBus):
    """Example bus class for testing Swift class.
    """


class AnotherExampleBus(BaseBus):
    """Another example bus class for testing Swift class.
    """
