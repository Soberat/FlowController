from PyQt5.QtGui import QIcon
import pyvisa
from ControllerGUITab import ControllerGUITab
from GlobalTab import GlobalTab
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QWidget,
    QTabWidget,
)
import resources


# TODO: credit icon creator in about

class MainWindow(QWidget):
    def __init__(self, pyvisaConnection, controllers=None):
        super().__init__()
        if controllers is None:
            controllers = [True, True, True, False]
        self.setWindowIcon(QIcon(":/icon.png"))
        self.setWindowTitle("FlowController by Mirosław Wiącek")
        self.setMinimumSize(900, 730)

        layout = QVBoxLayout()
        self.setLayout(layout)

        tabs = QTabWidget()

        references = []
        if controllers[0]:
            try:
                tab = ControllerGUITab(channel=1, pyvisa=pyvisaConnection)
                tabs.addTab(tab, "Controller 1")
                references.append(tab)
            except pyvisa.errors.VisaIOError as vioe:
                print(f"Error while creating Tab 1: {vioe}")
        else:
            references.append(None)
        if controllers[1]:
            try:
                tab = ControllerGUITab(channel=2, pyvisa=pyvisaConnection)
                tabs.addTab(tab, "Controller 2")
                references.append(tab)
            except pyvisa.errors.VisaIOError as vioe:
                print(f"Error while creating Tab 2: {vioe}")
        else:
            references.append(None)
        if controllers[2]:
            try:
                tab = ControllerGUITab(channel=3, pyvisa=pyvisaConnection)
                tabs.addTab(tab, "Controller 3")
                references.append(tab)
            except pyvisa.errors.VisaIOError as vioe:
                print(f"Error while creating Tab 3: {vioe}")
        else:
            references.append(None)
        if controllers[3]:
            try:
                tab = ControllerGUITab(channel=4, pyvisa=pyvisaConnection)
                tabs.addTab(tab, "Controller 4")
                references.append(tab)
            except pyvisa.errors.VisaIOError as vioe:
                print(f"Error while creating Tab 4: {vioe}")
        else:
            references.append(None)

        tabs.addTab(GlobalTab(references), "Global controls")
        layout.addWidget(tabs)

