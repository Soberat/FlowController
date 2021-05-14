from PyQt5.QtGui import QIcon

from ControllerGUITab import ControllerGUITab

from PyQt5.QtWidgets import (
    QVBoxLayout,
    QWidget,
    QTabWidget,
)


# TODO: maybe use QMainWindow
# TODO: credit icon creator in about
class MainWindow(QWidget):
    def __init__(self, pyvisa):
        super().__init__()
        self.setWindowIcon(QIcon("icon.png"))
        self.setWindowTitle("FlowController by Mirosław Wiącek")
        self.setMinimumSize(900, 730)

        layout = QVBoxLayout()
        self.setLayout(layout)

        tabs = QTabWidget()
        tabs.addTab(ControllerGUITab(channel=1, pyvisa=pyvisa), "Controller 1")
        tabs.addTab(ControllerGUITab(channel=2, pyvisa=pyvisa), "Controller 2")
        tabs.addTab(ControllerGUITab(channel=3, pyvisa=pyvisa), "Controller 3")
        tabs.addTab(ControllerGUITab(channel=4, pyvisa=pyvisa), "Controller 4")
        layout.addWidget(tabs)

