import sys
import pyvisa
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
    rm = pyvisa.ResourceManager()
    conDialog = MasterControllerConfigDialog(resourceManager=rm)
    conDialog.accepted.connect(callback)
    conDialog.exec_()

    brooks = rm.open_resource(parameters['resource'], write_termination='\r',
                              read_termination='\r\n')  # , baud_rate = 9600, write_termination = '\r', read_termination = '\r\n')
    brooks.time_out = 200

    window = MainWindow(pyvisa=brooks)
    window.show()
    sys.exit(app.exec_())
