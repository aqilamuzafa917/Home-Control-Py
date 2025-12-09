
from PyQt6.QtCore import QObject, pyqtSignal

class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    result = pyqtSignal(object)
