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
        self.write_register(0x14, lowHi[1], 1)

    # register 0, 1 decimal (thermocouple resolution 0.1 deg C)
    def read_temperature(self):
        return self.read_register(0x00, 1)

    # Set the 4-step ramping process according to the datasheet
    # Page 18, section 12.7
    # gradient 1 to 300
    # set 1/2 -1999 to 18000
    # t_hold 1/2  0 to 3600
    # hysteresis 1/2 0 to 9999
    def set_ramping_parameters(self, gradient, set1, th1, h1, set2, th2, h2):
        self.write_register(0x2D, gradient, 1)
        self.write_register(0x1A, set1, 1)
        self.write_register(0x2E, th1, 1)
        self.write_register(0x1B, h1, 1)
        self.write_register(0x1E, set2, 1)
        self.write_register(0x2F, th2, 1)
        self.write_register(0x1F, h2, 1)

    def ramping_on(self):
        raise NotImplementedError

    def ramping_off(self):
        raise NotImplementedError
