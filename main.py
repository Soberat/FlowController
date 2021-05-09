import sys

import serial
from PyQt5.QtWidgets import QApplication
from MainWindow import MainWindow
from MasterControllerConfigDialog import MasterControllerConfigDialog

global parameters


def callback(values):
    global parameters
    parameters = values


if __name__ == "__main__":
    app = QApplication(sys.argv)
    try:
        import qdarkstyle
        app.setStyleSheet(qdarkstyle.load_stylesheet())
    except ImportError as e:
        pass

    global parameters
    conDialog = MasterControllerConfigDialog()
    conDialog.accepted.connect(callback)
    conDialog.exec_()

    ser = serial.Serial(port=parameters['port'],
                        baudrate=9600,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=None)

    window = MainWindow(serial=ser)
    window.show()
    sys.exit(app.exec_())
