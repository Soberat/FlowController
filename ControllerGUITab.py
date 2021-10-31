import sys
import pyqtgraph
from PyQt5.QtCore import Qt, QTimer, QRegExp, pyqtSignal
from PyQt5.QtGui import QRegExpValidator, QIntValidator, QIcon
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
import re
import resources


class ControllerGUITab(QWidget):
    LEFT_COLUMN_MAX_WIDTH = 400

    # This signal tells the global tab if is not possible to start dosing for this tab
    # False is sent out when the dosing vectors are incorrect or when the process is already started
    dosingSignal = pyqtSignal(bool)

    # This just signals if saving was enabled/disabled by the user in the tab, so the global tab can update itself
    savingSignal = pyqtSignal(bool)

    def __init__(self, controller: Controller):
        super().__init__()
        # Create the master layout
        outerLayout = QGridLayout()
        self.graph = None
        self.controller = controller
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
        self.saveCsvButton = None

        self.sensor1Timer = None
        self.sensor1SampleIntervalEdit = None
        self.sensor1BufferSizeEdit = None

        self.sensor2Timer = None
        self.sensor2SampleIntervalEdit = None
        self.sensor2BufferSizeEdit = None

        self.temperatureSlider = None
        self.temperatureLabel = None
        self.tempReadoutLabel = None
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
        self.dosingLabel = None
        self.dosingVorStateLabel = None
        self.dosingControlButton = None
        self.dosingEnabled = False

        # Data buffers
        self.sampleBufferSize = 64
        self.samplesPV = RingBuffer(capacity=self.sampleBufferSize, dtype=np.float16)
        self.samplesTotalizer = RingBuffer(capacity=self.sampleBufferSize, dtype=np.float32)
        self.sampleTimestamps = RingBuffer(capacity=self.sampleBufferSize, dtype=datetime)

        # Nest the inner layouts into the outer layout
        outerLayout.addLayout(self.create_left_column(), 0, 0)
        outerLayout.addLayout(self.create_right_column(), 0, 1)
        # Set the window's main layout
        self.setLayout(outerLayout)

        # Generic timer that calls generic_update every second
        # Used to update a few labels
        self.genericTimer = QTimer()
        self.genericTimer.timeout.connect(self.update_generic)
        self.genericTimer.start(1000)

        self.graphTimer = QTimer()
        self.graphTimer.timeout.connect(self.update_plot)
        self.graphTimer.start(int(60*1000*float(self.intervalEdit.text())))

        self.dosingValue = None
        self.dosingTimer = QTimer()
        self.dosingTimer.timeout.connect(self.dosing_process)

        self.csvFile = None
        self.csvIterator = 1

        self.defaultStyleSheet = QLineEdit().styleSheet()

        # Current dosing value, used to set the setpoint edit
        # text correctly after a process shutdown
        self.spValue = 1.0

        # Get initial dosing values from the text inside
        self.dosingValues = [float(x) for x in self.dosingValuesEdit.text().split(sep=',') if x.strip() != '']
        self.dosingTimes = [float(x) * 60 * 1000 for x in self.dosingTimesEdit.text().split(sep=',') if x.strip() != '']
        self.dosingValues.reverse()
        self.dosingTimes.reverse()

    def get_measurement(self):
        # Proper implementation that gets the data from the device over serial
        current, total, timestamp = self.controller.get_measurements()
        if total is not None:
            self.samplesTotalizer.append(total)
            self.samplesPV.append(current)
            self.sampleTimestamps.append(timestamp)

    # Save samples to a csv file, named after the current time and controller number it is coming from
    # After this function saving is continued by update_plot function, which calls append_to_csv
    def save_to_csv_start(self):
        # If saving is invoked from global tab while it is already enabled, close the old file,
        # so no sensor data will be lost and the will be closed properly
        if self.csvFile is not None:
            self.save_to_csv_stop()
        filename = datetime.now().strftime(f"controller{self.controller.channel}_%Y-%m-%d_%H-%M-%S.csv")

        self.csvFile = open(filename, 'w')
        self.csvFile.write(
            f"Gas:{self.controller.get_gas()}\tDecimal point:{self.controller.get_decimal_point()},\tUnits:{self.controller.get_measurement_units()}/{self.controller.get_time_base()}\n")
        self.csvFile.write("{:<15} {:^18} {:>19}\n".format("Measurement", "Totalizer", "Time of measurement"))
        for i in range(0, len(self.samplesPV) - 1):
            self.csvFile.write("{:<15},{:^18},{:>19}\n".format(self.samplesPV[len(self.samplesPV) - 1],
                                                               self.samplesTotalizer[len(self.samplesPV) - 1],
                                                               self.sampleTimestamps[len(self.samplesPV) - 1].strftime(
                                                                   "%Y/%m/%d,%H:%M:%S")))

        self.saveCsvButton.clicked.disconnect()
        self.saveCsvButton.clicked.connect(self.save_to_csv_stop)
        self.saveCsvButton.setText("Stop saving to CSV")
        self.savingSignal.emit(True)

    def append_to_csv(self):
        # check if file is bigger than ~8MB
        if self.csvFile.tell() > 8192000:
            name = re.sub(r"(|_[0-9]+).csv", f"_{self.csvIterator}.csv",
                          self.csvFile.name.split("\\")[len(self.csvFile.name.split("\\")) - 1])
            self.csvIterator += 1
            self.append_sensor()
            self.csvFile.close()
            self.csvFile = open(name, 'w')
        self.csvFile.write("{:<15},{:^18},{:>19}\n".format(self.samplesPV[len(self.samplesPV) - 1],
                                                           self.samplesTotalizer[len(self.samplesPV) - 1],
                                                           self.sampleTimestamps[len(self.samplesPV) - 1].strftime(
                                                               "%Y/%m/%d,%H:%M:%S")))

    def save_to_csv_stop(self):
        self.append_sensor()
        self.csvFile.close()
        self.csvFile = None
        self.saveCsvButton.clicked.disconnect()
        self.saveCsvButton.clicked.connect(self.save_to_csv_start)
        self.saveCsvButton.setText("Start saving to CSV")
        self.csvIterator = 1
        self.savingSignal.emit(False)

    def append_sensor(self):
        # if available, append data from sensors
        if self.sensor1 is not None and len(self.sensor1.buffer) > 0:
            self.csvFile.write(f"Sensor 1 header: {self.sensor1.header}\n")
            for i in range(0, len(self.sensor1.buffer)):
                self.csvFile.write(str(self.sensor1.buffer[i]))
            self.sensor1.buffer.clear()
            self.csvFile.write('\n')

        if self.sensor2 is not None and len(self.sensor2.buffer) > 0:
            self.csvFile.write(f"Sensor 2 header: {self.sensor2.header}\n")
            for i in range(0, len(self.sensor2.buffer)):
                self.csvFile.write(str(self.sensor2.buffer[i]))
            self.sensor2.buffer.clear()

    # Handler functions for UI elements
    # TODO: react to returned value from functions
    def update_vor_normal(self):
        if self.vorNormalButton.isChecked():
            # disable other buttons to clarify which VOR state is active
            self.vorClosedButton.setChecked(False)
            self.vorOpenButton.setChecked(False)
            self.controller.set_valve_override(Controller.VOR_OPTION_NORMAL)
            self.dosingVorStateLabel.setText("VOR is normal")
            self.dosingVorStateLabel.setStyleSheet("color: green;")

    def update_vor_closed(self):
        if self.vorClosedButton.isChecked():
            self.vorNormalButton.setChecked(False)
            self.vorOpenButton.setChecked(False)
            self.controller.set_valve_override(Controller.VOR_OPTION_CLOSED)
            self.dosingVorStateLabel.setText("VOR is closed")
            self.dosingVorStateLabel.setStyleSheet("color: red;")

    def update_vor_open(self):
        if self.vorOpenButton.isChecked():
            self.vorClosedButton.setChecked(False)
            self.vorNormalButton.setChecked(False)
            self.controller.set_valve_override(Controller.VOR_OPTION_OPEN)
            self.dosingVorStateLabel.setText("VOR is open")
            self.dosingVorStateLabel.setStyleSheet("color: red;")

    def update_gas_type(self):
        self.controller.set_gas(self.gasDropdown.currentText())

    def update_pv_full_scale(self):
        self.controller.set_pv_full_scale(float(self.pvFullScaleEdit.text()))

    def update_pv_signal_type(self):
        self.controller.set_pv_signal_type(self.pvSigtypeDropdown.currentText())

    def update_sp_full_scale(self):
        self.controller.set_sp_full_scale(float(self.spFullScaleEdit.text()))

    def update_sp_signal_type(self):
        self.controller.set_sp_signal_type(self.spSigtypeDropdown.currentText())

    def update_source(self):
        self.controller.set_source(self.spSourceDropdown.currentText())

    def update_decimal_point(self):
        self.controller.set_decimal_point(self.decimalDropdown.currentText())

    def update_measure_units(self):
        if self.dosingUnitsLabel is not None:
            self.dosingUnitsLabel.setText(
                f"{self.measureUnitsDropdown.currentText()}/{self.timebaseDropdown.currentText()}")
        if self.setpointUnitsLabel is not None:
            self.setpointUnitsLabel.setText(
                f"{self.measureUnitsDropdown.currentText()}/{self.timebaseDropdown.currentText()}")
        self.controller.set_measurement_units(self.measureUnitsDropdown.currentText())

    def update_time_base(self):
        if self.dosingUnitsLabel is not None:
            self.dosingUnitsLabel.setText(
                f"{self.measureUnitsDropdown.currentText()}/{self.timebaseDropdown.currentText()}")
        if self.setpointUnitsLabel is not None:
            self.setpointUnitsLabel.setText(
                f"{self.measureUnitsDropdown.currentText()}/{self.timebaseDropdown.currentText()}")
        self.controller.set_time_base(self.timebaseDropdown.currentText())

    def update_buffer_size(self):
        self.change_buffer_size(int(self.bufferSizeEdit.text()))
        self.sampleBufferSize = int(self.bufferSizeEdit.text())

    def update_graph_timer(self):
        self.graphTimer.setInterval(float(self.intervalEdit.text()) * 60 * 1000)

    def update_setpoint(self):
        value = float(self.setpointEdit.text())
        self.controller.set_setpoint(value)

    def update_sensor1_timer(self):
        self.sensor1Timer.setInterval(float(self.sensor1SampleIntervalEdit.text()) * 60 * 1000)

    def update_sensor1_buffer(self):
        self.sensor1.change_buffer_size(int(self.sensor1BufferSizeEdit.text()))

    def update_sensor2_timer(self):
        self.sensor2Timer.setInterval(float(self.sensor2SampleIntervalEdit.text()) * 60 * 1000)

    def update_sensor2_buffer(self):
        self.sensor2.change_buffer_size(int(self.sensor2BufferSizeEdit.text()))

    def update_temperature(self):
        self.temperatureController.set_temperature(float(self.temperatureSlider.value()))
        self.temperatureLabel.setText(self.temperatureSlider.value())

    def update_range_low(self):
        newTemp = self.temperatureController.set_range_low(float(self.rangeLowEdit.text()))
        self.temperatureSlider.setMinimum(float(self.rangeLowEdit.text()))
        self.temperatureSlider.setValue(newTemp)

    def update_range_high(self):
        newTemp = self.temperatureController.set_range_high(float(self.rangeHighEdit.text()))
        self.temperatureSlider.setMaximum(float(self.rangeHighEdit.text()))
        self.temperatureSlider.setValue(newTemp)

    def update_ramping_enable(self):
        if self.rampingCheckbox.isChecked():
            self.temperatureController.ramping_on()
        else:
            self.temperatureController.ramping_off()

    def update_gradient(self):
        self.temperatureController.set_gradient(float())

    def update_temp_control_enable(self):
        if self.tempControlButton.isChecked():
            self.temperatureController.ramping_on()
            self.tempControlButton.setText("Disable output")
        else:
            self.temperatureController.ramping_off()
            self.tempControlButton.setText("Enable output")

    def update_dosing_vectors(self):
        self.dosingValues = [float(x) for x in self.dosingValuesEdit.text().split(sep=',') if x.strip() != '']
        self.dosingTimes = [float(x) * 1000 * 60 for x in self.dosingTimesEdit.text().split(sep=',') if x.strip() != '']

        # Since we will be using pop() to get the next values, we reverse the arrays
        self.dosingValues.reverse()
        self.dosingTimes.reverse()

        if len(self.dosingTimes) != len(self.dosingValues) or len(self.dosingTimes) * len(self.dosingValues) == 0:
            self.dosingTimesEdit.setStyleSheet("color: red;")
            self.dosingValuesEdit.setStyleSheet("color: red;")
            self.dosingControlButton.setEnabled(False)
            self.dosingSignal.emit(True)
        else:
            self.dosingTimesEdit.setStyleSheet(self.defaultStyleSheet)
            self.dosingValuesEdit.setStyleSheet(self.defaultStyleSheet)
            self.dosingControlButton.setEnabled(True)
            self.dosingSignal.emit(False)

    def update_dosing_state(self):
        if self.dosingControlButton.isChecked():
            self.dosingValuesEdit.setEnabled(False)
            self.dosingValuesEdit.setStyleSheet("color: grey")
            self.dosingTimesEdit.setEnabled(False)
            self.dosingTimesEdit.setStyleSheet("color: grey")
            self.dosingControlButton.setText("Disable dosing")
            self.setpointEdit.setEnabled(False)
            self.dosingEnabled = True
            self.dosingSignal.emit(True)
            # Set VOR to normal for dosing
            self.vorNormalButton.setChecked(True)
            self.update_vor_normal()
            self.dosing_process()
        else:
            self.dosingValuesEdit.setEnabled(True)
            self.dosingValuesEdit.setStyleSheet(self.defaultStyleSheet)
            self.dosingTimesEdit.setEnabled(True)
            self.dosingTimesEdit.setStyleSheet(self.defaultStyleSheet)
            self.dosingControlButton.setText("Enable dosing")
            self.setpointEdit.setEnabled(True)
            self.dosingEnabled = False
            self.end_dosing_process()

    # This function sets the setpoint to those values that were set when "Enable dosing" was pressed
    # and iterates over them
    def dosing_process(self):
        self.spValue = self.dosingValues.pop()
        spTime = self.dosingTimes.pop()

        self.setpointEdit.setText(f"{str(self.spValue)} - dosing is enabled")
        self.controller.set_setpoint(self.spValue)

        if len(self.dosingTimes) == 0:
            self.dosingTimer.timeout.disconnect()
            self.dosingTimer.singleShot(spTime, self.end_dosing_process)

        self.dosingTimer.setInterval(spTime)
        self.dosingTimer.start()

    def update_generic(self):
        if self.dosingTimer.isActive() and len(self.dosingValues) > 0:
            if self.dosingTimer.remainingTime() / 1000 > 60:
                self.dosingLabel.setText(
                    f"{int(self.dosingTimer.remainingTime() / (1000 * 60))} minutes {int(self.dosingTimer.remainingTime() / 1000) % 60} seconds until next dosing value: {self.dosingValues[-1]}")
            else:
                self.dosingLabel.setText(
                    f"{int(self.dosingTimer.remainingTime() / 1000)} seconds until next dosing value: {self.dosingValues[-1]}")
        elif self.dosingTimer.isActive() and len(self.dosingValues) == 0:
            self.dosingLabel.setText(f"{int(self.dosingTimer.remainingTime() / 1000)} seconds until end of process")
        else:
            self.dosingLabel.setText("Dosing disabled")

        if self.temperatureController is not None:
            self.tempReadoutLabel.setText(f"Readout: {self.temperatureController.read_temperature()} ℃")
        else:
            self.tempReadoutLabel.setText("Readout: None ℃")

    def end_dosing_process(self):
        self.dosingControlButton.setChecked(False)
        self.dosingControlButton.setText("Enable dosing")
        self.dosingLabel.setText("Dosing disabled")
        self.dosingTimer.stop()

        # Since all the values have been popped and the text is unchanged, we fill the vectors again
        self.dosingValues = [float(x) for x in self.dosingValuesEdit.text().split(sep=',') if x.strip() != '']
        self.dosingTimes = [float(x) * 60 * 1000 for x in self.dosingTimesEdit.text().split(sep=',') if x.strip() != '']
        self.dosingValues.reverse()
        self.dosingTimes.reverse()

        # Remove the string portion from setpoint field
        self.setpointEdit.setText(str(self.spValue))

        # Unlock the setpoint and dosing values/times fields
        self.setpointEdit.setEnabled(True)
        self.dosingValuesEdit.setEnabled(True)
        self.dosingTimesEdit.setEnabled(True)

        # Return to normal stylesheet
        self.dosingValuesEdit.setStyleSheet(self.defaultStyleSheet)
        self.dosingTimesEdit.setStyleSheet(self.defaultStyleSheet)

        # reconnect the dosing_process function to the timer
        self.dosingTimer.timeout.connect(self.dosing_process)

        # Set the setpoint to 0 and close valve at the end
        self.controller.set_setpoint(0)
        self.setpointEdit.setText("0")

        self.vorClosedButton.setChecked(True)
        self.dosingSignal.emit(False)
        self.update_vor_closed()

    def update_plot(self):
        self.graph.clear()
        self.get_measurement()
        self.graph.plot(self.samplesPV, pen=pyqtgraph.mkPen((255, 127, 0), width=1.25), symbolBrush=(255, 127, 0),
                        symbolPen=pyqtgraph.mkPen((255, 127, 0)), symbol='o', symbolSize=5, name="symbol ='o'")
        if self.csvFile is not None:
            self.append_to_csv()

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
            self.sensor1 = None

    # connect to sensor instance 1 using values returned by the dialog
    def connect_sensor1(self, values):
        self.sensor1 = Sensor(comport=values['port'],
                              baudrate=values['baudrate'],
                              databits=values['databits'],
                              parity=values['paritybits'],
                              stopbits=values['stopbits'],
                              dataHeader=values['header'])
        self.sensor1Timer = QTimer()
        self.sensor1Timer.setInterval(float(self.sensor1SampleIntervalEdit.text()) * 1000 * 60)
        self.sensor1Timer.timeout.connect(self.sensor1_get_data)
        self.sensor1Timer.start()

    # Wrapper function to handle exceptions from GUI level
    def sensor1_get_data(self):
        try:
            self.sensor1.getData()
        except SerialException as se:
            dg = QErrorMessage()
            dg.setWindowIcon(QIcon(':/icon.png'))
            dg.setWindowTitle("Sensor 1 Exception")

            filename = datetime.now().strftime("sensor1_%Y-%m-%d_%H-%M-%S.csv")
            dumpFile = open(filename, 'w')

            dumpFile.write(f"Sensor 1 header: {self.sensor1.header}\n")
            for i in range(0, len(self.sensor1.buffer)):
                self.csvFile.write(str(self.sensor1.buffer[i]))
            dumpFile.close()

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
            self.sensor2 = None

    # connect to sensor instance 2 using values returned by the dialog
    def connect_sensor2(self, values):
        self.sensor2 = Sensor(comport=values['port'],
                              baudrate=values['baudrate'],
                              databits=values['databits'],
                              parity=values['paritybits'],
                              stopbits=values['stopbits'],
                              dataHeader=values['header'])
        self.sensor2Timer = QTimer()
        self.sensor2Timer.setInterval(float(self.sensor2SampleIntervalEdit.text()) * 1000 * 60)
        self.sensor2Timer.timeout.connect(self.sensor2_get_data)
        self.sensor2Timer.start()

    # Wrapper function to handle exceptions from GUI level
    def sensor2_get_data(self):
        try:
            self.sensor2.getData()
        except SerialException as se:
            dg = QErrorMessage()
            dg.setWindowIcon(QIcon(':/icon.png'))
            dg.setWindowTitle("Sensor 2 Exception")

            filename = datetime.now().strftime("sensor2_%Y-%m-%d_%H-%M-%S.csv")
            dumpFile = open(filename, 'w')

            dumpFile.write(f"Sensor 2 header: {self.sensor2.header}\n")
            for i in range(0, len(self.sensor2.buffer)):
                self.csvFile.write(str(self.sensor2.buffer[i]))
            dumpFile.close()

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
            self.temperatureController = None
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

        vorState = self.controller.get_valve_override()
        if vorState == "Normal":
            self.vorNormalButton.setChecked(True)
            self.vorClosedButton.setChecked(False)
            self.vorOpenButton.setChecked(False)
        elif vorState == "Closed":
            self.vorNormalButton.setChecked(False)
            self.vorClosedButton.setChecked(True)
            self.vorOpenButton.setChecked(False)
        elif vorState == "Open":
            self.vorNormalButton.setChecked(False)
            self.vorClosedButton.setChecked(False)
            self.vorOpenButton.setChecked(True)
        else:
            raise ValueError(f"Unexpected vor state: {vorState}")

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
        self.gasDropdown.setCurrentText(str(self.controller.get_gas()))

        self.pvFullScaleEdit = QLineEdit()
        self.pvFullScaleEdit.setValidator(QRegExpValidator(QRegExp("(-|)[0-9]{1,3}(|\\.[0-9]{1,3})")))
        self.pvFullScaleEdit.editingFinished.connect(self.update_pv_full_scale)
        self.pvFullScaleEdit.setText(str(self.controller.get_pv_full_scale()))

        self.pvSigtypeDropdown = QComboBox()
        self.pvSigtypeDropdown.addItems(Controller.INPUT_PORT_TYPES.keys())
        self.pvSigtypeDropdown.currentTextChanged.connect(self.update_pv_signal_type)
        self.pvSigtypeDropdown.setCurrentText(str(self.controller.get_pv_signal_type()))

        self.spFullScaleEdit = QLineEdit()
        self.spFullScaleEdit.setValidator(QRegExpValidator(QRegExp("(-|)[0-9]{1,3}(|\\.[0-9]{1,3})")))
        self.spFullScaleEdit.editingFinished.connect(self.update_sp_full_scale)
        self.spFullScaleEdit.setText(str(self.controller.get_sp_full_scale()))

        self.spSigtypeDropdown = QComboBox()
        self.spSigtypeDropdown.addItems(Controller.OUTPUT_PORT_TYPES.keys())
        self.spSigtypeDropdown.currentTextChanged.connect(self.update_sp_signal_type)
        self.spSigtypeDropdown.setCurrentText(str(self.controller.get_sp_signal_type()))

        self.spSourceDropdown = QComboBox()
        self.spSourceDropdown.addItems(Controller.SP_SOURCES.keys())
        self.spSourceDropdown.currentTextChanged.connect(self.update_source)
        self.spSourceDropdown.setCurrentText(str(self.controller.get_source()))

        self.decimalDropdown = QComboBox()
        self.decimalDropdown.addItems(Controller.DECIMAL_POINTS.keys())
        self.decimalDropdown.currentTextChanged.connect(self.update_decimal_point)
        self.decimalDropdown.setCurrentText(str(self.controller.get_decimal_point()))

        self.measureUnitsDropdown = QComboBox()
        self.measureUnitsDropdown.addItems(Controller.MEASUREMENT_UNITS.keys())
        self.measureUnitsDropdown.currentTextChanged.connect(self.update_measure_units)
        self.measureUnitsDropdown.setCurrentText(str(self.controller.get_measurement_units()))

        self.timebaseDropdown = QComboBox()
        self.timebaseDropdown.addItems(Controller.RATE_TIME_BASE.keys())
        self.timebaseDropdown.currentTextChanged.connect(self.update_time_base)
        self.timebaseDropdown.setCurrentText(str(self.controller.get_time_base()))

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
        self.bufferSizeEdit.setValidator(QIntValidator())
        self.bufferSizeEdit.editingFinished.connect(self.update_buffer_size)

        layout.addWidget(QLabel("Sample buffer size"))
        layout.addWidget(self.bufferSizeEdit)
        layout.addWidget(QLabel("samples"))

        runtimeLayout.addLayout(layout)

        layout = QHBoxLayout()

        self.intervalEdit = QLineEdit()
        self.intervalEdit.setText("1")
        self.intervalEdit.setValidator(QRegExpValidator(QRegExp("[0-9]*(|\\.[0-9]*)")))
        self.intervalEdit.editingFinished.connect(self.update_graph_timer)

        layout.addWidget(QLabel("Data update interval"))
        layout.addWidget(self.intervalEdit)
        layout.addWidget(QLabel("minutes"))

        runtimeLayout.addLayout(layout)

        layout = QHBoxLayout()

        self.setpointEdit = QLineEdit()
        self.setpointEdit.setValidator(QRegExpValidator(QRegExp("[0-9]*(|\\.[0-9]*)")))
        self.setpointEdit.editingFinished.connect(self.update_setpoint)
        self.setpointEdit.setText(str(self.controller.get_setpoint()))

        self.setpointUnitsLabel = QLabel(f"{self.measureUnitsDropdown.currentText()}/{self.timebaseDropdown.currentText()}")

        layout.addWidget(QLabel("Setpoint"))
        layout.addWidget(self.setpointEdit)
        layout.addWidget(self.setpointUnitsLabel)

        runtimeLayout.addLayout(layout)

        layout = QHBoxLayout()

        manualMeasureButton = QPushButton("Get measurement")
        manualMeasureButton.clicked.connect(self.update_plot)
        self.saveCsvButton = QPushButton("Start saving to CSV")
        self.saveCsvButton.clicked.connect(self.save_to_csv_start)

        layout.addWidget(manualMeasureButton)
        layout.addWidget(self.saveCsvButton)

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
        self.sensor1SampleIntervalEdit.setValidator(QRegExpValidator(QRegExp("[0-9]*(|\\.[0-9]*)")))
        self.sensor1SampleIntervalEdit.setFixedWidth(100)
        self.sensor1SampleIntervalEdit.editingFinished.connect(self.update_sensor1_timer)
        self.sensor1SampleIntervalEdit.setText("1")

        label = QLabel('Sampling interval')
        label.setFixedWidth(90)
        layout.addWidget(label)
        layout.addWidget(self.sensor1SampleIntervalEdit)
        layout.addWidget(QLabel('minutes'))
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
        self.sensor2SampleIntervalEdit.setValidator(QRegExpValidator(QRegExp("[0-9]*(|\\.[0-9]*)")))
        self.sensor2SampleIntervalEdit.setFixedWidth(100)
        self.sensor2SampleIntervalEdit.editingFinished.connect(self.update_sensor2_timer)
        self.sensor2SampleIntervalEdit.setText("1")

        label = QLabel('Sampling interval')
        label.setFixedWidth(90)
        layout.addWidget(label)
        layout.addWidget(self.sensor2SampleIntervalEdit)
        layout.addWidget(QLabel('minutes'))
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

        self.tempControllerGroup = QGroupBox("Temperature controller")
        self.tempControllerGroup.setCheckable(True)
        self.tempControllerGroup.setEnabled(False) # Disabled functionality as it is untested
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

        self.tempReadoutLabel = QLabel("Readout: None ℃")

        layout = QHBoxLayout()
        layout.addWidget(QLabel("Ramping"), alignment=Qt.AlignLeft)
        layout.addWidget(self.rampingCheckbox, alignment=Qt.AlignLeft)
        layout.addWidget(self.tempReadoutLabel, alignment=Qt.AlignBottom)
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
        dosingGroup.setCheckable(False)
        dosingLayout = QVBoxLayout()

        layout = QHBoxLayout()
        self.dosingTimesEdit = QLineEdit()
        self.dosingTimesEdit.setMinimumWidth(160)
        self.dosingTimesEdit.setText("1, 1, 1.5")
        self.dosingTimesEdit.setValidator(QRegExpValidator(QRegExp("(([0-9]+|[0-9]+\\.[0-9]+),(| ))+")))
        self.dosingTimesEdit.textChanged.connect(self.update_dosing_vectors)

        label = QLabel("Times")
        label.setFixedWidth(55)

        layout.addWidget(label)
        layout.addWidget(self.dosingTimesEdit)
        layout.addWidget(QLabel("minutes"))
        dosingLayout.addLayout(layout)

        layout = QHBoxLayout()
        self.dosingValuesEdit = QLineEdit()
        self.dosingValuesEdit.setMinimumWidth(160)
        self.dosingValuesEdit.setText("1.0, 2.0, 5.0")
        self.dosingValuesEdit.setValidator(QRegExpValidator(QRegExp("(([0-9]+|[0-9]+\\.[0-9]+),(| ))+")))
        self.dosingValuesEdit.textChanged.connect(self.update_dosing_vectors)

        label = QLabel("Setpoints")
        label.setFixedWidth(55)

        self.dosingUnitsLabel = QLabel(f"{self.measureUnitsDropdown.currentText()}/{self.timebaseDropdown.currentText()}")

        layout.addWidget(label)
        layout.addWidget(self.dosingValuesEdit)
        layout.addWidget(self.dosingUnitsLabel)
        dosingLayout.addLayout(layout)

        self.dosingLabel = QLabel("Dosing disabled")

        self.dosingVorStateLabel = QLabel(f"VOR is {self.controller.get_valve_override().lower()}")

        if "normal" in self.dosingVorStateLabel.text():
            self.dosingVorStateLabel.setStyleSheet("color: green")
        else:
            self.dosingVorStateLabel.setStyleSheet("color: red")

        self.dosingControlButton = QPushButton("Start dosing")
        self.dosingControlButton.setCheckable(True)
        self.dosingControlButton.clicked.connect(self.update_dosing_state)

        dosingLayout.addWidget(self.dosingLabel, alignment=Qt.AlignLeft)
        layout = QHBoxLayout()
        layout.addWidget(self.dosingVorStateLabel, alignment=Qt.AlignLeft)
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
            newBufPV = RingBuffer(capacity=value, dtype=np.float16)
            newBufTotal = RingBuffer(capacity=value, dtype=np.float32)
            newTimestampBuf = RingBuffer(capacity=value, dtype=datetime)

            newBufPV.extend(self.samplesPV)
            newBufTotal.extend(self.samplesTotalizer)
            newTimestampBuf.extend(self.sampleTimestamps)

            self.samplesPV = newBufPV
            self.samplesTotalizer = newBufTotal
            self.sampleTimestamps = newTimestampBuf
        elif value < self.sampleBufferSize:
            newBufPV = RingBuffer(capacity=value, dtype=np.float16)
            newBufTotal = RingBuffer(capacity=value, dtype=np.float32)
            newTimestampBuf = RingBuffer(capacity=value, dtype=datetime)

            newBufPV.extend(self.samplesPV[:-value])
            newBufTotal.extend(self.samplesTotalizer[:-value])
            newTimestampBuf.extend(self.sampleTimestamps[:-value])

            self.samplesPV = newBufPV
            self.samplesTotalizer = newBufTotal
            self.sampleTimestamps = newTimestampBuf
