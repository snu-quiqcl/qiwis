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
        consumed(str): Emitted when an item is found and consumed from the queue.
        finished: Emitted when run() method finishes.
    """

    consumed = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, queue_, timeout=1):
        """
        Args:
            queue_: A queue.Queue-like object which implements get() and Empty.
            timeout: Desired timeout for blocking queue reading, in seconds.
              This should not be None in order not to become uniterruptible.
        """
        super().__init__()
        self._queue = queue_
        self._timeout = timeout
