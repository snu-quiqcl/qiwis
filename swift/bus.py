"""
Module for bus features.
"""

from queue import Queue, SimpleQueue, Empty
from typing import Optional

from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

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

    def __init__(self, name: str, timeout: float = 1, parent: Optional[QObject] = None):
        """
        Args:
            name: Name of the bus for identification.
            timeout: See QueueConsumer.__init__().
            parent: Parent object.
        """
        super().__init__(parent=parent)
        self.name = name
        self._queue = SimpleQueue()  # message queue
        self._timeout = timeout
        self._consumer = None  # QueueConsumer
        self._thread = None

    def write(self, msg: str):
        """Puts a message into the queue.
        
        Args:
            msg: Given message string to put in the queue.
        """
        self._queue.put(msg)

    def start(self):
        """Creates a queue consumer thread and starts it.
        
        This can be called only if there is no queue consumer.
        """
        if self._consumer is not None:
            raise RuntimeError("queue consumer already exists.")
        self._consumer = QueueConsumer(self._queue, self._timeout)
        # move consumer to thread
        self._thread = QThread()
        self._consumer.moveToThread(self._thread)
        # signal connection
        self._thread.started.connect(self._consumer.run)
        self._thread.finished.connect(self._thread.deleteLater)
        self._consumer.finished.connect(self._thread.quit)
        self._consumer.finished.connect(self._thread.wait)
        self._consumer.finished.connect(self._consumer.deleteLater)
        self._consumer.finished.connect(self._clean_up)
        self._consumer.consumed.connect(self.received)
        # start the thread
        self._thread.start()

    def stop(self):
        """Stops the queue consumer thread.
        
        This can be called only if there is an active queue consumer thread.
        This method call does not guarantee the immediate termination of the
        thread. It may take a while depending on the `timeout` parameter.
        """
        if self._consumer is None or not self._consumer.isRunning():
            raise RuntimeError("There is no queue consumer to stop.")
        self._consumer.stop()

    @pyqtSlot()
    def _clean_up(self):
        """Cleans up after the thread is finished.
        
        This erases the reference of the queue consumer when its run() is done.
        """
        self._consumer = None


class QueueConsumer(QObject):
    """Threaded queue consumer.
    
    Signals:
        consumed(str): Emitted when an item is found and consumed from the queue.
        finished: Emitted when run() method finishes.
    """

    consumed = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, queue_: Queue, timeout: float = 1, parent: Optional[QObject] = None):
        """
        Args:
            queue_: A queue.Queue-like object which implements get() and Empty.
            timeout: Desired timeout for blocking queue reading, in seconds.
              This should not be None in order not to become uniterruptible.
            parent: Parent object.
        """
        super().__init__(parent=parent)
        self._queue = queue_
        self._timeout = timeout
        self._running = True

    def isRunning(self) -> bool:
        """Returns whether the consumer is running."""
        return self._running

    @pyqtSlot()
    def run(self):
        """Keeps consuming the items in the queue whenever there exist some.
        
        This method will be connected to QThread.started signal.
        Whenever it consumes an item, it emits `consumed` signal with the content.
        """
        while self._running:
            try:
                item = self._queue.get(block=True, timeout=self._timeout)
            except Empty:
                pass
            else:
                self.consumed.emit(item)
        self.finished.emit()

    def stop(self):
        """Stops the consuming thread.
        
        It may take a while for the thread to actually stop, depending on
          the timeout parameter.
        """
        self._running = False
