import sys
from PyQt5.QtCore import Qt, QRegExp, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QRegExpValidator, QIntValidator
from PyQt5.QtWidgets import (
    QCheckBox, QVBoxLayout, QWidget, QHBoxLayout, QGridLayout, QGroupBox, QLabel,
    QPushButton, QComboBox, QSpinBox, QDoubleSpinBox, QDialog, QFormLayout, QLineEdit
)
from numpy_ringbuffer import RingBuffer
import numpy as np
from pyqtgraph import mkPen, PlotWidget
from Brooks025X import Brooks025X
from datetime import datetime
from PyQt5 import QtCore
from sensirion_shdlc_driver import ShdlcConnection, ShdlcSerialPort
from sensirion_shdlc_sensorbridge import SensorBridgeShdlcDevice, SensorBridgePort
from sensirion.SensirionSensor import SensirionSensor
from sensirion.SHT85 import SHT85
from sensirion.STC31 import STC31
from serial.tools.list_ports import comports
import resources


class SSBDialog(QDialog):
    accepted = pyqtSignal(dict)

    # unlock OK only if all fields are set
    def unlock_ok(self):
        elements = [self.port.currentText(),
                    self.baudrate.text(),
                    self.slave_address.text()]
        self.buttonOk.setEnabled(all([len(x) > 0 for x in elements]))

    def ok_pressed(self):
        values = {'port': self.port.currentText(),
                  'baudrate': int(self.baudrate.text()),
                  'address': int(self.slave_address.text())}
        self.accepted.emit(values)
        self.accept()

    def cancel_pressed(self):
        self.close()

    def refresh_devices(self):
        devices = [device.name for device in set(comports())]
        if devices != self.devices:
            self.devices = devices
            self.port.clear()
            self.port.addItems(devices)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Prepare dialog window, disable whatsthis
        self.setWindowTitle("Configure serial device")
        self.setWindowFlags(QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowTitleHint)
        self.devices = [device.name for device in set(comports())]

        self.port = QComboBox()
        self.port.addItems(self.devices)
        self.port.currentTextChanged.connect(self.unlock_ok)

        self.baudrate = QLineEdit("460800")
        self.baudrate.setValidator(QIntValidator())
        self.baudrate.textChanged.connect(self.unlock_ok)

        self.slave_address = QLineEdit("0")
        self.slave_address.setValidator(QIntValidator())
        self.slave_address.textChanged.connect(self.unlock_ok)

        self.buttonOk = QPushButton("Connect")
        self.buttonOk.setEnabled(False)
        self.buttonOk.clicked.connect(self.ok_pressed)

        self.buttonCancel = QPushButton("Cancel")
        self.buttonCancel.clicked.connect(self.cancel_pressed)

        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_devices)
        self.timer.start(1000)

        form = QFormLayout(self)
        form.addRow('Port', self.port)
        form.addRow('Baud rate', self.baudrate)
        form.addRow('Slave address', self.slave_address)
        form.addRow('', self.buttonOk)
        form.addRow('', self.buttonCancel)

        self.unlock_ok()


class SensirionSBPlot(QWidget):
    def __init__(self, plot_title, color, bufferSize):
        super().__init__()
        masterLayout = QVBoxLayout()
        self.pen = mkPen(color, width=1.25)

        layout = QVBoxLayout()
        self.group = QGroupBox(plot_title)
        self.plot = PlotWidget()
        self.plot.getPlotItem().showGrid(x=True, y=True, alpha=1)
        if "qdarkstyle" in sys.modules:
            self.plot.setBackground((25, 35, 45))
        self.buffer = RingBuffer(capacity=bufferSize, dtype=float)

        self.group.setLayout(layout)
        layout.addWidget(self.plot)
        masterLayout.addWidget(self.group)

        self.setLayout(masterLayout)

    def change_capacity(self, value):
        if value > len(self.buffer):
            newBuf = RingBuffer(capacity=value, dtype=float)
            newBuf.extend(self.buffer)
            self.buffer = newBuf

        elif value < len(self.buffer):
            newBuf = RingBuffer(capacity=value, dtype=float)
            newBuf.extend(self.buffer[:-value])
            self.buffer = newBuf

    def update_plot(self, sample):
        self.plot.clear()
        self.buffer.append(sample)
        self.plot.plot(self.buffer, pen=self.pen, symbolPen=self.pen, symbol='o', symbolSize=5, name="symbol ='o'")


