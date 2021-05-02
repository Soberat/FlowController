import sys
from ControllerGUITab import ControllerGUITab

from PyQt5.QtWidgets import (
    QApplication,
    QVBoxLayout,
    QWidget,
    QTabWidget,
)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FlowController by Mirosław Wiącek")
        self.setMinimumSize(640, 480)

        layout = QVBoxLayout()
        self.setLayout(layout)

        tabs = QTabWidget()
        tabs.addTab(ControllerGUITab(), "Controller 1")
        tabs.addTab(ControllerGUITab(), "Controller 2")
        tabs.addTab(ControllerGUITab(), "Controller 3")
        tabs.addTab(ControllerGUITab(), "Controller 4")
        layout.addWidget(tabs)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
