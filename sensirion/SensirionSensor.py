# Class defining the properties of all Sensirion sensors connected via Sensor Bridge

from sensirion_shdlc_sensorbridge import SensorBridgeShdlcDevice, SensorBridgePort


class SensirionSensor:

    # Wrapper dictionary, since QComboBoxes require list of strings as items
    PORTS = {
        'Port 1': SensorBridgePort.ONE,
        'Port 2': SensorBridgePort.TWO
    }

    def __init__(self, bridge: SensorBridgeShdlcDevice, bridgePort: int):
        assert bridgePort in [SensorBridgePort.ONE, SensorBridgePort.TWO]

        self.__device = bridge
        self.bridgePort = bridgePort
        self.i2c_address = 0x00

    # Wrapper around parsing 16 bit arguments into correct values for transceive_i2c function
    def _send_command(self, command: int, argument: int = None, rx_length: int = 0):
        tx_array = bytearray(int.to_bytes(command, 2, 'big'))
        if argument is not None:
            arg = bytearray(int.to_bytes(argument, 2, 'big'))
            tx_array.append(arg[0])
            tx_array.append(arg[1])
        rx_data = self.__device.transceive_i2c(self.bridgePort, address=self.i2c_address, tx_data=tx_array,
                                               rx_length=rx_length, timeout_us=100e3)
        return rx_data

    def analog_measurement(self):
        return self.__device.measure_voltage(self.bridgePort)

    def blink(self):
        self.__device.blink_led(self.bridgePort)

    def set_supply_voltage(self, voltage):
        self.__device.set_supply_voltage(self.bridgePort, float(voltage))

    def set_i2c_frequency(self, frequency):
        self.__device.set_i2c_frequency(self.bridgePort, float(frequency))