class SensirionSB(QWidget):
    # Each plot is individually notified of a new value,
    # but if one measurement fails, no signal is sent.
    # This is to prevent plot phase shift when 1 measurement was successful and another was not.
    sht85TemperatureReady = pyqtSignal(float)
    sht85HumidityReady = pyqtSignal(float)
    sht85AnalogReady = pyqtSignal(float)
    stc31ConcentrationReady = pyqtSignal(float)
    stc31AnalogReady = pyqtSignal(float)

    def __init__(self):
        super().__init__()

        self.ssbGroup = QGroupBox("Sensirion Sensorbridge control")
        self.portLabel = QLabel("Serial port: not connected")
        self.device: SensorBridgeShdlcDevice = None

        self.portOnePowerEnabled = False
        self.portOnePowerButton = QPushButton("Enable supply")
        self.portOnePowerButton.clicked.connect(self.port_one_supply_clicked)
        self.portOnePowerLabel = QLabel("Unknown state")

        self.portTwoPowerEnabled = False
        self.portTwoPowerButton = QPushButton("Enable supply")
        self.portTwoPowerButton.clicked.connect(self.port_two_supply_clicked)
        self.portTwoPowerLabel = QLabel("Unknown state")

        self.sht85device: SHT85 = None

        self.sht85PortDropdown = QComboBox()
        self.sht85PortDropdown.addItems(SensirionSensor.PORTS.keys())
        self.sht85PortDropdown.setCurrentIndex(1)
        self.sht85PortDropdown.currentTextChanged.connect(self.sht85_port_changed)

        self.sht85compensationEnabled = False
        self.sht85compensationCheckbox = QCheckBox("Compensate STC31 on measurement")
        self.sht85compensationCheckbox.clicked.connect(self.compensate_changed)

        self.sht85TemperatureLabel = QLabel("Temp: ? ???")
        self.sht85HumidityLabel = QLabel("Humidity: ? % RH")
        self.sht85AnalogLabel = QLabel("Analog: ? V")

        self.sht85BlinkButton = QPushButton("Blink")
        self.sht85BlinkButton.clicked.connect(lambda: self.sht85device.blink())

        self.stc31device: STC31 = None

        self.stc31PortDropdown = QComboBox()
        self.stc31PortDropdown.addItems(SensirionSensor.PORTS.keys())
        self.stc31PortDropdown.setCurrentIndex(1)
        self.stc31PortDropdown.currentTextChanged.connect(self.stc31_port_changed)

        self.stc31BinaryGasDropdown = QComboBox()
        self.stc31BinaryGasDropdown.addItems(STC31.BINARY_GAS.keys())
        self.stc31BinaryGasDropdown.currentTextChanged.connect(
            lambda: self.stc31device.set_binary_gas(self.stc31BinaryGasDropdown.currentText()))

        self.stc31RelativeHumidityEdit = QDoubleSpinBox()
        self.stc31RelativeHumidityEdit.setRange(0.0, 100.0)
        self.stc31RelativeHumidityEdit.setValue(0.0)
        self.stc31RelativeHumidityEdit.setSuffix("  % RH")
        self.stc31RelativeHumidityEdit.editingFinished.connect(
            lambda: self.stc31device.set_relative_humidity(self.stc31RelativeHumidityEdit.value()))

        self.stc31TemperatureEdit = QDoubleSpinBox()
        self.stc31TemperatureEdit.setRange(-163.84, 163.835)
        self.stc31TemperatureEdit.setSuffix("  ???")
        self.stc31TemperatureEdit.editingFinished.connect(
            lambda: self.stc31device.set_temperature(self.stc31TemperatureEdit.value()))

        self.stc31PressureEdit = QSpinBox()
        self.stc31PressureEdit.setRange(0, 65535)
        self.stc31PressureEdit.setValue(1013)
        self.stc31PressureEdit.setSuffix("  mbar")
        self.stc31PressureEdit.editingFinished.connect(
            lambda: self.stc31device.set_pressure(self.stc31PressureEdit.value()))

        self.stc31ForcedRecalibrationEdit = QSpinBox()
        self.stc31ForcedRecalibrationEdit.setRange(0, 65535)
        self.stc31ForcedRecalibrationEdit.setValue(0)
        self.stc31ForcedRecalibrationEdit.setSuffix(" % vol")
        self.stc31ForcedRecalibrationEdit.editingFinished.connect(
            lambda: self.stc31device.forced_recalibration(self.stc31ForcedRecalibrationEdit.value()))

        self.stc31GasConcentrationLabel = QLabel("Gas concentration: ? %")
        self.stc31AnalogLabel = QLabel("Analog: ? V")

        self.stc31AutoSelfCalibrationCheckbox = QCheckBox("Automatic self calibration")
        self.stc31AutoSelfCalibrationCheckbox.setChecked(False)
        self.stc31AutoSelfCalibrationCheckbox.clicked.connect(
            lambda: self.stc31device.automatic_self_calibration(self.stc31AutoSelfCalibrationCheckbox.isChecked()))

        self.stc31SelfTestButton = QPushButton("Self test")
        self.stc31SelfTestButton.clicked.connect(self.stc31_self_test)

        self.stc31SoftResetButton = QPushButton("Soft reset")
        self.stc31SoftResetButton.clicked.connect(lambda: self.stc31device.soft_reset())

        self.stc31BlinkButton = QPushButton("Blink")
        self.stc31BlinkButton.clicked.connect(lambda: self.stc31device.blink())

        self.timer = QTimer()
        self.timer.timeout.connect(self.on_timeout)

        self.intervalEdit = QLineEdit("1")
        self.intervalEdit.setValidator(QRegExpValidator(QRegExp("[0-9]*(|\\.[0-9]*)")))
        self.intervalEdit.setMaximumWidth(150)
        self.intervalEdit.editingFinished.connect(
            lambda: self.timer.setInterval(int(60 * 1000 * float(self.intervalEdit.text()))))

        self.csvFile = None
        self.savingEnabled = False
        self.savingButton = QPushButton("Start saving to file")
        self.savingButton.clicked.connect(self.saving_button_clicked)

        self.bufferSizeEdit = QLineEdit()
        self.bufferSizeEdit.setValidator(QIntValidator())
        self.bufferSizeEdit.setText("128")
        self.bufferSizeEdit.editingFinished.connect(self.update_buffer_sizes)

        self.sht85TemperaturePlotWidget = SensirionSBPlot("SHT85 temperature", (255, 32, 0), 128)
        self.sht85HumidityPlotWidget = SensirionSBPlot("SHT85 relative humidity", (0, 127, 255), 128)
        self.sht85AnalogPlotWidget = SensirionSBPlot("SHT85 analog", (255, 127, 0), 128)
        self.stc31ConcentrationPlotWidget = SensirionSBPlot("STC31 concentration", (200, 200, 200), 128)
        self.stc31AnalogPlotWidget = SensirionSBPlot("STC31 analog", (255, 127, 0), 128)

        self.sht85TemperatureReady.connect(self.sht85TemperaturePlotWidget.update_plot)
        self.sht85HumidityReady.connect(self.sht85HumidityPlotWidget.update_plot)
        self.sht85AnalogReady.connect(self.sht85AnalogPlotWidget.update_plot)
        self.stc31ConcentrationReady.connect(self.stc31ConcentrationPlotWidget.update_plot)
        self.stc31AnalogReady.connect(self.stc31AnalogPlotWidget.update_plot)

        self.setLayout(self.create_layout())

    def stc31_self_test(self):
        result = int.from_bytes(self.stc31device.self_test(), 'big')
        if result == 0x00:
            self.stc31SelfTestButton.setText("Self test: OK")
            QTimer().singleShot(5000, lambda: self.stc31SelfTestButton.setText("Self test"))
        else:
            self.stc31SelfTestButton.setText("Self test: FAIL (0x{:04x})".format(result))
            QTimer().singleShot(5000, lambda: self.stc31SelfTestButton.setText("Self test"))

    def update_buffer_sizes(self):
        value = int(self.bufferSizeEdit.text())
        self.sht85TemperaturePlotWidget.change_capacity(value)
        self.sht85HumidityPlotWidget.change_capacity(value)
        self.sht85AnalogPlotWidget.change_capacity(value)
        self.stc31ConcentrationPlotWidget.change_capacity(value)
        self.stc31AnalogPlotWidget.change_capacity(value)

    # Function to create the layout
    def create_layout(self):
        masterLayout = QHBoxLayout()
        # Create a vertical layout for the left column
        leftColumnLayout = QVBoxLayout()

        self.ssbGroup.setCheckable(True)
        self.ssbGroup.setChecked(False)
        self.ssbGroup.clicked.connect(self.update_ssb_group)
        ssbLayout = QVBoxLayout()
        self.ssbGroup.setLayout(ssbLayout)
        self.ssbGroup.setFixedWidth(405)

        ssbLayout.addWidget(self.portLabel)

        powerGroup = QGroupBox("Power supply")
        powerLayout = QHBoxLayout()

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Port 1"), alignment=Qt.AlignCenter)
        layout.addWidget(self.portOnePowerButton)
        layout.addWidget(self.portOnePowerLabel, alignment=Qt.AlignCenter)
        powerLayout.addLayout(layout)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Port 2"), alignment=Qt.AlignCenter)
        layout.addWidget(self.portTwoPowerButton)
        layout.addWidget(self.portTwoPowerLabel, alignment=Qt.AlignCenter)
        powerLayout.addLayout(layout)

        powerGroup.setLayout(powerLayout)
        ssbLayout.addWidget(powerGroup)

        shtGroup = QGroupBox("SHT85 control")
        shtLayout = QVBoxLayout()

        layout = QHBoxLayout()
        layout.addWidget(QLabel("Sensorbridge port"))
        layout.addWidget(self.sht85PortDropdown)
        shtLayout.addLayout(layout)

        shtLayout.addWidget(self.sht85compensationCheckbox)

        shtLayout.addWidget(self.sht85TemperatureLabel)
        shtLayout.addWidget(self.sht85HumidityLabel)
        shtLayout.addWidget(self.sht85AnalogLabel)

        shtLayout.addWidget(self.sht85BlinkButton)

        shtGroup.setLayout(shtLayout)
        ssbLayout.addWidget(shtGroup)

        stcGroup = QGroupBox("STC31 control")
        stcLayout = QVBoxLayout()

        layout = QHBoxLayout()
        layout.addWidget(QLabel("Sensorbridge port"))
        layout.addWidget(self.stc31PortDropdown)
        stcLayout.addLayout(layout)

        layout = QHBoxLayout()
        layout.addWidget(QLabel("Binary gas"))
        layout.addWidget(self.stc31BinaryGasDropdown)
        stcLayout.addLayout(layout)

        layout = QHBoxLayout()
        layout.addWidget(QLabel("Relative humidity"))
        layout.addWidget(self.stc31RelativeHumidityEdit)
        stcLayout.addLayout(layout)

        layout = QHBoxLayout()
        layout.addWidget(QLabel("Temperature"))
        layout.addWidget(self.stc31TemperatureEdit)
        stcLayout.addLayout(layout)

        layout = QHBoxLayout()
        layout.addWidget(QLabel("Pressure"))
        layout.addWidget(self.stc31PressureEdit)
        stcLayout.addLayout(layout)

        layout = QHBoxLayout()
        layout.addWidget(QLabel("Forced calibration"))
        layout.addWidget(self.stc31ForcedRecalibrationEdit)
        stcLayout.addLayout(layout)

        stcLayout.addWidget(self.stc31AutoSelfCalibrationCheckbox)
        stcLayout.addWidget(self.stc31GasConcentrationLabel)
        stcLayout.addWidget(self.stc31AnalogLabel)
        stcLayout.addWidget(self.stc31SelfTestButton)
        stcLayout.addWidget(self.stc31SoftResetButton)
        stcLayout.addWidget(self.stc31BlinkButton)

        stcGroup.setLayout(stcLayout)
        ssbLayout.addWidget(stcGroup)

        layout = QHBoxLayout()
        layout.addWidget(QLabel("Measurement interval"))
        layout.addWidget(self.intervalEdit)
        layout.addWidget(QLabel("minutes"))
        layout.setStretch(0, 10)
        ssbLayout.addLayout(layout)

        ssbLayout.addWidget(self.savingButton)
        button = QPushButton("I2C scan")
        i2cLabel = QLabel("I2C devices: unknown")
        button.clicked.connect(lambda: i2cLabel.setText(
            "I2C devices: " + ", ".join([hex(address) for address in self.device.scan_i2c(SensorBridgePort.ONE)] + [hex(address) for address in self.device.scan_i2c(SensorBridgePort.TWO)])))
        ssbLayout.addWidget(button)
        ssbLayout.addWidget(i2cLabel)

        layout = QHBoxLayout()
        layout.addWidget(QLabel("Buffer size"))
        layout.addWidget(self.bufferSizeEdit)
        layout.addWidget(QLabel("samples"))
        layout.setStretch(0, 10)
        ssbLayout.addLayout(layout)

        leftColumnLayout.addWidget(self.ssbGroup, alignment=Qt.AlignTop)
        leftColumnLayout.setStretch(2, 10)

        masterLayout.addLayout(leftColumnLayout)

        # Layout housing all the plot widgets
        rightColumnLayout = QVBoxLayout()
        rightColumnLayout.addWidget(self.sht85TemperaturePlotWidget)
        rightColumnLayout.addWidget(self.sht85HumidityPlotWidget)
        rightColumnLayout.addWidget(self.sht85AnalogPlotWidget)
        rightColumnLayout.addWidget(self.stc31ConcentrationPlotWidget)
        rightColumnLayout.addWidget(self.stc31AnalogPlotWidget)

        masterLayout.addLayout(rightColumnLayout)

        return masterLayout

    def sht85_port_changed(self):
        self.sht85device.bridgePort = self.sht85device.PORTS[self.sht85PortDropdown.currentText()]

    def stc31_port_changed(self):
        self.stc31device.bridgePort = self.stc31device.PORTS[self.stc31PortDropdown.currentText()]

    def port_one_supply_clicked(self):
        if not self.portTwoPowerEnabled:
            self.portOnePowerButton.setText("Disable supply")
            self.portOnePowerLabel.setText("Supply state: enabled")
            self.portOnePowerEnabled = True
            self.device.switch_supply_on(SensorBridgePort.ONE)
            QTimer().singleShot(200, self.stc31device.disable_crc)
            QTimer().singleShot(300, lambda: self.stc31device.set_binary_gas(self.stc31BinaryGasDropdown.currentText()))
        else:
            self.portOnePowerButton.setText("Enable supply")
            self.portOnePowerLabel.setText("Supply state: disabled")
            self.portOnePowerEnabled = False
            self.device.switch_supply_off(SensorBridgePort.ONE)

    def port_two_supply_clicked(self):
        if not self.portTwoPowerEnabled:
            self.portTwoPowerButton.setText("Disable supply")
            self.portTwoPowerLabel.setText("Supply state: enabled")
            self.portTwoPowerEnabled = True
            self.device.switch_supply_on(SensorBridgePort.TWO)
            QTimer().singleShot(200, self.stc31device.disable_crc)
            QTimer().singleShot(300, lambda: self.stc31device.set_binary_gas(self.stc31BinaryGasDropdown.currentText()))
        else:
            self.portTwoPowerButton.setText("Enable supply")
            self.portTwoPowerLabel.setText("Supply state: disabled")
            self.portTwoPowerEnabled = False
            self.device.switch_supply_off(SensorBridgePort.TWO)

    def compensate_changed(self):
        if self.sht85compensationCheckbox.isChecked():
            self.sht85compensationEnabled = True
            self.stc31TemperatureEdit.setEnabled(False)
            self.stc31RelativeHumidityEdit.setEnabled(False)
        else:
            self.sht85compensationEnabled = False
            self.stc31TemperatureEdit.setEnabled(True)
            self.stc31RelativeHumidityEdit.setEnabled(True)

    def compensate_stc31(self, temperature, humidity):
        self.stc31TemperatureEdit.setValue(temperature)
        self.stc31RelativeHumidityEdit.setValue(humidity)
        # manually trigger updates
        self.stc31device.set_temperature(temperature)
        self.stc31device.set_relative_humidity(humidity)

    def on_timeout(self):
        try:
            temperature, humidity = self.sht85device.get_measurements()
            analog1 = self.sht85device.analog_measurement()
            self.sht85TemperatureLabel.setText(f"Temp: {temperature:.5f} ???")
            self.sht85HumidityLabel.setText(f"Humidity: {humidity:.5f} % RH")
            self.sht85AnalogLabel.setText(f"Analog: {analog1:.5f} V")

            if self.sht85compensationEnabled:
                self.compensate_stc31(temperature, humidity)

            concentration = self.stc31device.measure_gas_concentration()
            analog2 = self.stc31device.analog_measurement()
            self.stc31GasConcentrationLabel.setText(f"Concentration: {concentration:.5f} %")
            self.stc31AnalogLabel.setText(f"Analog: {analog2:.5f} V")

            self.sht85TemperatureReady.emit(temperature)
            self.sht85HumidityReady.emit(humidity)
            self.sht85AnalogReady.emit(analog1)
            self.stc31ConcentrationReady.emit(concentration)
            self.stc31AnalogReady.emit(analog2)
        except Exception:
            return

        if self.savingEnabled:
            self.append_to_csv(temperature, humidity, concentration, analog1, analog2)

    def saving_button_clicked(self):
        if not self.savingEnabled:
            filename = datetime.now().strftime(f"sensorbridge_%Y-%m-%d_%H-%M-%S.csv")
            self.csvFile = open(filename, 'w')
            self.csvFile.write(
                "{},{},{},{},{},{}\n".format("Temperature", "Humidity", "Concentration", "Analog 1", "Analog 2",
                                             "Timestamp"))
            self.csvFile.close()
            self.savingEnabled = True
            self.savingButton.setText("Disable saving to file")
        else:
            self.csvFile.close()
            self.csvFile = None
            self.savingEnabled = False
            self.savingButton.setText("Start saving to file")

    def append_to_csv(self, temperature, humidity, concentration, analog1, analog2):
        self.csvFile = open(self.csvFile.name, 'a')
        self.csvFile.write("{},{},{},{},{},{}\n".format(temperature, humidity, concentration, analog1, analog2,
                                                        datetime.now().strftime("%Y/%m/%d-%H:%M:%S")))
        self.csvFile.close()

    def update_devices(self, values):
        self.portLabel.setText(f"Serial port: {values['port']}")
        self.device = SensorBridgeShdlcDevice(
            ShdlcConnection(ShdlcSerialPort(values['port'], baudrate=values['baudrate'])),
            slave_address=values['address'])
        self.sht85device = SHT85(self.device, SensirionSensor.PORTS[self.sht85PortDropdown.currentText()])
        self.stc31device = STC31(self.device, SensirionSensor.PORTS[self.stc31PortDropdown.currentText()])

    def update_ssb_group(self):
        if self.ssbGroup.isChecked():
            dg = SSBDialog()
            dg.accepted.connect(self.update_devices)
            # if unsuccessful, disable the group
            if dg.exec_() == 0:
                self.ssbGroup.setChecked(False)
            else:
                self.timer.start(int(60 * 1000 * float(self.intervalEdit.text())))
        else:
            # Stop all timers, disconnect device to free up serial port
            self.timer.stop()
            self.device = None
            self.sht85device = None
            self.stc31device = None
            self.portLabel.setText("Serial port: not connected")
            if self.savingEnabled:
                self.csvFile.close()
                self.csvFile = None
                self.savingEnabled = False


