import minimalmodbus
import numpy as np


class AR6X2(minimalmodbus.Instrument):
    """
    Instrument class for APAR AR6X2 controllers

    Args:
        * port (str): port name
        * address (int): slave address in the range 1 to 247

    """

    REGISTER_OUT1_STATE = 0x2D
    REGISTER_OUT1_TEMP = 0x1A
    REGISTER_OUT1_LOW = 0x14
    REGISTER_OUT1_HIGH = 0x15

    REGISTER_TEMP_PROBE = 0x00

    REGISTER_RAMP_GRADIENT = 0x2D
    REGISTER_RAMP_TIMEHOLD = 0x2E
    REGISTER_RAMP_STATE = 0x2C

    PARAM_OUTPUT_OFF = 0
    PARAM_OUTPUT_HEATING = 2

    PARAM_RAMPING_OFF = 0
    PARAM_RAMPING_AUTO = 2

    def __init__(self, port, address):
        # A serial connection. The default values match the AR6x2 datasheet
        # However, the AR6x2 unit should have the baudrate set to 19200
        minimalmodbus.Instrument.__init__(self, port, int(address))
        self.__rangeLow = -199.9
        self.__rangeHigh = 850.0
        self.__currentOutTemp = 100.0

    def turn_off(self):
        self.write_register(AR6X2.REGISTER_OUT1_STATE, AR6X2.PARAM_OUTPUT_OFF, 1)

    def turn_on(self):
        self.write_register(AR6X2.REGISTER_OUT1_STATE, AR6X2.PARAM_OUTPUT_HEATING, 1)

    def set_temperature(self, temperature):
        temperature = np.clip(temperature, self.__rangeLow, self.__rangeHigh)
        self.write_register(AR6X2.REGISTER_OUT1_TEMP, temperature, 1)
        self.__currentOutTemp = temperature

    # Set the operation temperature range
    # If Low1 is bigger than High1 then "we get an inverse curve"
    # Manual page 13, note (2)
    def set_range_low(self, value):
        value = np.clip(value, -199.9, 1800.0)[0]
        self.__rangeLow = value
        self.write_register(AR6X2.REGISTER_OUT1_LOW, value, 1)
        newTemp = np.clip(self.__currentOutTemp, self.__rangeLow, self.__rangeHigh)
        self.write_register(AR6X2.REGISTER_OUT1_TEMP, newTemp)
        return newTemp

    def set_range_high(self, value):
        value = np.clip(value, -199.9, 1800.0)[0]
        self.__rangeHigh = value
        self.write_register(AR6X2.REGISTER_OUT1_HIGH, value, 1)
        newTemp = np.clip(self.__currentOutTemp, self.__rangeLow, self.__rangeHigh)[0]
        self.write_register(AR6X2.REGISTER_OUT1_TEMP, newTemp)
        return newTemp

    # register 0, 1 decimal (thermocouple resolution 0.1 deg C)
    def read_temperature(self):
        return self.read_register(AR6X2.REGISTER_TEMP_PROBE, 1)

    # Set the gradient of 2 stage ramping
    # To hold set1 indefinitely we set th1 to 0
    # Page 18, section 12.7
    # Values between 1 and 300 are mapped between 1.0 and 30.0
    def set_gradient(self, gradient):
        gradient = np.clip(gradient, 1.0, 30.0)[0]
        self.write_register(AR6X2.REGISTER_RAMP_GRADIENT, gradient*10, 1)
        self.write_register(AR6X2.REGISTER_RAMP_TIMEHOLD, 0, 1)

    # Setting the ramping mode to auto will start the process immediately
    def ramping_on(self):
        self.write_register(AR6X2.REGISTER_RAMP_STATE, AR6X2.PARAM_RAMPING_AUTO, 1)

    def ramping_off(self):
        self.write_register(AR6X2.REGISTER_RAMP_STATE, AR6X2.PARAM_RAMPING_OFF, 1)
