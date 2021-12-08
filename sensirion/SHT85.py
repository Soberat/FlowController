from sensirion_shdlc_sensorbridge import SensorBridgeShdlcDevice
from sensirion.SensirionSensor import SensirionSensor


class SHT85(SensirionSensor):

    def __init__(self, bridge: SensorBridgeShdlcDevice, bridgePort: int):
        super().__init__(bridge, bridgePort)
        self.i2c_address = 0x44

    def get_measurements(self):
        command = 0x2400  # 2400 for high repeatability, 240B for medium, 2416 for low
        values = self._send_command(command, rx_length=6)
        temperature = -45 + (175*int.from_bytes(values[0:2], 'big'))/65535
        humidity = 100 * int.from_bytes(values[3:5], 'big')/65535
        return temperature, humidity