class CombinedPlot(QWidget):

    PLOT_PENS = [mkPen((219, 148, 92), width=1.25),
                 mkPen((103, 219, 104), width=1.25),
                 mkPen((59, 198, 219), width=1.25),
                 mkPen((219, 70, 143), width=1.25)]
                 
    def __init__(self):
        super().__init__()
        capacity = 256
    
        self.buffer1 = RingBuffer(capacity=capacity, dtype=np.float32)
        self.buffer2 = RingBuffer(capacity=capacity, dtype=np.float32)
        self.buffer3 = RingBuffer(capacity=capacity, dtype=np.float32)
        self.buffer4 = RingBuffer(capacity=capacity, dtype=np.float32)
        
        self.plot = PlotWidget()
        self.plot.getPlotItem().showGrid(x=True, y=True, alpha=1)
        self.plot.addLegend()
        if "qdarkstyle" in sys.modules:
            self.plot.setBackground((25, 35, 45))
            
        self.bufferSizeEdit = QLineEdit()
        self.bufferSizeEdit.setText(str(capacity))
        self.bufferSizeEdit.setValidator(QRegExpValidator(QRegExp("[0-9]*")))
        self.bufferSizeEdit.editingFinished.connect(self.change_capacity)
        
        self.layout = QVBoxLayout()
        
        group = QGroupBox("Combined controller plot")
        
        layout = QVBoxLayout()
        layout.addWidget(self.plot)
        
        innerLayout = QHBoxLayout()
        innerLayout.addWidget(QLabel("Buffer size"))
        innerLayout.addWidget(self.bufferSizeEdit)
        layout.addLayout(innerLayout)
        
        group.setLayout(layout)
        self.layout.addWidget(group)
        self.setLayout(self.layout)
        
    def update_plot(self, controllerN: int, sample: np.float16):
        self.plot.clear()
        
        if controllerN == 1:
            self.buffer1.append(sample)
        elif controllerN == 2:
            self.buffer2.append(sample)
        elif controllerN == 3:
            self.buffer3.append(sample)
        elif controllerN == 4:
            self.buffer4.append(sample)
        
        self.plot.plot(self.buffer1, pen=self.PLOT_PENS[0], symbolPen=self.PLOT_PENS[0], symbol='o', symbolSize=5, name="Controller 1")
        self.plot.plot(self.buffer2, pen=self.PLOT_PENS[1], symbolPen=self.PLOT_PENS[1], symbol='o', symbolSize=5, name="Controller 2")
        self.plot.plot(self.buffer3, pen=self.PLOT_PENS[2], symbolPen=self.PLOT_PENS[2], symbol='o', symbolSize=5, name="Controller 3")
        self.plot.plot(self.buffer4, pen=self.PLOT_PENS[3], symbolPen=self.PLOT_PENS[3], symbol='o', symbolSize=5, name="Controller 4")
        
    def change_capacity(self):
        value = int(self.bufferSizeEdit.text())
        if value > len(self.buffer1):
            newBuf1 = RingBuffer(capacity=value, dtype=np.float16)
            newBuf1.extend(self.buffer1)
            newBuf2 = RingBuffer(capacity=value, dtype=np.float16)
            newBuf2.extend(self.buffer2)
            newBuf3 = RingBuffer(capacity=value, dtype=np.float16)
            newBuf3.extend(self.buffer3)
            newBuf4 = RingBuffer(capacity=value, dtype=np.float16)
            newBuf4.extend(self.buffer4)

            self.buffer1 = newBuf1
            self.buffer2 = newBuf2
            self.buffer3 = newBuf3
            self.buffer4 = newBuf4

        elif value < len(self.buffer1):
            newBuf1 = RingBuffer(capacity=value, dtype=np.float16)
            newBuf1.extend(self.buffer1[:-value])
            newBuf2 = RingBuffer(capacity=value, dtype=np.float16)
            newBuf2.extend(self.buffer2[:-value])
            newBuf3 = RingBuffer(capacity=value, dtype=np.float16)
            newBuf3.extend(self.buffer3[:-value])
            newBuf4 = RingBuffer(capacity=value, dtype=np.float16)
            newBuf4.extend(self.buffer4[:-value])

            self.buffer1 = newBuf1
            self.buffer2 = newBuf2
            self.buffer3 = newBuf3
            self.buffer4 = newBuf4


