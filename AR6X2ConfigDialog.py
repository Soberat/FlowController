from PyQt5 import QtCore
from PyQt5.QtCore import QRegExp, pyqtSignal, QTimer
from PyQt5.QtGui import QRegExpValidator, QIcon
from PyQt5.QtWidgets import QDialog, QFormLayout, QPushButton, QLineEdit, QComboBox
from serial.tools.list_ports import comports
import resources


class AR6X2ConfigDialog(QDialog):
    accepted = pyqtSignal(dict)

    # unlock OK only if both fields are set
    def unlock_ok(self):
        self.buttonOk.setEnabled(len(self.address.text()) and len(self.port.currentText()) > 1)

    def ok_pressed(self):
        values = {'port': self.port.currentText(),
                  'address': self.address.text()}
        self.accepted.emit(values)
        self.accept()

    def cancel_pressed(self):
        self.close()

    def refresh_devices(self):
        devices = [device.name for device in set(comports())]
        if devices != self.devices:
            self.devices = devices
            self.port.clear()
            self.port.addItems(devices)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Prepare dialog window, disable whatsthis
        self.setFixedSize(200, 120)
        self.setWindowIcon(QIcon(':/icon.png'))
        self.setWindowTitle("Configure AR6X2 device")
        self.setWindowFlags(QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowTitleHint)
        self.devices = [device.name for device in set(comports())]

        self.port = QComboBox()
        self.port.addItems(self.devices)
        self.port.currentTextChanged.connect(self.unlock_ok)

        self.address = QLineEdit()
        self.address.setValidator(QRegExpValidator(QRegExp("[0-9]{1,5}")))
        self.address.textChanged.connect(self.unlock_ok)

        self.buttonOk = QPushButton("Connect")
        self.buttonOk.setEnabled(False)
        self.buttonOk.clicked.connect(self.ok_pressed)

        self.buttonCancel = QPushButton("Cancel")
        self.buttonCancel.clicked.connect(self.cancel_pressed)

        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_devices)
        self.timer.start(1000)

        form = QFormLayout(self)
        form.addRow('Port', self.port)
        form.addRow('Address', self.address)
        form.addRow('', self.buttonOk)
        form.addRow('', self.buttonCancel)
