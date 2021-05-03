import pyqtgraph
from PyQt5.QtCore import Qt, QTimer, QRegExp
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtWidgets import (
    QCheckBox,
    QLineEdit,
    QVBoxLayout,
    QWidget, QHBoxLayout, QGridLayout, QGroupBox, QSlider, QLabel, QPushButton, QFormLayout, QComboBox,
)
from pyqtgraph import PlotWidget
import numpy as np
from Controller import Controller


# TODO: Left column
# TODO: Sensor groups
# TODO: Default values
# TODO: Handler functions
class ControllerGUITab(QWidget):
    LEFT_COLUMN_MAX_WIDTH = 400

    def __init__(self):
        super().__init__()
        # Create the master layout
        outerLayout = QGridLayout()
        self.graph = None

        # Nest the inner layouts into the outer layout
        outerLayout.addLayout(self.create_left_column(), 0, 0)
        outerLayout.addLayout(self.create_right_column(), 0, 1)
        # Set the window's main layout
        self.setLayout(outerLayout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(500)

    def update_plot(self):
        self.graph.clear()
        self.graph.plot(np.linspace(0, 1, 100), np.random.random(100), pen=pyqtgraph.mkPen((255, 127, 0), width=1.25))
        # pg.mkPen((0, 127, 255), width=1.25)

    def create_left_column(self):
        # Create a vertical layout for the left column
        leftColumnLayout = QVBoxLayout()

        # Valve override group
        vorGroup = QGroupBox("Valve override")
        vorLayout = QVBoxLayout()

        layout = QHBoxLayout()

        # TODO: on check, uncheck others
        vorNormalButton = QPushButton("Normal")
        vorNormalButton.setMinimumWidth(50)
        vorNormalButton.setFixedHeight(30)
        vorNormalButton.setCheckable(True)
        vorNormalButton.setChecked(True)

        vorClosedButton = QPushButton("Closed")
        vorClosedButton.setMinimumWidth(50)
        vorClosedButton.setFixedHeight(30)
        vorClosedButton.setCheckable(True)

        vorOpenButton = QPushButton("Open")
        vorOpenButton.setMinimumWidth(50)
        vorOpenButton.setFixedHeight(30)
        vorOpenButton.setCheckable(True)

        vorStatusLabel = QLabel("Current status: Normal")

        layout.addWidget(vorNormalButton)
        layout.addWidget(vorClosedButton)
        layout.addWidget(vorOpenButton)

        vorLayout.addLayout(layout)
        vorLayout.addWidget(vorStatusLabel)

        vorGroup.setLayout(vorLayout)
        vorGroup.setMaximumWidth(ControllerGUITab.LEFT_COLUMN_MAX_WIDTH)
        leftColumnLayout.addWidget(vorGroup, alignment=Qt.AlignTop)

        # Process configuration group
        processGroup = QGroupBox("Process configuration")
        processLayout = QFormLayout()

        gasDropdown = QComboBox()
        gasDropdown.addItems(Controller.GAS_TYPES.keys())

        pvFullScaleEdit = QLineEdit()
        pvFullScaleEdit.setText("100.000")
        pvFullScaleEdit.setValidator(QRegExpValidator(QRegExp("(-|)[0-9]{1,3}\\.[0-9]{1,3}")))

        pvSigtypeDropdown = QComboBox()
        pvSigtypeDropdown.addItems(Controller.INPUT_PORT_TYPES.keys())

        spFullScaleEdit = QLineEdit()
        spFullScaleEdit.setText("100.000")
        spFullScaleEdit.setValidator(QRegExpValidator(QRegExp("(-|)[0-9]{1,3}\\.[0-9]{1,3}")))

        spSigtypeDropdown = QComboBox()
        spSigtypeDropdown.addItems(Controller.OUTPUT_PORT_TYPES.keys())

        spSourceDropdown = QComboBox()
        spSourceDropdown.addItems(Controller.SP_SOURCES.keys())

        decimalDropdown = QComboBox()
        decimalDropdown.addItems(Controller.DECIMAL_POINTS.keys())

        unitsDropdown = QComboBox()
        unitsDropdown.addItems(Controller.MEASUREMENT_UNITS.keys())

        timebaseDropdown = QComboBox()
        timebaseDropdown.addItems(Controller.RATE_TIME_BASE.keys())

        processLayout.addRow(QLabel("Gas"), gasDropdown)
        processLayout.addRow(QLabel("PV Full Scale"), pvFullScaleEdit)
        processLayout.addRow(QLabel("PV Signal Type"), pvSigtypeDropdown)
        processLayout.addRow(QLabel("SP Full Scale"), spFullScaleEdit)
        processLayout.addRow(QLabel("SP Signal Type"), spSigtypeDropdown)
        processLayout.addRow(QLabel("Setpoint source"), spSourceDropdown)
        processLayout.addRow(QLabel("Decimal point"), decimalDropdown)
        processLayout.addRow(QLabel("Measurement units"), unitsDropdown)
        processLayout.addRow(QLabel("Time base"), timebaseDropdown)

        processGroup.setLayout(processLayout)
        processGroup.setMaximumWidth(ControllerGUITab.LEFT_COLUMN_MAX_WIDTH)
        leftColumnLayout.addWidget(processGroup, alignment=Qt.AlignTop)
        leftColumnLayout.setStretch(1, 100)

        runtimeGroup = QGroupBox("Runtime options")
        runtimeLayout = QVBoxLayout()

        layout = QHBoxLayout()

        bufferSizeEdit = QLineEdit()
        bufferSizeEdit.setText("64")
        bufferSizeEdit.setValidator(QRegExpValidator(QRegExp("[0-9]*")))

        layout.addWidget(QLabel("Sample buffer size"))
        layout.addWidget(bufferSizeEdit)
        layout.addWidget(QLabel("samples"))

        runtimeLayout.addLayout(layout)

        layout = QHBoxLayout()

        intervalEdit = QLineEdit()
        intervalEdit.setText("500")
        intervalEdit.setValidator(QRegExpValidator(QRegExp("[0-9]*.[0-9]*")))

        layout.addWidget(QLabel("Data update interval"))
        layout.addWidget(intervalEdit)
        layout.addWidget(QLabel("milliseconds"))

        runtimeLayout.addLayout(layout)

        layout = QHBoxLayout()

        setpointEdit = QLineEdit()
        setpointEdit.setText("1")
        setpointEdit.setValidator(QRegExpValidator(QRegExp("[0-9]*.[0-9]*")))
        unitsLabel = QLabel("mu/tb")

        layout.addWidget(QLabel("Setpoint"))
        layout.addWidget(setpointEdit)
        layout.addWidget(unitsLabel)

        runtimeLayout.addLayout(layout)

        layout = QHBoxLayout()

        manualMeasureButton = QPushButton("Get measurement")
        saveCsvButton = QPushButton("Save to CSV")

        layout.addWidget(manualMeasureButton)
        layout.addWidget(saveCsvButton)

        runtimeLayout.addLayout(layout)

        runtimeGroup.setLayout(runtimeLayout)
        runtimeGroup.setMaximumWidth(ControllerGUITab.LEFT_COLUMN_MAX_WIDTH)
        runtimeGroup.setFixedHeight(150)

        leftColumnLayout.addWidget(runtimeGroup, alignment=Qt.AlignBottom)

        return leftColumnLayout

    def create_right_column(self):
        # Create layouts and elements for the right column, including graph and sensor/temperature control/dosing groups
        rightColumnLayout = QGridLayout()
        rightGridLayout = QVBoxLayout()
        rightInnerGrid = QGridLayout()

        # Creation of sensor 1 and sub-elements
        sensor1Group = QGroupBox("Sensor 1")
        sensor1Group.setCheckable(True)
        sensor1Group.setChecked(False)

        # Creation of sensor 2 and sub-elements
        sensor2Group = QGroupBox("Sensor 2")
        sensor2Group.setCheckable(True)
        sensor2Group.setChecked(False)

        # TODO: Add address and comport fields
        tempControllerGroup = QGroupBox("Temperature controller")
        tempControllerGroup.setCheckable(True)
        tempControllerGroup.setChecked(False)
        tempControllerLayout = QVBoxLayout()

        layout = QHBoxLayout()

        temperatureSlider = QSlider(Qt.Horizontal)
        temperatureSlider.setMinimumWidth(95)
        temperatureSlider.setMaximumWidth(1000)
        temperatureSlider.setMinimum(-199.9)
        temperatureSlider.setMaximum(850.0)
        temperatureSlider.setValue(100)
        temperatureLabel = QLabel("100")
        layout.addWidget(QLabel("Temperature"), alignment=Qt.AlignLeft)
        layout.addWidget(temperatureSlider, alignment=Qt.AlignLeft)
        layout.addWidget(temperatureLabel, alignment=Qt.AlignLeft)
        layout.addWidget(QLabel("℃"), alignment=Qt.AlignLeft)

        layout.setStretch(3, 200)
        tempControllerLayout.addLayout(layout)

        # these edits have validators, but input still has to be capped
        # Also, the validator seems overly complex if we cap the value anyway
        layout = QHBoxLayout()
        tempControllerLowEdit = QLineEdit()
        tempControllerLowEdit.setMinimumWidth(30)
        tempControllerLowEdit.setMaximumWidth(60)
        tempControllerLowEdit.setText("-199.9")
        tempControllerLowEdit.setValidator(QRegExpValidator(QRegExp("(-[0-9]{1,3}\\.[0-9]|[0-9]{1,3}\\.[0-9|[0-9]{1,4})")))

        tempControllerHighEdit = QLineEdit()
        tempControllerHighEdit.setMinimumWidth(30)
        tempControllerHighEdit.setMaximumWidth(60)
        tempControllerHighEdit.setText("850.0")
        tempControllerHighEdit.setValidator(QRegExpValidator(QRegExp("(-[0-9]{1,3}\\.[0-9]|[0-9]{1,3}\\.[0-9|[0-9]{1,4})")))

        layout.addWidget(QLabel("Range"))
        layout.addWidget(tempControllerLowEdit, alignment=Qt.AlignLeft)
        layout.addWidget(tempControllerHighEdit, alignment=Qt.AlignLeft)
        layout.addWidget(QLabel("℃"))
        layout.setStretch(3, 10)
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
        gradientEdit.setText("0.1")  # default value from the datasheet

        temperatureButton = QPushButton("Enable output")
        temperatureButton.setCheckable(True)

        layout.addWidget(QLabel("Gradient"), alignment=Qt.AlignLeft)
        layout.addWidget(gradientEdit, alignment=Qt.AlignLeft)
        layout.addWidget(QLabel("℃/min"))
        layout.addWidget(temperatureButton, alignment=Qt.AlignBottom)
        layout.setStretch(2, 10)

        tempControllerLayout.addLayout(layout)

        tempControllerGroup.setLayout(tempControllerLayout)
        tempControllerGroup.setMinimumWidth(200)
        tempControllerGroup.setFixedHeight(150)

        dosingGroup = QGroupBox("Dosing control")
        dosingGroup.setCheckable(True)
        dosingGroup.setChecked(False)
        dosingLayout = QVBoxLayout()

        layout = QHBoxLayout()
        dosingTimesEdit = QLineEdit()
        dosingTimesEdit.setMinimumWidth(200)
        dosingTimesEdit.setText("1000, 10000, 15000")
        dosingTimesEdit.setValidator(QRegExpValidator(QRegExp("([0-9]*, |))+")))

        label = QLabel("Times")
        label.setFixedWidth(35)

        layout.addWidget(label, alignment=Qt.AlignLeft)
        layout.addWidget(dosingTimesEdit, alignment=Qt.AlignLeft)
        layout.setStretch(1, 10)
        dosingLayout.addLayout(layout)

        layout = QHBoxLayout()
        dosingValuesEdit = QLineEdit()
        dosingValuesEdit.setMinimumWidth(200)
        dosingValuesEdit.setText("1.0, 2.0, 5.0")
        dosingValuesEdit.setValidator(QRegExpValidator(QRegExp("([0-9]{1,3}\\.[0-9]{1,3},(| ))+")))

        label = QLabel("Values")
        label.setFixedWidth(35)

        layout.addWidget(label, alignment=Qt.AlignLeft)
        layout.addWidget(dosingValuesEdit, alignment=Qt.AlignLeft)
        layout.setStretch(1, 10)
        dosingLayout.addLayout(layout)

        nextTimeLabel = QLabel("10 seconds until next dose")
        nextDoseLabel = QLabel("Next dose value: 50")

        dosingButton = QPushButton("Start dosing")
        dosingButton.setCheckable(True)

        dosingLayout.addWidget(nextTimeLabel, alignment=Qt.AlignLeft)
        dosingLayout.addWidget(nextDoseLabel, alignment=Qt.AlignLeft)
        dosingLayout.addWidget(dosingButton, alignment=Qt.AlignRight)

        # finally, assign the layout to the group
        dosingGroup.setLayout(dosingLayout)
        dosingGroup.setMinimumWidth(200)
        dosingGroup.setFixedHeight(150)

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

        rightGridLayout.addWidget(self.graph)
        rightGridLayout.addLayout(rightInnerGrid)
        # Add some checkboxes to the layout
        rightColumnLayout.addLayout(rightGridLayout, 0, 1)

        return rightColumnLayout