class GlobalTab(QWidget):
    def __init__(self, brooksObject: Brooks025X, controllerTabs):
        super().__init__()

        self.brooks = brooksObject
        self.tabs = controllerTabs

        self.saving1Checkbox = QCheckBox("Controller 1")
        self.saving2Checkbox = QCheckBox("Controller 2")
        self.saving3Checkbox = QCheckBox("Controller 3")
        self.saving4Checkbox = QCheckBox("Controller 4")
        self.savingCheckboxes = [self.saving1Checkbox, self.saving2Checkbox, self.saving3Checkbox, self.saving4Checkbox]

        self.dosing1Checkbox = QCheckBox("Controller 1")
        self.dosing2Checkbox = QCheckBox("Controller 2")
        self.dosing3Checkbox = QCheckBox("Controller 3")
        self.dosing4Checkbox = QCheckBox("Controller 4")
        self.dosingCheckboxes = [self.dosing1Checkbox, self.dosing2Checkbox, self.dosing3Checkbox, self.dosing4Checkbox]

        self.saving1Enabled = False
        self.saving2Enabled = False
        self.saving3Enabled = False
        self.saving4Enabled = False

        self.dosing1Enabled = False
        self.dosing2Enabled = False
        self.dosing3Enabled = False
        self.dosing4Enabled = False

        self.saveCsvButton = None
        self.dosingControlButton = None

        errorImage = QPixmap(":/error.png")

        self.savingErrorLabel = QLabel()
        self.savingErrorLabel.setPixmap(errorImage)
        self.savingErrorLabel.setMask(errorImage.mask())

        self.dosingErrorLabel = QLabel()
        self.dosingErrorLabel.setPixmap(errorImage)
        self.dosingErrorLabel.setMask(errorImage.mask())

        self.savingInfoLabel = QLabel()
        self.dosingInfoLabel = QLabel()

        self.audioBeepCheckbox = QCheckBox()
        self.zeroSuppressCheckbox = QCheckBox()
        self.powerSpClearCheckbox = QCheckBox()
        
        self.combinedPlotWidget = CombinedPlot()

        # Connect to all existing tabs' signals
        if self.tabs[0] is not None:
            self.tabs[0].dosingSignal.connect(self.update_dosing1)
            self.tabs[0].savingSignal.connect(self.update_saving1)
            self.tabs[0].sampleReady.connect(self.combinedPlotWidget.update_plot)

        if self.tabs[1] is not None:
            self.tabs[1].dosingSignal.connect(self.update_dosing2)
            self.tabs[1].savingSignal.connect(self.update_saving2)
            self.tabs[1].sampleReady.connect(self.combinedPlotWidget.update_plot)
            
        if self.tabs[2] is not None:
            self.tabs[2].dosingSignal.connect(self.update_dosing3)
            self.tabs[2].savingSignal.connect(self.update_saving3)
            self.tabs[2].sampleReady.connect(self.combinedPlotWidget.update_plot)
            
        if self.tabs[3] is not None:
            self.tabs[3].dosingSignal.connect(self.update_dosing4)
            self.tabs[3].savingSignal.connect(self.update_saving4)
            self.tabs[3].sampleReady.connect(self.combinedPlotWidget.update_plot)
            
        masterLayout = QGridLayout()
        masterLayout.addLayout(self.create_left_column(self.tabs), 0, 0)
        masterLayout.addLayout(self.create_middle_column(), 0, 1)

        self.setLayout(masterLayout)

    # Callbacks to updating functions
    def update_dosing1(self, enabled: bool):
        self.dosing1Enabled = enabled
        self.update_checkboxes_dosing()

    def update_dosing2(self, enabled: bool):
        self.dosing2Enabled = enabled
        self.update_checkboxes_dosing()

    def update_dosing3(self, enabled: bool):
        self.dosing3Enabled = enabled
        self.update_checkboxes_dosing()

    def update_dosing4(self, enabled: bool):
        self.dosing4Enabled = enabled
        self.update_checkboxes_dosing()

    def update_saving1(self, enabled: bool):
        self.saving1Enabled = enabled
        self.saving_signal_update()

    def update_saving2(self, enabled: bool):
        self.saving2Enabled = enabled
        self.saving_signal_update()

    def update_saving3(self, enabled: bool):
        self.saving3Enabled = enabled
        self.saving_signal_update()

    def update_saving4(self, enabled: bool):
        self.saving4Enabled = enabled
        self.saving_signal_update()

    # If user turned off all ongoing saving processes, this function will revert the button back to the proper state
    def saving_signal_update(self):
        if not any([self.saving1Enabled, self.saving2Enabled, self.saving3Enabled, self.saving4Enabled]):
            self.saving1Checkbox.setEnabled(self.tabs[0] is not None)
            self.saving2Checkbox.setEnabled(self.tabs[1] is not None)
            self.saving3Checkbox.setEnabled(self.tabs[2] is not None)
            self.saving4Checkbox.setEnabled(self.tabs[3] is not None)
            self.saveCsvButton.setText("Start saving to CSVs")
            self.saveCsvButton.clicked.disconnect()
            self.saveCsvButton.clicked.connect(self.start_saving_to_csv)

    # Callbacks for changed selection of controllers
    # Saving can be enabled even if it was already enabled, it will just be restarted
    def update_checkboxes_saving(self):
        enabled = any([box.isChecked() for box in self.savingCheckboxes])
        self.saveCsvButton.setEnabled(enabled)
        self.savingInfoLabel.setVisible(not enabled)
        self.savingErrorLabel.setVisible(not enabled)

    # Dosing requires valid vectors for all controllers in the program
    def update_checkboxes_dosing(self):
        enabled = any([box.isChecked() for box in self.dosingCheckboxes]) and not any([self.dosing1Enabled,
                                                                                       self.dosing2Enabled,
                                                                                       self.dosing3Enabled,
                                                                                       self.dosing4Enabled])
        self.dosingControlButton.setEnabled(enabled)
        self.dosingInfoLabel.setVisible(not enabled)
        self.dosingErrorLabel.setVisible(not enabled)

        if not any([self.dosing1Enabled, self.dosing2Enabled, self.dosing3Enabled, self.dosing4Enabled]):
            self.dosing1Checkbox.setEnabled(self.tabs[0] is not None)
            self.dosing2Checkbox.setEnabled(self.tabs[1] is not None)
            self.dosing3Checkbox.setEnabled(self.tabs[2] is not None)
            self.dosing4Checkbox.setEnabled(self.tabs[3] is not None)

            self.dosingControlButton.setText("Start dosing processes")
            self.dosingControlButton.clicked.disconnect()
            self.dosingControlButton.clicked.connect(self.start_dosing)

        # Set an error message depending on the error
        if not any([box.isChecked() for box in self.dosingCheckboxes]):
            self.dosingInfoLabel.setText("No controller was selected!")
        else:
            self.dosingInfoLabel.setText("One of dosing vectors is wrong or dosing is already enabled for a controller")

    def start_saving_to_csv(self):
        for box in self.savingCheckboxes:
            box.setEnabled(False)
        self.saveCsvButton.setText("Stop saving to CSVs")
        self.saveCsvButton.clicked.disconnect()
        self.saveCsvButton.clicked.connect(self.stop_saving_to_csv)

        if self.saving1Checkbox.isChecked():
            self.tabs[0].save_to_csv_start()
        if self.saving2Checkbox.isChecked():
            self.tabs[1].save_to_csv_start()
        if self.saving3Checkbox.isChecked():
            self.tabs[2].save_to_csv_start()
        if self.saving4Checkbox.isChecked():
            self.tabs[3].save_to_csv_start()

    # Stop the saving which is in progress
    def stop_saving_to_csv(self):
        self.saving1Checkbox.setEnabled(self.tabs[0] is not None)
        self.saving2Checkbox.setEnabled(self.tabs[1] is not None)
        self.saving3Checkbox.setEnabled(self.tabs[2] is not None)
        self.saving4Checkbox.setEnabled(self.tabs[3] is not None)
        self.saveCsvButton.setText("Start saving to CSVs")
        self.saveCsvButton.clicked.disconnect()
        self.saveCsvButton.clicked.connect(self.start_saving_to_csv)

        if self.saving1Checkbox.isChecked():
            self.tabs[0].save_to_csv_stop()
        if self.saving2Checkbox.isChecked():
            self.tabs[1].save_to_csv_stop()
        if self.saving3Checkbox.isChecked():
            self.tabs[2].save_to_csv_stop()
        if self.saving4Checkbox.isChecked():
            self.tabs[3].save_to_csv_stop()

    def start_dosing(self):
        for box in self.dosingCheckboxes:
            box.setEnabled(False)
        self.dosingControlButton.setText("Stop dosing processes")
        self.dosingControlButton.clicked.connect(self.stop_dosing)

        if self.dosing1Checkbox.isChecked():
            self.tabs[0].dosingControlButton.setChecked(True)
            self.tabs[0].update_dosing_state()
        if self.dosing2Checkbox.isChecked():
            self.tabs[1].dosingControlButton.setChecked(True)
            self.tabs[1].update_dosing_state()
        if self.dosing3Checkbox.isChecked():
            self.tabs[2].dosingControlButton.setChecked(True)
            self.tabs[2].update_dosing_state()
        if self.dosing4Checkbox.isChecked():
            self.tabs[3].dosingControlButton.setChecked(True)
            self.tabs[3].update_dosing_state()

    def stop_dosing(self):
        self.dosing1Checkbox.setEnabled(self.tabs[0] is not None)
        self.dosing2Checkbox.setEnabled(self.tabs[1] is not None)
        self.dosing3Checkbox.setEnabled(self.tabs[2] is not None)
        self.dosing4Checkbox.setEnabled(self.tabs[3] is not None)

        self.dosingControlButton.setText("Start dosing processes")
        self.dosingControlButton.clicked.connect(self.start_dosing)

        if self.dosing1Checkbox.isChecked():
            self.tabs[0].dosingControlButton.setChecked(False)
            self.tabs[0].update_dosing_state()
        if self.dosing2Checkbox.isChecked():
            self.tabs[1].dosingControlButton.setChecked(False)
            self.tabs[1].update_dosing_state()
        if self.dosing3Checkbox.isChecked():
            self.tabs[2].dosingControlButton.setChecked(False)
            self.tabs[2].update_dosing_state()
        if self.dosing4Checkbox.isChecked():
            self.tabs[3].dosingControlButton.setChecked(False)
            self.tabs[3].update_dosing_state()

    # Checkbox handlers
    def update_audio_beep(self):
        self.brooks.set_audio_beep(self.audioBeepCheckbox.isChecked())

    def update_zero_suppress(self):
        self.brooks.set_zero_suppress(self.zeroSuppressCheckbox.isChecked())

    def update_power_sp_clear(self):
        self.brooks.set_power_sp_clear(self.powerSpClearCheckbox.isChecked())

    # Function to create the layout
    def create_left_column(self, controllerTabs):
        # Create a vertical layout for the left column
        leftColumnLayout = QVBoxLayout()

        # Saving group
        savingGroup = QGroupBox("Simultaneous saving start")
        savingLayout = QVBoxLayout()

        layout = QHBoxLayout()

        self.saving1Checkbox.setChecked(controllerTabs[0] is not None)
        self.saving1Checkbox.setEnabled(controllerTabs[0] is not None)
        self.saving1Checkbox.stateChanged.connect(self.update_checkboxes_saving)
        layout.addWidget(self.saving1Checkbox, alignment=Qt.AlignTop)

        self.saving2Checkbox.setChecked(controllerTabs[1] is not None)
        self.saving2Checkbox.setEnabled(controllerTabs[1] is not None)
        self.saving2Checkbox.stateChanged.connect(self.update_checkboxes_saving)
        layout.addWidget(self.saving2Checkbox, alignment=Qt.AlignTop)

        self.saving3Checkbox.setChecked(controllerTabs[2] is not None)
        self.saving3Checkbox.setEnabled(controllerTabs[2] is not None)
        self.saving3Checkbox.stateChanged.connect(self.update_checkboxes_saving)
        layout.addWidget(self.saving3Checkbox, alignment=Qt.AlignTop)

        self.saving4Checkbox.setChecked(controllerTabs[3] is not None)
        self.saving4Checkbox.setEnabled(controllerTabs[3] is not None)
        self.saving4Checkbox.stateChanged.connect(self.update_checkboxes_saving)
        layout.addWidget(self.saving4Checkbox, alignment=Qt.AlignTop)

        savingLayout.addLayout(layout)

        layout = QHBoxLayout()
        self.saveCsvButton = QPushButton("Start saving to CSVs")
        self.saveCsvButton.clicked.connect(self.start_saving_to_csv)
        layout.addWidget(self.saveCsvButton, alignment=Qt.AlignTop)
        savingLayout.addLayout(layout)

        layout = QHBoxLayout()
        layout.addWidget(self.savingErrorLabel, alignment=Qt.AlignBottom)
        self.savingInfoLabel.setText("No controller was selected!")
        layout.addWidget(self.savingInfoLabel, alignment=Qt.AlignBottom)
        layout.setStretch(1, 10)
        self.savingInfoLabel.setVisible(False)
        self.savingErrorLabel.setVisible(False)

        savingLayout.setStretch(1, 10)
        savingLayout.addLayout(layout)

        savingGroup.setLayout(savingLayout)
        savingGroup.setFixedWidth(405)
        savingGroup.setFixedHeight(103)

        leftColumnLayout.addWidget(savingGroup, alignment=Qt.AlignTop)

        # Dosing group
        dosingGroup = QGroupBox("Simultaneous dosing start")
        dosingLayout = QVBoxLayout()

        layout = QHBoxLayout()

        self.dosing1Checkbox.setChecked(controllerTabs[0] is not None)
        self.dosing1Checkbox.setEnabled(controllerTabs[0] is not None)
        self.dosing1Checkbox.stateChanged.connect(self.update_checkboxes_dosing)
        layout.addWidget(self.dosing1Checkbox, alignment=Qt.AlignTop)

        self.dosing2Checkbox.setChecked(controllerTabs[1] is not None)
        self.dosing2Checkbox.setEnabled(controllerTabs[1] is not None)
        self.dosing2Checkbox.stateChanged.connect(self.update_checkboxes_dosing)
        layout.addWidget(self.dosing2Checkbox, alignment=Qt.AlignTop)

        self.dosing3Checkbox.setChecked(controllerTabs[2] is not None)
        self.dosing3Checkbox.setEnabled(controllerTabs[2] is not None)
        self.dosing3Checkbox.stateChanged.connect(self.update_checkboxes_dosing)
        layout.addWidget(self.dosing3Checkbox, alignment=Qt.AlignTop)

        self.dosing4Checkbox.setChecked(controllerTabs[3] is not None)
        self.dosing4Checkbox.setEnabled(controllerTabs[3] is not None)
        self.dosing4Checkbox.stateChanged.connect(self.update_checkboxes_dosing)
        layout.addWidget(self.dosing4Checkbox, alignment=Qt.AlignTop)

        dosingLayout.addLayout(layout)

        layout = QHBoxLayout()
        self.dosingControlButton = QPushButton("Start dosing processes")
        self.dosingControlButton.clicked.connect(self.start_dosing)
        layout.addWidget(self.dosingControlButton, alignment=Qt.AlignTop)
        dosingLayout.addLayout(layout)

        layout = QHBoxLayout()
        layout.addWidget(self.dosingErrorLabel, alignment=Qt.AlignBottom)
        layout.addWidget(self.dosingInfoLabel, alignment=Qt.AlignBottom)
        self.dosingInfoLabel.setVisible(False)
        self.dosingErrorLabel.setVisible(False)
        layout.setStretch(1, 10)
        dosingLayout.addLayout(layout)
        dosingLayout.setStretch(1, 10)

        dosingGroup.setLayout(dosingLayout)
        dosingGroup.setFixedSize(405, 103)

        leftColumnLayout.addWidget(dosingGroup, alignment=Qt.AlignTop)

        # Global device configuration group
        deviceGroup = QGroupBox("Device configuration")
        deviceLayout = QFormLayout()

        self.audioBeepCheckbox.stateChanged.connect(self.update_audio_beep)
        self.zeroSuppressCheckbox.stateChanged.connect(self.update_zero_suppress)
        self.powerSpClearCheckbox.stateChanged.connect(self.update_power_sp_clear)
        networkAddressLabel = QLabel(self.brooks.get_network_address())

        deviceLayout.addRow(QLabel("Audio beep"), self.audioBeepCheckbox)
        deviceLayout.addRow(QLabel("Zero suppress"), self.zeroSuppressCheckbox)
        deviceLayout.addRow(QLabel("Power SP Clear"), self.powerSpClearCheckbox)
        deviceLayout.addRow(QLabel("Network address"), networkAddressLabel)

        deviceGroup.setLayout(deviceLayout)
        deviceGroup.setFixedWidth(405)
        leftColumnLayout.addWidget(deviceGroup, alignment=Qt.AlignTop)
        leftColumnLayout.addWidget(self.combinedPlotWidget)
        return leftColumnLayout

    def create_middle_column(self):
        middleColumnLayout = QVBoxLayout()
        middleColumnLayout.addWidget(SensirionSB())

        return middleColumnLayout
