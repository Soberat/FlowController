from PyQt5.QtGui import QIcon
import pyvisa
from ControllerGUITab import ControllerGUITab

from PyQt5.QtWidgets import (
    QVBoxLayout,
    QWidget,
    QTabWidget,
)


# TODO: credit icon creator in about

class MainWindow(QWidget):
    def __init__(self, pyvisa, controllers=None):
        super().__init__()
        if controllers is None:
            controllers = [True, True, True, False]
        self.setWindowIcon(QIcon("icon.png"))
        self.setWindowTitle("FlowController by Mirosław Wiącek")
        self.setMinimumSize(900, 730)

        layout = QVBoxLayout()
        self.setLayout(layout)

        tabs = QTabWidget()
        if controllers[0]:
            try:
                tabs.addTab(ControllerGUITab(channel=1, pyvisa=pyvisa), "Controller 1")
            except pyvisa.errors.VisaIOError as vioe:
                print(f"Error while creating Tab 1: {vioe}")
        if controllers[1]:
            try:
                tabs.addTab(ControllerGUITab(channel=2, pyvisa=pyvisa), "Controller 2")
            except pyvisa.errors.VisaIOError as vioe:
                print(f"Error while creating Tab 2: {vioe}")
        if controllers[2]:
            try:
                tabs.addTab(ControllerGUITab(channel=3, pyvisa=pyvisa), "Controller 3")
            except pyvisa.errors.VisaIOError as vioe:
                print(f"Error while creating Tab 3: {vioe}")
        if controllers[3]:
            try:
                tabs.addTab(ControllerGUITab(channel=4, pyvisa=pyvisa), "Controller 4")
            except pyvisa.errors.VisaIOError as vioe:
                print(f"Error while creating Tab 4: {vioe}")
        layout.addWidget(tabs)

