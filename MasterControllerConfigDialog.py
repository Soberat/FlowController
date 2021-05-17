from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QFormLayout, QPushButton, QLineEdit, QComboBox
import pyvisa


class MasterControllerConfigDialog(QDialog):
    accepted = pyqtSignal(dict)

    # unlock OK only if both fields are set
    def unlock_ok(self):
        self.buttonOk.setEnabled(len(self.resource.currentText()) > 1)

    def ok_pressed(self):
        values = {'resource': self.resource.currentText()}
        self.accepted.emit(values)
        self.accept()

    def cancel_pressed(self):
        self.close()

    def refresh_devices(self):
        devices = [device for device in sorted(set(self.list_resources()))]
        if devices != self.devices:
            self.devices = devices
            self.resource.clear()
            self.resource.addItems(devices)

    def __init__(self, resourceManager: pyvisa.ResourceManager, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # PyVisa resource manager for listing available resources
        self.rm = resourceManager

        # Prepare dialog window, disable whatsthis
        self.setFixedSize(220, 100)
        self.setWindowIcon(QIcon('icon.png'))
        self.setWindowTitle("Configure Brooks 0254 device")
        self.setWindowFlags(QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowTitleHint)
        self.devices = [device for device in sorted(set(self.list_resources()))]

        self.resource = QComboBox()
        self.resource.addItems(self.devices)
        self.resource.currentTextChanged.connect(self.unlock_ok)

        self.identity = QLineEdit()
        self.identity.setEnabled(False)

        self.buttonOk = QPushButton("Connect")
        self.unlock_ok()
        self.buttonOk.clicked.connect(self.ok_pressed)

        self.buttonCancel = QPushButton("Cancel")
        self.buttonCancel.clicked.connect(self.cancel_pressed)

        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_devices)
        self.timer.start(1000)

        form = QFormLayout(self)
        form.addRow('Resource', self.resource)
        form.addRow('', self.buttonOk)
        form.addRow('', self.buttonCancel)
