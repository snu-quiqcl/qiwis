"""
Base module for App.

Every App class should be a subclass of BaseApp.
"""

from PyQt5.QtCore import QObject, pyqtSignal

class BaseApp(QObject):
    """Base App class that all apps should inherit.

    Signals: 
        broadcastRequested(str, str): A signal for broadcasting to a bus 
          which contains the destination bus name and the message.
        received(str, str): A signal for receiving a global signal from a bus
          which contains the departure bus name and the message.
    """

    broadcastRequested = pyqtSignal(str, str)
    received = pyqtSignal(str, str)

    def __init__(self, name: str, parent=None):
        """
        Args:
            name: A string that indicates the name of App.
            parent: A parent object.
        """
        super().__init__(parent=parent)
        self.name = name

    def frames(self):
        """Gets frames for which are managed by the App.

        Returns:
            Iterable: An iterable object of Frame objects for showing.
        """
        return ()
