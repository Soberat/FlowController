import serial
from PyQt5 import QtCore
from PyQt5.QtCore import QRegExp, pyqtSignal, QTimer
from PyQt5.QtGui import QRegExpValidator, QIcon, QIntValidator
from PyQt5.QtWidgets import QDialog, QFormLayout, QPushButton, QLineEdit, QComboBox
from serial.tools.list_ports import comports


class SensorConfigDialog(QDialog):
    accepted = pyqtSignal(dict)

    parity = {'None': serial.PARITY_NONE,
              'Odd': serial.PARITY_ODD,
              'Space': serial.PARITY_SPACE,
              'Even': serial.PARITY_EVEN,
              'Mark': serial.PARITY_MARK,
              'Names': serial.PARITY_NAMES}

    stop = {'1': serial.STOPBITS_ONE,
            '1.5': serial.STOPBITS_ONE_POINT_FIVE,
            '2': serial.STOPBITS_TWO}

    data = {'8': serial.EIGHTBITS,
            '7': serial.SEVENBITS,
            '6': serial.SIXBITS,
            '5': serial.FIVEBITS
            }

    # unlock OK only if all fields are set
    def unlock_ok(self):
        elements = [self.port.currentText(),
                    self.baudrate.text(),
                    self.databits.currentText(),
                    self.paritybits.currentText(),
                    self.stopbits.currentText(),
                    self.datalen.text(),
                    self.header.text()]
        self.buttonOk.setEnabled(all([len(x) > 0 for x in elements]))

    def ok_pressed(self):
        values = {'port': self.port.currentText(),
                  'baudrate': self.baudrate.text(),
                  'databits': self.data[self.databits.currentText()],
                  'paritybits': self.parity[self.paritybits.currentText()],
                  'stopbits': self.stop[self.stopbits.currentText()],
                  'datalen': int(self.datalen.text()),
                  'header': self.header.text()}
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
        self.setFixedSize(280, 285)
        self.setWindowIcon(QIcon('icon.png'))
        self.setWindowTitle("Configure serial device")
        self.setWindowFlags(QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowTitleHint)
        self.devices = [device.name for device in set(comports())]

        self.port = QComboBox()
        self.port.addItems(self.devices)
        self.port.currentTextChanged.connect(self.unlock_ok)

        self.baudrate = QLineEdit()
        self.baudrate.setValidator(QRegExpValidator(QRegExp("[0-9]{1,5}")))
        self.baudrate.textChanged.connect(self.unlock_ok)

        self.databits = QComboBox()
        self.databits.addItems(self.data.keys())
        self.databits.currentTextChanged.connect(self.unlock_ok)

        self.paritybits = QComboBox()
        self.paritybits.addItems(self.parity.keys())
        self.paritybits.currentTextChanged.connect(self.unlock_ok)

        self.stopbits = QComboBox()
        self.stopbits.addItems(self.stop.keys())
        self.stopbits.currentTextChanged.connect(self.unlock_ok)

        self.datalen = QLineEdit()
        self.datalen.setText("64")
        self.datalen.setValidator(QIntValidator())
        self.datalen.textChanged.connect(self.unlock_ok)

        self.header = QLineEdit()
        self.header.setText("Sensor")
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
        form.addRow('Data length', self.datalen)
        form.addRow('Header', self.header)
        form.addRow('', self.buttonOk)
        form.addRow('', self.buttonCancel)
