import random

from bidict import bidict
from sensirion_shdlc_sensorbridge import SensorBridgeShdlcDevice
from SensirionSensor import SensirionSensor


# TODO: Check length of returned values, as they are not stated in the datasheet
# TODO: Write tests with known params to test connectivity

class STC31(SensirionSensor):

    def __init__(self, bridge: SensorBridgeShdlcDevice, bridgePort: int):
        super().__init__(bridge, bridgePort)
        self.i2c_address = 0x29
        # TODO: Uncomment
        # self.disable_crc()

    BINARY_GAS = bidict({
        "CO2 in N2, 0-100%": 0x0000,
        "CO2 in air, 0-100%": 0x0001,
        "CO2 in N2, 0-25%": 0x0002,
        "CO2 in air, 0-25%": 0x0003
    })

    # Disable CRC for reads/writes. Reboot to re-enable
    def disable_crc(self):
        self._send_command(command=0x3768)

    def set_binary_gas(self, binaryGas):
        assert binaryGas in self.BINARY_GAS.keys()
        self._send_command(command=0x3615, argument=self.BINARY_GAS[binaryGas])

    def set_relative_humidity(self, relativeHumidity: float):
        # TODO: Uncomment
        assert 0.0 <= relativeHumidity <= 100.0
        # self._send_command(command=0x3624, argument=int((65535 * relativeHumidity) / 100))

    def set_temperature(self, temperature: float):
        assert -163.84 <= temperature <= 163.835
        # TODO: Uncomment
        # self.send_command(command=0x361E, argument=int(200 * temperature))

    def set_pressure(self, pressure):
        assert 0 <= pressure <= 65535
        self._send_command(command=0x362F, argument=pressure)

    def measure_gas_concentration(self):
        # TODO: Unrandom
        return random.Random().random()
        values = self._send_command(command=0x3639, rx_length=9)
        concentration = 100*(int.from_bytes(values[0:2], 'big') - 16384)/32768
        return concentration

    def forced_recalibration(self, referenceConcentration):
        assert 0 <= referenceConcentration <= 65535
        self._send_command(command=0x3661, argument=referenceConcentration)

    def automatic_self_calibration(self, enabled: bool):
        if enabled:
            self._send_command(command=0x3FEF)
        else:
            self._send_command(command=0x3F6E)

    def self_test(self):
        print("self_test data: {}".format(self._send_command(command=0x365B, rx_length=2)))

    def soft_reset(self):
        print("soft_reset data: {}".format(self._send_command(command=0x0006)))
