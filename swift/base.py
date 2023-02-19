"""Base module for Frame and Logic.

Every Frame and Logic class should be a subclass of BaseFrame and BaseLogic, repectively.
"""

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot


class BaseFrame:
    """Base Frame class 
    """


class BaseLogic(QObject):
    """Base Logic class.
    """

    # Signal for broadcasting to buses to which Logic subscribes.
    broadcast_signal = pyqtSignal(str)

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

    @pyqtSlot(str)
    def receive_bus_signal(self, msg: str):
        """Receive a message which be transferred through the global bus.

        Args:
            msg (str): An input message that be transferred through the global bus.
        """