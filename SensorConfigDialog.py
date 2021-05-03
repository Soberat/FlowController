from PyQt5 import QtCore
from PyQt5.QtCore import QRegExp, pyqtSignal, QTimer
from PyQt5.QtGui import QRegExpValidator, QIcon
from PyQt5.QtWidgets import QDialog, QFormLayout, QPushButton, QLineEdit, QComboBox
from serial.tools.list_ports import comports


class SensorConfigDialog(QDialog):
    accepted = pyqtSignal(dict)

    # unlock OK only if all fields are set
    def unlock_ok(self):
        elements = [self.port.currentText(),
                    self.baudrate.text(),
                    self.databits.text(),
                    self.paritybits.text(),
                    self.stopbits.text(),
                    self.header.text()]
        return all([len(x) > 0 for x in elements])

    def ok_pressed(self):
        values = {'port': self.port.currentText(),
                  'baudrate': self.address.text(),
                  'databits': self.databits.text(),
                  'paritybits': self.paritybits.text(),
                  'stopbits': self.stopbits.text(),
                  'header': self.header.text()}
        self.accepted.emit(values)
        self.accept()

    def cancel_pressed(self):
        self.close()

    def refresh_devices(self):
        devices = set(comports())
        if devices != self.devices:
            self.devices = devices
            self.port.clear()
            self.port.addItems(devices)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Prepare dialog window, disable whatsthis
        self.setFixedSize(280, 230)
        self.setWindowIcon(QIcon('icon.png'))
        self.setWindowTitle("Configure serial device")
        self.setWindowFlags(QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowTitleHint)
        self.devices = set(comports())

        self.port = QComboBox()
        self.port.addItems(self.devices)
        self.port.currentTextChanged.connect(self.unlock_ok)

        self.baudrate = QLineEdit()
        self.baudrate.setValidator(QRegExpValidator(QRegExp("[0-9]{1,5}")))
        self.baudrate.textChanged.connect(self.unlock_ok)

        self.databits = QLineEdit()
        self.databits.setValidator(QRegExpValidator(QRegExp("[0-9]{1,5}")))
        self.databits.textChanged.connect(self.unlock_ok)

        self.paritybits = QLineEdit()
        self.paritybits.setValidator(QRegExpValidator(QRegExp("[0-9]{1,5}")))
        self.paritybits.textChanged.connect(self.unlock_ok)

        self.stopbits = QLineEdit()
        self.stopbits.setValidator(QRegExpValidator(QRegExp("[0-9]{1,5}")))
        self.stopbits.textChanged.connect(self.unlock_ok)

        self.header = QLineEdit()
        self.header.textChanged.connect(self.unlock_ok)

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
        form.addRow('Baud rate', self.baudrate)
        form.addRow('Data bits', self.databits)
        form.addRow('Parity bits', self.paritybits)
        form.addRow('Stop bits', self.stopbits)
        form.addRow('Header', self.header)
        form.addRow('', self.buttonOk)
        form.addRow('', self.buttonCancel)
