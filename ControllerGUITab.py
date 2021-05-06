import sys
import pyqtgraph
from PyQt5.QtCore import Qt, QTimer, QRegExp
from PyQt5.QtGui import QRegExpValidator, QIntValidator
from PyQt5.QtWidgets import (
    QCheckBox,
    QLineEdit,
    QVBoxLayout,
    QWidget, QHBoxLayout, QGridLayout, QGroupBox, QSlider, QLabel, QPushButton, QFormLayout, QComboBox, QErrorMessage
)
from pyqtgraph import PlotWidget
import numpy as np
from Controller import Controller
from AR6X2ConfigDialog import AR6X2ConfigDialog
from AR6X2 import AR6X2
from SensorConfigDialog import SensorConfigDialog
from Sensor import Sensor
from datetime import datetime
from numpy_ringbuffer import RingBuffer
from serial import SerialException


# TODO: Getting values from serial, and not assuming defaults
# TODO: Handler functions
# TODO: Implement dosing process
# TODO: Disabling the dosing group should disable the process

class ControllerGUITab(QWidget):
    LEFT_COLUMN_MAX_WIDTH = 400

    def __init__(self):
        super().__init__()
        # Create the master layout
        outerLayout = QGridLayout()
        self.graph = None
        self.controller = None
        self.temperatureController = None
        self.tempControllerGroup = None
        self.sensor1 = None
        self.sensor2 = None
        self.sensor1Group = None
        self.sensor2Group = None

        self.vorNormalButton = None
        self.vorClosedButton = None
        self.vorOpenButton = None

        self.gasDropdown = None
        self.pvFullScaleEdit = None
        self.pvSigtypeDropdown = None
        self.spFullScaleEdit = None
        self.spSigtypeDropdown = None
        self.spSourceDropdown = None
        self.decimalDropdown = None
        self.measureUnitsDropdown = None
        self.timebaseDropdown = None

        self.bufferSizeEdit = None
        self.intervalEdit = None
        self.setpointEdit = None
        self.setpointUnitsLabel = None

        self.sensor1Timer = None
        self.sensor1SampleIntervalEdit = None
        self.sensor1BufferSizeEdit = None

        self.sensor2Timer = None
        self.sensor2SampleIntervalEdit = None
        self.sensor2BufferSizeEdit = None

        self.temperatureSlider = None
        self.temperatureLabel = None
        self.rangeLowEdit = None
        self.rangeHighEdit = None
        self.rampingCheckbox = None
        self.gradientEdit = None
        self.tempControlButton = None

        self.dosingTimesEdit = None
        self.dosingTimes = None
        self.dosingValuesEdit = None
        self.dosingValues = None
        self.dosingUnitsLabel = None
        self.dosingTimerLabel = None
        self.dosingValueLabel = None
        self.dosingControlButton = None

        # Data buffers
        self.sampleBufferSize = 64
        self.samplesPV = RingBuffer(capacity=self.sampleBufferSize, dtype=np.float16)
        self.samplesTotalizer = RingBuffer(capacity=self.sampleBufferSize, dtype=np.float16)
        self.sampleTimestamps = RingBuffer(capacity=self.sampleBufferSize, dtype=np.uint64)

        # Nest the inner layouts into the outer layout
        outerLayout.addLayout(self.create_left_column(), 0, 0)
        outerLayout.addLayout(self.create_right_column(), 0, 1)
        # Set the window's main layout
        self.setLayout(outerLayout)

        self.graphTimer = QTimer()
        self.graphTimer.timeout.connect(self.update_plot)
        self.graphTimer.start(500)

        # We will use the above timer to update dosing labels
        self.dosingValue = None
        self.dosingTimer = QTimer()

        self.defaultStyleSheet = QLineEdit().styleSheet()

        # Get initial dosing values from the text inside
        self.dosingValues = [float(x) for x in self.dosingValuesEdit.text().split(sep=',') if x.strip() != '']
        self.dosingTimes = [int(x) for x in self.dosingTimesEdit.text().split(sep=',') if x.strip() != '']
        self.dosingValues.reverse()
        self.dosingTimes.reverse()

    def get_measurement(self):
        # Demo implementation, generating random data
        self.samplesTotalizer.append(0)  # unused
        self.samplesPV.append(np.random.random_integers(0, 100, 1)[0])
        self.sampleTimestamps.append(datetime.now().timestamp())

        return
        # Proper implementation that gets the data from the device over serial
        total, current, timestamp = self.controller.get_measurements()
        self.samplesTotalizer.append(total)
        self.samplesPV.append(current)
        self.sampleTimestamps.append(timestamp)

    # Save samples to a csv file, named after the current time and controller number it is coming from
    def save_to_csv(self):
        now = datetime.now()
        if self.controller is not None:
            filename = now.strftime(f"controller{self.controller.__channel}_%Y-%m-%d_%H-%M-%S.csv")
        else:
            filename = now.strftime("controller0_%Y-%m-%d_%H-%M-%S.csv")
        file = open(filename, 'w')
        if self.controller is not None:
            file.write(
                f"Gas: {self.controller.__gas}, Gas factor:{self.controller.__gasFactor}, Decimal point:{self.controller.__decimal_point}, Units:{self.controller.__measure_units}/{self.controller.__time_base}\n")
        file.write("Measurement [Rate], Measurement [Total], Unix timestamp (in milliseconds)\n")
        for i in range(0, self.sampleBufferSize - 1):
            file.write(f'{self.samplesPV[i]},{self.samplesTotalizer[i]},{self.sampleTimestamps[i]}\n')
        file.write('\n')

        # if available, append data from sensors
        if self.sensor1 is not None and len(self.sensor1.buffer) > 0:
            file.write(f"Sensor 1 header: {self.sensor1.header}\n")
            for i in range(0, len(self.sensor1.buffer)):
                file.write(str(self.sensor1.buffer[i]))
        file.write('\n')

        if self.sensor2 is not None and len(self.sensor2.buffer) > 0:
            file.write(f"Sensor 2 header: {self.sensor2.header}\n")
            for i in range(0, len(self.sensor2.buffer)):
                file.write(self.sensor2.buffer[i])

        file.close()

    # Handler functions for UI elements
    def update_vor_normal(self):
        print("update_vor_normal")
        if self.vorNormalButton.isChecked():
            # disable other buttons to clarify which VOR state is active
            self.vorClosedButton.setChecked(False)
            self.vorOpenButton.setChecked(False)
            self.controller.set_valve_override(Controller.VOR_OPTION_NORMAL)

    def update_vor_closed(self):
        print("update_vor_closed")
        if self.vorClosedButton.isChecked():
            self.vorNormalButton.setChecked(False)
            self.vorOpenButton.setChecked(False)
            self.controller.set_valve_override(Controller.VOR_OPTION_CLOSED)

    def update_vor_open(self):
        print("update_vor_open")
        if self.vorOpenButton.isChecked():
            self.vorClosedButton.setChecked(False)
            self.vorNormalButton.setChecked(False)
            self.controller.set_valve_override(Controller.VOR_OPTION_OPEN)

    def update_gas_type(self):
        print("update_gas_type")
        self.controller.set_gas(self.gasDropdown.currentText())
        self.wipe_buffers()

    def update_pv_full_scale(self):
        print("update_pv_full_scale")
        self.controller.set_pv_full_scale(float(self.pvFullScaleEdit.text()))

    def update_pv_signal_type(self):
        print("update_pv_signal_type")
        self.controller.set_pv_signal_type(self.pvSigtypeDropdown.currentText())

    def update_sp_full_scale(self):
        print("update_sp_full_scale")
        self.controller.set_sp_full_scale(float(self.spFullScaleEdit.text()))

    def update_sp_signal_type(self):
        print("update_sp_signal_type")
        self.controller.set_sp_signal_type(self.spSigtypeDropdown.currentText())

    def update_source(self):
        print("update_source_enable")
        self.controller.set_source(self.spSourceDropdown.currentText())

    def update_decimal_point(self):
        print("update_decimal_point")
        self.controller.set_decimal_point(self.decimalDropdown.currentText())

    def update_measure_units(self):
        print("update_measure_units")
        self.dosingUnitsLabel.setText(f"{self.measureUnitsDropdown.currentText()}/{self.timebaseDropdown.currentText()}")
        self.setpointUnitsLabel.setText(f"{self.measureUnitsDropdown.currentText()}/{self.timebaseDropdown.currentText()}")
        self.controller.set_measurement_units(self.measureUnitsDropdown.currentText())

    def update_time_base(self):
        print("update_time_base")
        self.dosingUnitsLabel.setText(f"{self.measureUnitsDropdown.currentText()}/{self.timebaseDropdown.currentText()}")
        self.setpointUnitsLabel.setText(f"{self.measureUnitsDropdown.currentText()}/{self.timebaseDropdown.currentText()}")
        self.controller.set_time_base(self.timebaseDropdown.currentText())

    def update_buffer_size(self):
        self.change_buffer_size(int(self.bufferSizeEdit.text()))
        self.sampleBufferSize = int(self.bufferSizeEdit.text())

    def update_graph_timer(self):
        self.graphTimer.setInterval(int(self.intervalEdit.text()))

    def update_setpoint(self):
        value = float(self.setpointEdit.text())
        self.controller.set_setpoint(value)

    def update_sensor1_timer(self):
        print("update_sensor1_timer")
        self.sensor1Timer.setInterval(int(self.sensor1SampleIntervalEdit.text()))

    def update_sensor1_buffer(self):
        print("update_sensor1_buffer")
        self.sensor1.change_buffer_size(int(self.sensor1BufferSizeEdit.text()))

    def update_sensor2_timer(self):
        print("update_sensor2_timer")
        self.sensor2Timer.setInterval(int(self.sensor2SampleIntervalEdit.text()))

    def update_sensor2_buffer(self):
        print("update_sensor2_buffer")
        self.sensor2.change_buffer_size(int(self.sensor2BufferSizeEdit.text()))

    def update_temperature(self):
        print("update_temperature")
        self.temperatureController.set_temperature(float(self.temperatureSlider.value()))
        self.temperatureLabel.setText(self.temperatureSlider.value())

    def update_range_low(self):
        print("update_range_low")
        newTemp = self.temperatureController.set_range_low(float(self.rangeLowEdit.text()))
        self.temperatureSlider.setMinimum(float(self.rangeLowEdit.text()))
        self.temperatureSlider.setValue(newTemp)

    def update_range_high(self):
        print("update_range_high")
        newTemp = self.temperatureController.set_range_high(float(self.rangeHighEdit.text()))
        self.temperatureSlider.setMaximum(float(self.rangeHighEdit.text()))
        self.temperatureSlider.setValue(newTemp)

    def update_ramping_enable(self):
        print("update_ramping_enable")
        if self.rampingCheckbox.isChecked():
            self.temperatureController.ramping_on()
        else:
            self.temperatureController.ramping_off()

    def update_gradient(self):
        print("update_gradient")
        self.temperatureController.set_gradient(float())

    def update_temp_control_enable(self):
        print("update_temp_control_enable")
        if self.tempControlButton.isChecked():
            self.temperatureController.ramping_on()
            self.tempControlButton.setText("Disable output")
        else:
            self.temperatureController.ramping_off()
            self.tempControlButton.setText("Enable output")

    def update_dosing_vectors(self):
        print("update_dosing_vectors")
        self.dosingValues = [float(x) for x in self.dosingValuesEdit.text().split(sep=',') if x.strip() != '']
        self.dosingTimes = [int(x) for x in self.dosingTimesEdit.text().split(sep=',') if x.strip() != '']

        # Since we will be using pop() to get the next values, we reverse the arrays
        self.dosingValues.reverse()
        self.dosingTimes.reverse()

        if len(self.dosingTimes) != len(self.dosingValues) or len(self.dosingTimes) * len(self.dosingValues) == 0:
            self.dosingTimesEdit.setStyleSheet("color: red;")
            self.dosingValuesEdit.setStyleSheet("color: red;")
            self.dosingControlButton.setEnabled(False)
        else:
            self.dosingTimesEdit.setStyleSheet(self.defaultStyleSheet)
            self.dosingValuesEdit.setStyleSheet(self.defaultStyleSheet)
            self.dosingControlButton.setEnabled(True)

    def update_dosing_label_timer(self):
        print("update_dosing_label_timer")

    def update_dosing_label_value(self):
        print("update_dosing_enable")

    def update_dosing_enable(self):
        print("update_dosing_enable")
        if self.dosingControlButton.isChecked():
            self.dosingValuesEdit.setEnabled(False)
            self.dosingValuesEdit.setStyleSheet("color: grey")
            self.dosingTimesEdit.setEnabled(False)
            self.dosingTimesEdit.setStyleSheet("color: grey")
            self.dosingControlButton.setText("Disable dosing")
            self.setpointEdit.setEnabled(False)
        else:
            self.dosingValuesEdit.setEnabled(True)
            self.dosingValuesEdit.setStyleSheet(self.defaultStyleSheet)
            self.dosingTimesEdit.setEnabled(True)
            self.dosingTimesEdit.setStyleSheet(self.defaultStyleSheet)
            self.dosingControlButton.setText("Enable dosing")
            self.setpointEdit.setEnabled(True)

    def update_plot(self):
        self.graph.clear()
        self.get_measurement()
        self.graph.plot(self.samplesPV, pen=pyqtgraph.mkPen((255, 127, 0), width=1.25))

        if self.dosingTimer is not None:
            self.dosingTimerLabel.setText(str(self.dosingTimer.remainingTime()))
        # pg.mkPen((0, 127, 255), width=1.25)

    def update_sensor1_group(self):
        if self.sensor1Group.isChecked():
            dg = SensorConfigDialog()
            dg.accepted.connect(self.connect_sensor1)
            # if unsuccessful, disable the temperature controller group
            if dg.exec_() == 0:
                self.sensor1Group.setChecked(False)
        else:
            self.sensor1.close()
            self.sensor1Timer.stop()

    # connect to sensor instance 1 using values returned by the dialog
    def connect_sensor1(self, values):
        self.sensor1 = Sensor(comport=values['port'],
                              baudrate=values['baudrate'],
                              databits=values['databits'],
                              parity=values['paritybits'],
                              stopbits=values['stopbits'],
                              datalen=values['datalen'],
                              dataHeader=values['header'])
        self.sensor1.open()
        self.sensor1Timer = QTimer()
        self.sensor1Timer.setInterval(1000)
        self.sensor1Timer.timeout.connect(self.sensor1_get_data)
        self.sensor1Timer.start()

    # Wrapper function to handle exceptions from GUI level
    def sensor1_get_data(self):
        try:
            self.sensor1.getData()
        except SerialException as se:
            dg = QErrorMessage()
            self.sensor1Group.setChecked(False)
            self.update_sensor1_group()
            dg.showMessage(f"Sensor 1 has encountered an exception: {se}")
            dg.exec_()

    def update_sensor2_group(self):
        if self.sensor2Group.isChecked():
            dg = SensorConfigDialog()
            dg.accepted.connect(self.connect_sensor2)
            # if unsuccessful, disable the temperature controller group
            if dg.exec_() == 0:
                self.sensor2Group.setChecked(False)
        else:
            self.sensor2.close()
            self.sensor2Timer.stop()

    # connect to sensor instance 2 using values returned by the dialog
    def connect_sensor2(self, values):
        self.sensor2 = Sensor(comport=values['port'],
                              baudrate=values['baudrate'],
                              databits=values['databits'],
                              parity=values['paritybits'],
                              stopbits=values['stopbits'],
                              datalen=values['datalen'],
                              dataHeader=values['header'])
        self.sensor2.open()
        self.sensor2Timer = QTimer()
        self.sensor2Timer.setInterval(1000)
        self.sensor2Timer.timeout.connect(self.sensor2_get_data)
        self.sensor2Timer.start()

    # Wrapper function to handle exceptions from GUI level
    def sensor2_get_data(self):
        try:
            self.sensor2.getData()
        except SerialException as se:
            dg = QErrorMessage()
            self.sensor2Group.setChecked(False)
            self.update_sensor2_group()
            dg.showMessage(f"Sensor 2 has encountered an exception: {se}")
            dg.exec_()

    def update_temperature_group(self):
        if self.tempControllerGroup.isChecked():
            dg = AR6X2ConfigDialog()
            dg.accepted.connect(self.connect_temp_controller)
            # if unsuccessful, disable the temperature controller group
            if dg.exec_() == 0:
                self.tempControllerGroup.setChecked(False)
        else:
            self.temperatureController.turn_off()
            self.tempControlButton.setText("Enable output")

    # Connect to the AR6X2 controller using given parameters
    def connect_temp_controller(self, values):
        self.temperatureController = AR6X2(port=values['port'], address=values['address'])

    def create_left_column(self):
        # Create a vertical layout for the left column
        leftColumnLayout = QVBoxLayout()

        # Valve override group
        vorGroup = QGroupBox("Valve override")
        vorLayout = QVBoxLayout()

        layout = QHBoxLayout()

        self.vorNormalButton = QPushButton("Normal")
        self.vorNormalButton.setMinimumWidth(50)
        self.vorNormalButton.setFixedHeight(75)
        self.vorNormalButton.setCheckable(True)
        self.vorNormalButton.setChecked(True)
        self.vorNormalButton.clicked.connect(self.update_vor_normal)

        self.vorClosedButton = QPushButton("Closed")
        self.vorClosedButton.setMinimumWidth(50)
        self.vorClosedButton.setFixedHeight(75)
        self.vorClosedButton.setCheckable(True)
        self.vorClosedButton.clicked.connect(self.update_vor_closed)

        self.vorOpenButton = QPushButton("Open")
        self.vorOpenButton.setMinimumWidth(50)
        self.vorOpenButton.setFixedHeight(75)
        self.vorOpenButton.setCheckable(True)
        self.vorOpenButton.clicked.connect(self.update_vor_open)

        layout.addWidget(self.vorNormalButton)
        layout.addWidget(self.vorClosedButton)
        layout.addWidget(self.vorOpenButton)

        vorLayout.addLayout(layout)
        vorGroup.setLayout(vorLayout)
        vorGroup.setMaximumWidth(ControllerGUITab.LEFT_COLUMN_MAX_WIDTH)
        leftColumnLayout.addWidget(vorGroup, alignment=Qt.AlignTop)

        # Process configuration group
        processGroup = QGroupBox("Process configuration")
        processLayout = QFormLayout()

        self.gasDropdown = QComboBox()
        self.gasDropdown.addItems(Controller.GAS_TYPES.keys())
        self.gasDropdown.currentTextChanged.connect(self.update_gas_type)

        self.pvFullScaleEdit = QLineEdit()
        self.pvFullScaleEdit.setText("100.000")
        self.pvFullScaleEdit.setValidator(QRegExpValidator(QRegExp("(-|)[0-9]{1,3}(|\\.[0-9]{1,3})")))
        self.pvFullScaleEdit.editingFinished.connect(self.update_pv_full_scale)

        self.pvSigtypeDropdown = QComboBox()
        self.pvSigtypeDropdown.addItems(Controller.INPUT_PORT_TYPES.keys())
        self.pvSigtypeDropdown.currentTextChanged.connect(self.update_pv_signal_type)

        self.spFullScaleEdit = QLineEdit()
        self.spFullScaleEdit.setText("100.000")
        self.spFullScaleEdit.setValidator(QRegExpValidator(QRegExp("(-|)[0-9]{1,3}(|\\.[0-9]{1,3})")))
        self.spFullScaleEdit.editingFinished.connect(self.update_sp_full_scale)

        self.spSigtypeDropdown = QComboBox()
        self.spSigtypeDropdown.addItems(Controller.OUTPUT_PORT_TYPES.keys())
        self.spSigtypeDropdown.currentTextChanged.connect(self.update_sp_signal_type)

        self.spSourceDropdown = QComboBox()
        self.spSourceDropdown.addItems(Controller.SP_SOURCES.keys())
        self.spSourceDropdown.currentTextChanged.connect(self.update_source)

        self.decimalDropdown = QComboBox()
        self.decimalDropdown.addItems(Controller.DECIMAL_POINTS.keys())
        self.decimalDropdown.currentTextChanged.connect(self.update_decimal_point)

        self.measureUnitsDropdown = QComboBox()
        self.measureUnitsDropdown.addItems(Controller.MEASUREMENT_UNITS.keys())
        self.measureUnitsDropdown.currentTextChanged.connect(self.update_measure_units)

        self.timebaseDropdown = QComboBox()
        self.timebaseDropdown.addItems(Controller.RATE_TIME_BASE.keys())
        self.timebaseDropdown.currentTextChanged.connect(self.update_time_base)

        processLayout.addRow(QLabel("Gas"), self.gasDropdown)
        processLayout.addRow(QLabel("PV Full Scale"), self.pvFullScaleEdit)
        processLayout.addRow(QLabel("PV Signal Type"), self.pvSigtypeDropdown)
        processLayout.addRow(QLabel("SP Full Scale"), self.spFullScaleEdit)
        processLayout.addRow(QLabel("SP Signal Type"), self.spSigtypeDropdown)
        processLayout.addRow(QLabel("Setpoint source"), self.spSourceDropdown)
        processLayout.addRow(QLabel("Decimal point"), self.decimalDropdown)
        processLayout.addRow(QLabel("Measurement units"), self.measureUnitsDropdown)
        processLayout.addRow(QLabel("Time base"), self.timebaseDropdown)

        processGroup.setLayout(processLayout)
        processGroup.setMaximumWidth(ControllerGUITab.LEFT_COLUMN_MAX_WIDTH)
        leftColumnLayout.addWidget(processGroup, alignment=Qt.AlignTop)
        leftColumnLayout.setStretch(1, 100)

        runtimeGroup = QGroupBox("Runtime options")
        runtimeLayout = QVBoxLayout()

        layout = QHBoxLayout()

        self.bufferSizeEdit = QLineEdit()
        self.bufferSizeEdit.setText("64")
        self.bufferSizeEdit.setValidator(QRegExpValidator(QRegExp("[0-9]*")))
        self.bufferSizeEdit.editingFinished.connect(self.update_buffer_size)

        layout.addWidget(QLabel("Sample buffer size"))
        layout.addWidget(self.bufferSizeEdit)
        layout.addWidget(QLabel("samples"))

        runtimeLayout.addLayout(layout)

        layout = QHBoxLayout()

        self.intervalEdit = QLineEdit()
        self.intervalEdit.setText("500")
        self.intervalEdit.setValidator(QRegExpValidator(QRegExp("[0-9]*.[0-9]*")))
        self.intervalEdit.editingFinished.connect(self.update_graph_timer)

        layout.addWidget(QLabel("Data update interval"))
        layout.addWidget(self.intervalEdit)
        layout.addWidget(QLabel("milliseconds"))

        runtimeLayout.addLayout(layout)

        layout = QHBoxLayout()

        self.setpointEdit = QLineEdit()
        self.setpointEdit.setText("1")
        self.setpointEdit.setValidator(QRegExpValidator(QRegExp("[0-9]*.[0-9]*")))
        self.setpointEdit.editingFinished.connect(self.update_setpoint)

        self.setpointUnitsLabel = QLabel("ml/sec")

        layout.addWidget(QLabel("Setpoint"))
        layout.addWidget(self.setpointEdit)
        layout.addWidget(self.setpointUnitsLabel)

        runtimeLayout.addLayout(layout)

        layout = QHBoxLayout()

        manualMeasureButton = QPushButton("Get measurement")
        manualMeasureButton.clicked.connect(self.update_plot)
        saveCsvButton = QPushButton("Save to CSV")
        saveCsvButton.clicked.connect(self.save_to_csv)

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
        self.sensor1Group = QGroupBox("Sensor 1")
        self.sensor1Group.setCheckable(True)
        self.sensor1Group.setChecked(False)
        self.sensor1Group.clicked.connect(self.update_sensor1_group)
        sensor1Layout = QVBoxLayout()

        layout = QHBoxLayout()

        self.sensor1SampleIntervalEdit = QLineEdit()
        self.sensor1SampleIntervalEdit.setValidator(QIntValidator())
        self.sensor1SampleIntervalEdit.setFixedWidth(100)
        self.sensor1SampleIntervalEdit.editingFinished.connect(self.update_sensor1_timer)
        self.sensor1SampleIntervalEdit.setText("1000")

        label = QLabel('Sampling interval')
        label.setFixedWidth(90)
        layout.addWidget(label)
        layout.addWidget(self.sensor1SampleIntervalEdit)
        layout.addWidget(QLabel('milliseconds'))
        layout.setStretch(2, 10)
        sensor1Layout.addLayout(layout)

        layout = QHBoxLayout()

        self.sensor1BufferSizeEdit = QLineEdit()
        self.sensor1BufferSizeEdit.setValidator(QIntValidator())
        self.sensor1BufferSizeEdit.setFixedWidth(100)
        self.sensor1BufferSizeEdit.editingFinished.connect(self.update_sensor1_buffer)
        self.sensor1BufferSizeEdit.setText("64")

        label = QLabel('Buffer size')
        label.setFixedWidth(90)
        layout.addWidget(label)
        layout.addWidget(self.sensor1BufferSizeEdit)
        layout.addWidget(QLabel('samples'))
        layout.setStretch(2, 10)
        sensor1Layout.addLayout(layout)
        self.sensor1Group.setLayout(sensor1Layout)

        # Creation of sensor 2 and sub-elements
        self.sensor2Group = QGroupBox("Sensor 2")
        self.sensor2Group.setCheckable(True)
        self.sensor2Group.setChecked(False)
        self.sensor2Group.clicked.connect(self.update_sensor2_group)
        sensor2Layout = QVBoxLayout()

        layout = QHBoxLayout()

        self.sensor2SampleIntervalEdit = QLineEdit()
        self.sensor2SampleIntervalEdit.setValidator(QIntValidator())
        self.sensor2SampleIntervalEdit.setFixedWidth(100)
        self.sensor2SampleIntervalEdit.editingFinished.connect(self.update_sensor2_timer)
        self.sensor2SampleIntervalEdit.setText("1000")

        label = QLabel('Sampling interval')
        label.setFixedWidth(90)
        layout.addWidget(label)
        layout.addWidget(self.sensor2SampleIntervalEdit)
        layout.addWidget(QLabel('milliseconds'))
        layout.setStretch(2, 10)
        sensor2Layout.addLayout(layout)

        layout = QHBoxLayout()

        self.sensor2BufferSizeEdit = QLineEdit()
        self.sensor2BufferSizeEdit.setValidator(QIntValidator())
        self.sensor2BufferSizeEdit.setFixedWidth(100)
        self.sensor2BufferSizeEdit.editingFinished.connect(self.update_sensor2_buffer)
        self.sensor2BufferSizeEdit.setText("64")

        label = QLabel('Buffer size')
        label.setFixedWidth(90)
        layout.addWidget(label)
        layout.addWidget(self.sensor2BufferSizeEdit)
        layout.addWidget(QLabel('samples'))
        layout.setStretch(2, 10)
        sensor2Layout.addLayout(layout)
        self.sensor2Group.setLayout(sensor2Layout)

        # TODO: Add temperature readout
        self.tempControllerGroup = QGroupBox("Temperature controller")
        self.tempControllerGroup.setCheckable(True)
        self.tempControllerGroup.setChecked(False)
        self.tempControllerGroup.clicked.connect(self.update_temperature_group)
        tempControllerLayout = QVBoxLayout()

        layout = QHBoxLayout()

        self.temperatureSlider = QSlider(Qt.Horizontal)
        self.temperatureSlider.setMinimumWidth(95)
        self.temperatureSlider.setMaximumWidth(1000)
        self.temperatureSlider.setMinimum(-199.9)
        self.temperatureSlider.setMaximum(850.0)
        self.temperatureSlider.setValue(100)
        self.temperatureSlider.sliderMoved.connect(self.update_temperature)
        self.temperatureLabel = QLabel("100")
        layout.addWidget(QLabel("Temperature"), alignment=Qt.AlignLeft)
        layout.addWidget(self.temperatureSlider, alignment=Qt.AlignLeft)
        layout.addWidget(self.temperatureLabel, alignment=Qt.AlignLeft)
        layout.addWidget(QLabel("℃"), alignment=Qt.AlignLeft)

        layout.setStretch(3, 200)
        tempControllerLayout.addLayout(layout)

        # these edits have validators, but input still has to be capped
        # Also, the validator seems overly complex if we cap the value anyway
        layout = QHBoxLayout()
        self.rangeLowEdit = QLineEdit()
        self.rangeLowEdit.setMinimumWidth(30)
        self.rangeLowEdit.setMaximumWidth(60)
        self.rangeLowEdit.setText("-199.9")
        self.rangeLowEdit.setValidator(
            QRegExpValidator(QRegExp("(-[0-9]{1,3}\\.[0-9]|[0-9]{1,3}\\.[0-9|[0-9]{1,4})")))
        self.rangeLowEdit.editingFinished.connect(self.update_range_low)

        self.rangeHighEdit = QLineEdit()
        self.rangeHighEdit.setMinimumWidth(30)
        self.rangeHighEdit.setMaximumWidth(60)
        self.rangeHighEdit.setText("850.0")
        self.rangeHighEdit.setValidator(
            QRegExpValidator(QRegExp("(-[0-9]{1,3}\\.[0-9]|[0-9]{1,3}\\.[0-9|[0-9]{1,4})")))
        self.rangeHighEdit.editingFinished.connect(self.update_range_high)

        layout.addWidget(QLabel("Range"))
        layout.addWidget(self.rangeLowEdit, alignment=Qt.AlignLeft)
        layout.addWidget(self.rangeHighEdit, alignment=Qt.AlignLeft)
        layout.addWidget(QLabel("℃"))
        layout.setStretch(3, 10)
        tempControllerLayout.addLayout(layout)

        self.rampingCheckbox = QCheckBox()
        self.rampingCheckbox.stateChanged.connect(self.update_ramping_enable)

        layout = QHBoxLayout()
        layout.addWidget(QLabel("Ramping"), alignment=Qt.AlignLeft)
        layout.addWidget(self.rampingCheckbox, alignment=Qt.AlignLeft)
        layout.setStretch(1, 10)

        tempControllerLayout.addLayout(layout)

        layout = QHBoxLayout()

        self.gradientEdit = QLineEdit()
        self.gradientEdit.setMinimumWidth(30)
        self.gradientEdit.setMaximumWidth(60)
        self.gradientEdit.setText("0.1")  # default value from the datasheet
        self.gradientEdit.editingFinished.connect(self.update_gradient)

        self.tempControlButton = QPushButton("Enable output")
        self.tempControlButton.setCheckable(True)
        self.tempControlButton.clicked.connect(self.update_temp_control_enable)

        layout.addWidget(QLabel("Gradient"), alignment=Qt.AlignLeft)
        layout.addWidget(self.gradientEdit, alignment=Qt.AlignLeft)
        layout.addWidget(QLabel("℃/min"))
        layout.addWidget(self.tempControlButton, alignment=Qt.AlignBottom)
        layout.setStretch(2, 10)

        tempControllerLayout.addLayout(layout)

        self.tempControllerGroup.setLayout(tempControllerLayout)
        self.tempControllerGroup.setMinimumWidth(200)
        self.tempControllerGroup.setFixedHeight(150)

        dosingGroup = QGroupBox("Dosing control")
        dosingGroup.setCheckable(True)
        dosingGroup.setChecked(False)
        dosingLayout = QVBoxLayout()

        layout = QHBoxLayout()
        self.dosingTimesEdit = QLineEdit()
        self.dosingTimesEdit.setMinimumWidth(160)
        self.dosingTimesEdit.setText("1000, 10000, 15000")
        self.dosingTimesEdit.setValidator(QRegExpValidator(QRegExp("([0-9]+,(| ))+")))
        self.dosingTimesEdit.textChanged.connect(self.update_dosing_vectors)

        label = QLabel("Times")
        label.setFixedWidth(55)

        layout.addWidget(label)
        layout.addWidget(self.dosingTimesEdit)
        layout.addWidget(QLabel("milliseconds"))
        dosingLayout.addLayout(layout)

        layout = QHBoxLayout()
        self.dosingValuesEdit = QLineEdit()
        self.dosingValuesEdit.setMinimumWidth(160)
        self.dosingValuesEdit.setText("1.0, 2.0, 5.0")
        self.dosingValuesEdit.setValidator(QRegExpValidator(QRegExp("(([0-9]+|[0-9]+\\.[0-9]+),(| ))+")))
        self.dosingValuesEdit.textChanged.connect(self.update_dosing_vectors)

        label = QLabel("Setpoints")
        label.setFixedWidth(55)

        self.dosingUnitsLabel = QLabel("ml/sec")

        layout.addWidget(label)
        layout.addWidget(self.dosingValuesEdit)
        layout.addWidget(self.dosingUnitsLabel)
        dosingLayout.addLayout(layout)

        self.dosingTimerLabel = QLabel("Dosing disabled")
        self.dosingValueLabel = QLabel("")

        self.dosingControlButton = QPushButton("Start dosing")
        self.dosingControlButton.setCheckable(True)
        self.dosingControlButton.clicked.connect(self.update_dosing_enable)

        dosingLayout.addWidget(self.dosingTimerLabel, alignment=Qt.AlignLeft)
        layout = QHBoxLayout()
        layout.addWidget(self.dosingValueLabel, alignment=Qt.AlignLeft)
        layout.addWidget(self.dosingControlButton, alignment=Qt.AlignRight)

        dosingLayout.addLayout(layout)

        # finally, assign the layout to the group
        dosingGroup.setLayout(dosingLayout)
        dosingGroup.setMinimumWidth(200)
        dosingGroup.setFixedHeight(150)

        rightInnerGrid.addWidget(self.sensor1Group, 0, 0)
        rightInnerGrid.addWidget(self.sensor2Group, 0, 1)
        rightInnerGrid.addWidget(self.tempControllerGroup, 1, 0)
        rightInnerGrid.addWidget(dosingGroup, 1, 1)

        rightInnerGrid.setColumnStretch(0, 100)
        rightInnerGrid.setColumnStretch(1, 100)

        self.graph = PlotWidget()
        self.graph.getPlotItem().showGrid(x=True, y=True, alpha=1)
        if "qdarkstyle" in sys.modules:
            self.graph.setBackground((25, 35, 45))
        self.graph.plot([0, 1, 2, 3], [5, 5, 5, 5])

        rightGridLayout.addWidget(self.graph)
        rightGridLayout.addLayout(rightInnerGrid)
        # Add some checkboxes to the layout
        rightColumnLayout.addLayout(rightGridLayout, 0, 1)

        return rightColumnLayout

    # function to change the amount of stored samples without losing previously gathered samples
    def change_buffer_size(self, value):
        if value > self.sampleBufferSize:
            newBufPV = RingBuffer(capacity=value, dtype=np.int16)
            newBufTotal = RingBuffer(capacity=value, dtype=np.int16)
            newTimestampBuf = RingBuffer(capacity=value, dtype=np.uint64)

            newBufPV.extend(self.samplesPV)
            newBufTotal.extend(self.samplesTotalizer)
            newTimestampBuf.extend(self.sampleTimestamps)

            self.samplesPV = newBufPV
            self.samplesTotalizer = newBufTotal
            self.sampleTimestamps = newTimestampBuf
        elif value < self.sampleBufferSize:
            newBufPV = RingBuffer(capacity=value, dtype=np.int16)
            newBufTotal = RingBuffer(capacity=value, dtype=np.int16)
            newTimestampBuf = RingBuffer(capacity=value, dtype=np.uint64)

            newBufPV.extend(self.samplesPV[:-value])
            newBufTotal.extend(self.samplesTotalizer[:-value])
            newTimestampBuf.extend(self.sampleTimestamps[:-value])

            self.samplesPV = newBufPV
            self.samplesTotalizer = newBufTotal
            self.sampleTimestamps = newTimestampBuf

    # Interpretation of saved values depends on the measurement units, time base and decimal point
    # Since we would have to add those to every single sample it would increase memory usage
    # and would force the user to manually convert the values in case of a change, we just wipe the buffers
    # Also, I think that those parameters should be set at the beginning of the process
    # and they wouldn't be changed mid process.
    def wipe_buffers(self):
        self.samplesPV = RingBuffer(capacity=self.sampleBufferSize, dtype=np.int16)
        self.samplesTotalizer = RingBuffer(capacity=self.sampleBufferSize, dtype=np.int16)
        self.sampleTimestamps = RingBuffer(capacity=self.sampleBufferSize, dtype=np.uint64)
