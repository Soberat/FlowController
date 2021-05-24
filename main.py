import sys
import pyvisa
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QErrorMessage
from MainWindow import MainWindow
from MasterControllerConfigDialog import MasterControllerConfigDialog
import traceback
global parameters

# TODO: Add global tab

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
                              read_termination='\r\n')
    brooks.time_out = 200

    try:
        query = brooks.query('AZI')
        if "Brooks Instrument,Model 0254" not in query:
            dg = QErrorMessage()
            dg.setWindowIcon(QIcon('icon.png'))
            dg.setWindowTitle("Unexpected AZI response")
            dg.showMessage("AZI response was unexpected. Possibly wrong resource! Check console for response")
            dg.exec_()
            print(query)
            sys.exit()
    except pyvisa.VisaIOError as vioe:
        dg = QErrorMessage()
        dg.setWindowIcon(QIcon('icon.png'))
        dg.setWindowTitle("Error in AZI response")
        dg.showMessage("There was an error while querying AZI! Check console for stack trace")
        dg.exec_()
        print(traceback.format_exc())
        sys.exit()

    window = MainWindow(pyvisa=brooks, controllers=parameters['controllers'])
    window.show()
    sys.exit(app.exec_())
