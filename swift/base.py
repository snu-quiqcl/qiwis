"""Base module for Logic.

Every Logic class should be a subclass of BaseLogic.
"""

from PyQt5.QtCore import QObject, pyqtSignal


class BaseLogic(QObject):
    """Base Logic class.
    """

    # Signal for broadcasting to a bus
    # which contains the destination bus name and the message.
    broadcast = pyqtSignal(str, str)
    # Signal for receiving a global signal from a bus
    # which contains the departure bus name and the message.
    received = pyqtSignal(str, str)

    def __init__(self, name: str, show: bool, pos: str):
        """Constructor.

        Args:
            name (str): A name of Logic.
            show (bool): Whether Frames are shown at the beginning.
            pos (str): An initial position of Frames.
        """
        QObject.__init__(self)
        self.name = name
        self.show = show
        self.pos = pos

    def frames(self):
        """Get frames for which are managed by the Logic.

        Returns:
            Iterable: an iterable object of Frame objects for showing
        """
