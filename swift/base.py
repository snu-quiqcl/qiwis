"""Base module for Logic.

Every Logic class should be a subclass of BaseLogic.
"""

from PyQt5.QtCore import QObject, pyqtSignal


class BaseLogic(QObject):
    """Base Logic class that all Logics should inherit.

    Signals: 
        broadcastRequested(str, str): A signal for broadcasting to a bus 
            which contains the destination bus name and the message.
        received(str, str): A signal for receiving a global signal from a bus
            which contains the departure bus name and the message.
    """
    
    broadcastRequested = pyqtSignal(str, str)
    received = pyqtSignal(str, str)

    def __init__(self, name: str, show: bool, pos: str):
        """Constructor.

        Args:
            name: A string that indicates the name of Logic.
            show: Whether Frames are shown at the beginning.
            pos: An initial position of Frames.
                It should be one of "left", "right", "top", or "bottom"; and is case-insensitive.
                Otherwise, it will be regarded as default (AllDockWidgetAreas).
        """
        super().__init__(self)
        self.name = name
        self.show = show
        self.pos = pos

    def frames(self):
        """Get frames for which are managed by the Logic.

        Returns:
            Iterable: an iterable object of Frame objects for showing
        """
        return ()
