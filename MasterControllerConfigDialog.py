from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QFormLayout, QPushButton, QLineEdit, QComboBox, QCheckBox
import pyvisa
import sys
import resources


class MasterControllerConfigDialog(QDialog):
    accepted = pyqtSignal(dict)

    # unlock OK only if both fields are set
    def unlock_ok(self):
        self.buttonOk.setEnabled(len(self.resource.currentText()) > 1)

    def ok_pressed(self):
        values = {'resource': self.resource.currentText(),
                  'controllers': [self.controller1Checkbox.isChecked(),
                                  self.controller2Checkbox.isChecked(),
                                  self.controller3Checkbox.isChecked(),
                                  self.controller4Checkbox.isChecked()]}

        self.accepted.emit(values)
        self.accept()

    def cancel_pressed(self):
        self.close()
        sys.exit()

    def refresh_devices(self):
        devices = [device for device in sorted(set(self.rm.list_resources()))]
        if devices != self.devices:
            self.devices = devices
            self.resource.clear()
            self.resource.addItems(devices)

    def __init__(self, resourceManager: pyvisa.ResourceManager, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # PyVisa resource manager for listing available resources
        self.rm = resourceManager

        # Prepare dialog window, disable whatsthis
        self.setFixedSize(220, 200)
        self.setWindowIcon(QIcon(':/icon.png'))
        self.setWindowTitle("Configure Brooks 0254 device")
        self.setWindowFlags(QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowTitleHint)
        self.devices = [device for device in sorted(set(self.rm.list_resources()))]

        self.resource = QComboBox()
        self.resource.addItems(self.devices)
        self.resource.currentTextChanged.connect(self.unlock_ok)

        self.controller1Checkbox = QCheckBox()
        self.controller1Checkbox.setChecked(True)

        self.controller2Checkbox = QCheckBox()
        self.controller2Checkbox.setChecked(True)

        self.controller3Checkbox = QCheckBox()
        self.controller3Checkbox.setChecked(True)

        self.controller4Checkbox = QCheckBox()
        self.controller4Checkbox.setChecked(False)

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
        form.addRow('Controller 1', self.controller1Checkbox)
        form.addRow('Controller 2', self.controller2Checkbox)
        form.addRow('Controller 3', self.controller3Checkbox)
        form.addRow('Controller 4', self.controller4Checkbox)
        form.addRow('', self.buttonOk)
        form.addRow('', self.buttonCancel)
