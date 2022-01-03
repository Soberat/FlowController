from PyQt5.QtGui import QIcon
from ControllerGUITab import ControllerGUITab
from Brooks025X import Brooks025X
from GlobalTab import GlobalTab
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QWidget,
    QTabWidget,
)
import resources


class MainWindow(QWidget):
    def __init__(self, pyvisaConnection, controllers=None):
        super().__init__()
        if controllers is None:
            controllers = [True, True, True, False]
        self.setWindowIcon(QIcon(":/icon.png"))
        self.setWindowTitle("FlowController by Mirosław Wiącek")
        self.setMinimumSize(900, 730)

        brooks = Brooks025X(pyvisaConnection, controllers)

        layout = QVBoxLayout()
        self.setLayout(layout)
        tabs = QTabWidget()
        tabReferences = []

        if brooks.controller1 is not None:
            controller1Tab = ControllerGUITab(brooks.controller1)
            tabs.addTab(controller1Tab, "Controller 1")
            tabReferences.append(controller1Tab)
        else:
            tabReferences.append(None)

        if brooks.controller2 is not None:
            controller2Tab = ControllerGUITab(brooks.controller2)
            tabs.addTab(controller2Tab, "Controller 2")
            tabReferences.append(controller2Tab)
        else:
            tabReferences.append(None)

        if brooks.controller3 is not None:
            controller3Tab = ControllerGUITab(brooks.controller3)
            tabs.addTab(controller3Tab, "Controller 3")
            tabReferences.append(controller3Tab)
        else:
            tabReferences.append(None)

        if brooks.controller4 is not None:
            controller4Tab = ControllerGUITab(brooks.controller4)
            tabs.addTab(controller4Tab, "Controller 4")
            tabReferences.append(controller4Tab)
        else:
            tabReferences.append(None)

        tabs.addTab(GlobalTab(brooks, tabReferences), "Global controls")
        layout.addWidget(tabs)

