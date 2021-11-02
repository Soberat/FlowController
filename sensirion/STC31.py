from bidict import bidict
from sensirion_shdlc_sensorbridge import SensorBridgeShdlcDevice, SensorBridgePort


# TODO: Check length of returned values, as they are not stated in the datasheet
# TODO: Write tests with known params to test connectivity

class STC31:
    I2C_ADDRESS = 0x29

    BINARY_GAS = bidict({
        "CO2 in N2, 0-100%": 0x0000,
        "CO2 in air, 0-100%": 0x0001,
        "CO2 in N2, 0-25%": 0x0002,
        "CO2 in air, 0-25%": 0x0003
    })

    def __init__(self, bridge: SensorBridgeShdlcDevice, bridgePort: int):
        assert bridgePort in [SensorBridgePort.ONE, SensorBridgePort.TWO]

        self.__device = bridge
        self.bridgePort = bridgePort

    # Wrapper around parsing 16 bit arguments into correct values for transceive_i2c function
    def __send_command(self, command: int, argument: int = None, rx_length: int = 6):
        tx_array = bytearray(int.to_bytes(command, 2, 'big'))
        if argument is not None:
            arg = bytearray(int.to_bytes(argument, 2, 'big'))
            tx_array.append(arg[0])
            tx_array.append(arg[1])
        rx_data = self.__device.transceive_i2c(self.bridgePort, address=self.I2C_ADDRESS, tx_data=tx_array,
                                               rx_length=rx_length, timeout_us=100e3)
        return rx_data

    # Disable CRC for reads/writes. Reboot to re-enable
    def disable_crc(self):
        print("disable_crc data: {}".format(self.__send_command(command=0x3768)))

    def set_binary_gas(self, binaryGas):
        assert binaryGas in self.BINARY_GAS.keys()
        print("set_binary_gas data: {}".format(self.__send_command(command=0x3615, argument=self.BINARY_GAS[binaryGas])))

    def set_relative_humidity(self, relativeHumidity: float):
        assert 0.0 <= relativeHumidity <= 100.0
        print("set_relative_humidity data: {}".format(self.__send_command(command=0x3624, argument=int((65535*relativeHumidity)/100))))

    def set_temperature(self, temperature: float):
        assert -163.84 <= temperature <= 163.835
        print("set_temperature data: {}".format(self.__send_command(command=0x361E, argument=int(200*temperature))))

    def set_pressure(self, pressure):
        assert 0 <= pressure <= 65535
        print("set_pressure data: {}".format(self.__send_command(command=0x362F, argument=pressure)))

    def measure_gas_concentration(self):
        print("measure_gas_concentration: {}".format(self.__send_command(command=0x3639, rx_length=9)))

    def forced_recalibration(self, referenceConcentration):
        assert 0 <= referenceConcentration <= 65535
        print("forced_recalibration: {}".format(self.__send_command(command=0x3661, argument=referenceConcentration)))

    def automatic_self_calibration(self, enabled: bool):
        if enabled:
            print("automatic_self_calibration data: {}".format(self.__send_command(command=0x3FEF)))
        else:
            print("automatic_self_calibration data: {}".format(self.__send_command(command=0x3F6E)))

    def self_test(self):
        print("self_test data: {}".format(self.__send_command(command=0x365B, rx_length=3)))

    def soft_reset(self):
        print("soft_reset data: {}".format(self.__send_command(command=0x0006, rx_length=0)))

    def read_product_id(self):
        raise NotImplementedError
        print("read_product_id data: {}".format(self.__send_command(command=0x367CE102)))
