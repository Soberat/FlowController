import sys

from PyQt5.QtGui import QIcon

from ControllerGUITab import ControllerGUITab

from PyQt5.QtWidgets import (
    QApplication,
    QVBoxLayout,
    QWidget,
    QTabWidget,
)


# TODO: maybe use QMainWindow
# TODO: credit icon creator in about
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon("icon.png"))
        self.setWindowTitle("FlowController by Mirosław Wiącek")
        self.setMinimumSize(900, 730)

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
    try:
        import qdarkstyle
        app.setStyleSheet(qdarkstyle.load_stylesheet())
    except ImportError as e:
        pass
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
