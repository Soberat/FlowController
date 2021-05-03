import pyqtgraph
from PyQt5.QtCore import Qt, QTimer, QRegExp
from PyQt5.QtGui import QRegExpValidator, QIntValidator
from PyQt5.QtWidgets import (
    QCheckBox,
    QLineEdit,
    QVBoxLayout,
    QWidget, QHBoxLayout, QGridLayout, QGroupBox, QSlider, QLabel, QPushButton, QFormLayout, QComboBox,
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


# TODO: Getting values from serial, and not assuming defaults
# TODO: Handler functions
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

        self.intervalEdit = None
        self.bufferSizeEdit = None
        self.setpointEdit = None

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

    def update_buffer_size(self):
        self.change_buffer_size(int(self.bufferSizeEdit.text()))
        self.sampleBufferSize = int(self.bufferSizeEdit.text())

    def update_graph_timer(self):
        self.graphTimer.setInterval(int(self.intervalEdit.text()))

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
        if self.sensor1 is not None and self.sensor1.buffer.count() > 0:
            file.write(f"Sensor 1 header: {self.sensor1.header}\n")
            for i in range(0, self.sensor1.buffer.count()):
                file.write(self.sensor1.buffer[i] + '\n')
        file.write('\n')

        if self.sensor2 is not None and self.sensor2.buffer.count() > 0:
            file.write(f"Sensor 2 header: {self.sensor2.header}\n")
            for i in range(0, self.sensor2.buffer.count()):
                file.write(self.sensor2.buffer[i] + '\n')

        file.close()

    def update_setpoint(self):
        value = float(self.setpointEdit.text())
        self.controller.set_setpoint(value)

    def update_plot(self):
        self.graph.clear()
        self.get_measurement()
        self.graph.plot(self.samplesPV, pen=pyqtgraph.mkPen((255, 127, 0), width=1.25))
        # pg.mkPen((0, 127, 255), width=1.25)

    # TODO: setup timer to get data from sensors
    def create_sensor1_dialog(self):
        dg = SensorConfigDialog()
        dg.accepted.connect(self.connect_sensor1)
        # if unsuccessful, disable the temperature controller group
        if dg.exec_() == 0:
            self.sensor1Group.setChecked(False)

    # connect to sensor instance 1 using values returned by the dialog
    def connect_sensor1(self, values):
        self.sensor1 = Sensor(comport=values['port'],
                              baudrate=values['baudrate'],
                              databits=values['databits'],
                              parity=values['paritybits'],
                              stopbits=values['stopbits'],
                              dataHeader=values['header'])

    def create_sensor2_dialog(self):
        dg = SensorConfigDialog()
        dg.accepted.connect(self.connect_sensor2)
        # if unsuccessful, disable the temperature controller group
        if dg.exec_() == 0:
            self.sensor2Group.setChecked(False)

    # connect to sensor instance 2 using values returned by the dialog
    def connect_sensor2(self, values):
        self.sensor2 = Sensor(comport=values['port'],
                              baudrate=values['baudrate'],
                              databits=values['databits'],
                              parity=values['paritybits'],
                              stopbits=values['stopbits'],
                              dataHeader=values['header'])

    def create_temperature_dialog(self):
        dg = AR6X2ConfigDialog()
        dg.accepted.connect(self.connect_temp_controller)
        # if unsuccessful, disable the temperature controller group
        if dg.exec_() == 0:
            self.tempControllerGroup.setChecked(False)

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

        # TODO: on check, uncheck others
        vorNormalButton = QPushButton("Normal")
        vorNormalButton.setMinimumWidth(50)
        vorNormalButton.setFixedHeight(75)
        vorNormalButton.setCheckable(True)
        vorNormalButton.setChecked(True)

        vorClosedButton = QPushButton("Closed")
        vorClosedButton.setMinimumWidth(50)
        vorClosedButton.setFixedHeight(75)
        vorClosedButton.setCheckable(True)

        vorOpenButton = QPushButton("Open")
        vorOpenButton.setMinimumWidth(50)
        vorOpenButton.setFixedHeight(75)
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

        unitsLabel = QLabel("mu/tb")

        layout.addWidget(QLabel("Setpoint"))
        layout.addWidget(self.setpointEdit)
        layout.addWidget(unitsLabel)

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
        self.sensor1Group.clicked.connect(self.create_sensor1_dialog)
        sensor1Layout = QVBoxLayout()

        layout = QHBoxLayout()

        sensor1SampleIntervalEdit = QLineEdit()
        sensor1SampleIntervalEdit.setValidator(QIntValidator())
        sensor1SampleIntervalEdit.setFixedWidth(100)
        label = QLabel('milliseconds')

        layout.addWidget(QLabel('Sampling interval'))
        layout.addWidget(sensor1SampleIntervalEdit)
        layout.addWidget(label)
        sensor1Layout.addLayout(layout)

        layout = QHBoxLayout()

        sensor1BufferSizeEdit = QLineEdit()
        sensor1BufferSizeEdit.setValidator(QIntValidator())
        sensor1BufferSizeEdit.setFixedWidth(100)
        label = QLabel('samples')

        layout.addWidget(QLabel('Buffer size'))
        layout.addWidget(sensor1BufferSizeEdit)
        layout.addWidget(label)
        sensor1Layout.addLayout(layout)
        self.sensor1Group.setLayout(sensor1Layout)

        # Creation of sensor 2 and sub-elements
        self.sensor2Group = QGroupBox("Sensor 2")
        self.sensor2Group.setCheckable(True)
        self.sensor2Group.setChecked(False)
        self.sensor2Group.clicked.connect(self.create_sensor2_dialog)
        sensor2Layout = QVBoxLayout()

        layout = QHBoxLayout()

        sensor2SampleIntervalEdit = QLineEdit()
        sensor2SampleIntervalEdit.setValidator(QIntValidator())
        sensor2SampleIntervalEdit.setFixedWidth(100)
        label = QLabel('milliseconds')

        layout.addWidget(QLabel('Sampling interval'))
        layout.addWidget(sensor2SampleIntervalEdit)
        layout.addWidget(label)
        sensor2Layout.addLayout(layout)

        layout = QHBoxLayout()

        sensor2BufferSizeEdit = QLineEdit()
        sensor2BufferSizeEdit.setValidator(QIntValidator())
        sensor2BufferSizeEdit.setFixedWidth(100)
        label = QLabel('samples')

        layout.addWidget(QLabel('Buffer size'))
        layout.addWidget(sensor2BufferSizeEdit)
        layout.addWidget(label)
        sensor2Layout.addLayout(layout)
        self.sensor2Group.setLayout(sensor2Layout)

        # TODO: Add address and comport fields
        self.tempControllerGroup = QGroupBox("Temperature controller")
        self.tempControllerGroup.setCheckable(True)
        self.tempControllerGroup.setChecked(False)
        self.tempControllerGroup.clicked.connect(self.create_temperature_dialog)
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
        tempControllerLowEdit.setValidator(
            QRegExpValidator(QRegExp("(-[0-9]{1,3}\\.[0-9]|[0-9]{1,3}\\.[0-9|[0-9]{1,4})")))

        tempControllerHighEdit = QLineEdit()
        tempControllerHighEdit.setMinimumWidth(30)
        tempControllerHighEdit.setMaximumWidth(60)
        tempControllerHighEdit.setText("850.0")
        tempControllerHighEdit.setValidator(
            QRegExpValidator(QRegExp("(-[0-9]{1,3}\\.[0-9]|[0-9]{1,3}\\.[0-9|[0-9]{1,4})")))

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

        self.tempControllerGroup.setLayout(tempControllerLayout)
        self.tempControllerGroup.setMinimumWidth(200)
        self.tempControllerGroup.setFixedHeight(150)

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
        label.setFixedWidth(80)

        layout.addWidget(label, alignment=Qt.AlignLeft)
        layout.addWidget(dosingTimesEdit, alignment=Qt.AlignLeft)
        layout.setStretch(1, 10)
        dosingLayout.addLayout(layout)

        layout = QHBoxLayout()
        dosingValuesEdit = QLineEdit()
        dosingValuesEdit.setMinimumWidth(200)
        dosingValuesEdit.setText("1.0, 2.0, 5.0")
        dosingValuesEdit.setValidator(QRegExpValidator(QRegExp("([0-9]{1,3}\\.[0-9]{1,3},(| ))+")))

        label = QLabel("Setpoint values")
        label.setFixedWidth(80)

        layout.addWidget(label, alignment=Qt.AlignLeft)
        layout.addWidget(dosingValuesEdit, alignment=Qt.AlignLeft)
        layout.setStretch(1, 10)
        dosingLayout.addLayout(layout)

        nextTimeLabel = QLabel("10 seconds until next dose")
        nextDoseLabel = QLabel("Next dose value: 50")

        # TODO: lock above elements after starting
        dosingButton = QPushButton("Start dosing")
        dosingButton.setCheckable(True)

        dosingLayout.addWidget(nextTimeLabel, alignment=Qt.AlignLeft)
        layout = QHBoxLayout()
        layout.addWidget(nextDoseLabel, alignment=Qt.AlignLeft)
        layout.addWidget(dosingButton, alignment=Qt.AlignRight)

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
