"""
Module for bus features.
"""

from queue import SimpleQueue

from PyQt5.QtCore import QObject, pyqtSignal

class Bus(QObject):
    """Communication channel for frame logic instances in swift.

    Attributes:
        name: A string that indicates the name of the bus for identification.
    
    Signals:
        received(str): Emitted when a message is fetched from the queue.
          Its argument is the fetched message and this signal implies that
          the message is consumed, i.e., removed from the queue.
    """

    received = pyqtSignal(str)

    def __init__(self, name: str):
        """
        Args:
            name: Name of the bus for identification.
        """
        super().__init__()
        self.name = name
        self._queue = SimpleQueue()  # message queue
    
    def write(self, msg: str):
        """Puts a message into the queue.
        
        Args:
            msg: Given message string to put in the queue.
        """
        self._queue.put(msg)


class QueueConsumer(QObject):
    """Threaded queue consumer.
    
    Signals:
        consumed: Emitted when an item is found and consumed from the queue.
    """

    consumed = pyqtSignal()

    def __init__(self, queue_):
        """
        Args:
            queue_: A thread-safe queue object which implements `get()` method.
        """
        super().__init__()
        self._queue = queue_
