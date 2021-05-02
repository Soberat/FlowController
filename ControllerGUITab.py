import pyqtgraph
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QCheckBox,
    QLineEdit,
    QVBoxLayout,
    QWidget, QHBoxLayout, QGridLayout, QGroupBox, QSlider, QLabel, QPushButton,
)
from pyqtgraph import PlotWidget
import numpy as np


# TODO: Left column
# TODO: Sensor groups
# TODO: Default values
# TODO: Handler functions
class ControllerGUITab(QWidget):
    def __init__(self):
        super().__init__()
        # Create the master layout
        outerLayout = QGridLayout()
        # Create a vertical layout for the left column
        leftColumnLayout = QVBoxLayout()
        # Add an empty label to set constant width - not permanent solution
        label = QLabel("")
        label.setFixedWidth(200)
        leftColumnLayout.addWidget(label)

        # Create layouts and elements for the right column, including graph and sensor/temperature control/dosing groups
        rightColumnLayout = QGridLayout()
        rightGridLayout = QGridLayout()
        rightInnerGrid = QGridLayout()

        # Creation of sensor 1 and sub-elements
        sensor1Group = QGroupBox("Sensor 1")
        sensor1Group.setCheckable(True)
        sensor1Group.setChecked(False)

        # Creation of sensor 2 and sub-elements
        sensor2Group = QGroupBox("Sensor 2")
        sensor2Group.setCheckable(True)
        sensor2Group.setChecked(False)

        tempControllerGroup = QGroupBox("Temperature controller")
        tempControllerGroup.setCheckable(True)
        tempControllerGroup.setChecked(False)
        tempControllerLayout = QVBoxLayout()

        layout = QHBoxLayout()

        temperatureSlider = QSlider(Qt.Horizontal)
        temperatureSlider.setMinimumWidth(95)
        temperatureSlider.setMaximumWidth(1000)
        temperatureLabel = QLabel("Value")
        layout.addWidget(QLabel("Temperature"), alignment=Qt.AlignLeft)
        layout.addWidget(temperatureSlider, alignment=Qt.AlignLeft)
        layout.addWidget(temperatureLabel, alignment=Qt.AlignLeft)

        layout.setStretch(2, 200)
        tempControllerLayout.addLayout(layout)

        layout = QHBoxLayout()
        tempControllerLowEdit = QLineEdit()
        tempControllerLowEdit.setMinimumWidth(30)
        tempControllerLowEdit.setMaximumWidth(60)

        tempControllerHighEdit = QLineEdit()
        tempControllerHighEdit.setMinimumWidth(30)
        tempControllerHighEdit.setMaximumWidth(60)

        layout.addWidget(QLabel("Range"))
        layout.addWidget(tempControllerLowEdit, alignment=Qt.AlignLeft)
        layout.addWidget(tempControllerHighEdit, alignment=Qt.AlignLeft)
        layout.setStretch(2, 10)
        tempControllerLayout.addLayout(layout)

        layout = QHBoxLayout()
        layout.addWidget(QLabel("Ramping"), alignment=Qt.AlignLeft)
        layout.addWidget(QCheckBox(), alignment=Qt.AlignLeft)
        layout.setStretch(1, 10)

        tempControllerLayout.addLayout(layout)

        layout = QHBoxLayout()

        gradientEdit = QLineEdit()
        gradientEdit.setMinimumWidth(30)
        gradientEdit.setMaximumWidth(60)

        layout.addWidget(QLabel("Gradient"), alignment=Qt.AlignLeft)
        layout.addWidget(gradientEdit, alignment=Qt.AlignLeft)
        layout.setStretch(1, 10)

        tempControllerLayout.addLayout(layout)

        tempControllerGroup.setLayout(tempControllerLayout)
        tempControllerGroup.setMinimumWidth(200)

        dosingGroup = QGroupBox("Dosing control")
        dosingGroup.setCheckable(True)
        dosingGroup.setChecked(False)
        dosingLayout = QVBoxLayout()

        layout = QHBoxLayout()
        dosingTimesEdit = QLineEdit()

        label = QLabel("Times")
        label.setFixedWidth(35)

        layout.addWidget(label, alignment=Qt.AlignLeft)
        layout.addWidget(dosingTimesEdit, alignment=Qt.AlignLeft)
        layout.setStretch(1, 10)
        dosingLayout.addLayout(layout)

        layout = QHBoxLayout()
        dosingValuesEdit = QLineEdit()

        label = QLabel("Values")
        label.setFixedWidth(35)

        layout.addWidget(label, alignment=Qt.AlignLeft)
        layout.addWidget(dosingValuesEdit, alignment=Qt.AlignLeft)
        layout.setStretch(1, 10)
        dosingLayout.addLayout(layout)

        nextTimeLabel = QLabel("10 seconds until next dose")
        nextDoseLabel = QLabel("Next dose value: 50")

        dosingButton = QPushButton("Start dosing")

        dosingLayout.addWidget(nextTimeLabel, alignment=Qt.AlignLeft)
        dosingLayout.addWidget(nextDoseLabel, alignment=Qt.AlignLeft)
        dosingLayout.addWidget(dosingButton, alignment=Qt.AlignRight)

        # finally, assign the layout to the group
        dosingGroup.setLayout(dosingLayout)
        dosingGroup.setMinimumWidth(200)

        rightInnerGrid.addWidget(sensor1Group, 0, 0)
        rightInnerGrid.addWidget(sensor2Group, 0, 1)
        rightInnerGrid.addWidget(tempControllerGroup, 1, 0)
        rightInnerGrid.addWidget(dosingGroup, 1, 1)

        rightInnerGrid.setColumnStretch(0, 100)
        rightInnerGrid.setColumnStretch(1, 100)

        self.graph = PlotWidget()
        self.graph.getPlotItem().showGrid(x=True, y=True, alpha=1)
        self.graph.setBackground((25, 35, 45))
        self.graph.getPlotItem().setRange(xRange=(0, 1), yRange=(0, 1))
        self.graph.plot([0, 1, 2, 3], [5, 5, 5, 5])

        rightGridLayout.addWidget(self.graph, 0, 0)
        rightGridLayout.addLayout(rightInnerGrid, 1, 0)
        # Add some checkboxes to the layout
        rightColumnLayout.addLayout(rightGridLayout, 0, 1)

        # Nest the inner layouts into the outer layout
        outerLayout.addLayout(leftColumnLayout, 0, 0)
        outerLayout.addLayout(rightColumnLayout, 0, 1)
        # Set the window's main layout
        self.setLayout(outerLayout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(1000)

    def update_plot(self):
        self.graph.clear()
        self.graph.plot(np.linspace(0, 1, 100), np.random.random(100), pen=pyqtgraph.mkPen((255, 127, 0), width=1.25))
        # pg.mkPen((0, 127, 255), width=1.25)
