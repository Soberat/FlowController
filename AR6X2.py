import minimalmodbus


# TODO: Heating on/off
# TODO: Set temperature
# TODO: Ramping

class AR6X2(minimalmodbus.Instrument):
    """
    Instrument class for APAR AR6X2 controllers

    Args:
        * port (str): port name
        * address (int): slave address in the range 1 to 247

    """
    PARAM_OUTPUT_OFF = 0
    PARAM_OUTPUT_HEATING = 2

    PARAM_RAMPING_OFF = 0
    PARAM_RAMPING_AUTO = 2

    def __init__(self, port, address):
        # A serial connection. The default values match the AR6x2 datasheet
        # However, the AR6x2 unit should have the baudrate set to 19200
        minimalmodbus.Instrument.__init__(self, port, address)
        self.__rangeLow = 0.0
        self.__rangeHigh = 100.0

    def turn_off(self):
        self.write_register(0x2D, AR6X2.PARAM_OUTPUT_OFF, 1)

    def turn_on(self):
        self.write_register(0x2D, AR6X2.PARAM_OUTPUT_HEATING, 1)

    def set_temperature(self, temperature):
        assert self.__rangeLow <= temperature <= self.__rangeHigh
        self.write_register(0x14, temperature, 1)

    # Set the operation temperature range
    # If Low1 is bigger than High1 then "we get an inverse curve"
    # Manual page 13, note (2)
    def set_range(self, lowHi):
        assert lowHi is tuple
        self.write_register(0x14, lowHi[0], 1)
        self.write_register(0x15, lowHi[1], 1)

    # register 0, 1 decimal (thermocouple resolution 0.1 deg C)
    def read_temperature(self):
        return self.read_register(0x00, 1)

    # Set the parameters of 2 stage ramping
    # To hold set1 indefinitely we set th1 to 0
    # Page 18, section 12.7
    def set_ramping_parameters(self, gradient, set1):
        self.write_register(0x2D, gradient, 1)
        self.set_temperature(set1)
        self.write_register(0x2E, 0, 1)

    # Setting the ramping mode to auto will start the process immediately
    def ramping_on(self):
        self.write_register(0x2C, AR6X2.PARAM_RAMPING_AUTO, 1)

    def ramping_off(self):
        self.write_register(0x2C, AR6X2.PARAM_RAMPING_OFF, 1)
