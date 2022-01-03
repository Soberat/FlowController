import numpy as np
import pyvisa
from datetime import datetime
from bidict import bidict

# Class representing a single Brooks Mass Flow Controller,
# Handling communication via a 0254 controller according to the datasheets


class Controller:
    # Process value codes
    PARAM_PV_MEASURE_UNITS = 0x04
    PARAM_PV_TIME_BASE = 0x0A
    PARAM_PV_DECIMAL_POINT = 0x03
    PARAM_PV_GAS_FACTOR = 0x1B
    PARAM_PV_LOG_TYPE = 0x1C  # Unused according to the 10.2017 datasheet (page 3-10)
    PARAM_PV_SIGNAL_TYPE = 0x00
    PARAM_PV_FULL_SCALE = 0x09

    # Setpoint value codes
    PARAM_SP_SIGNAL_TYPE = 0x00
    PARAM_SP_FULL_SCALE = 0x09
    PARAM_SP_FUNCTION = 0x02
    PARAM_SP_RATE = 0x01
    PARAM_SP_VOR = 0x1D
    PARAM_SP_BATCH = 0x2C
    PARAM_SP_BLEND = 0x2D
    PARAM_SP_SOURCE = 0x2E

    # Valve override states
    # There is the dictionary for reverse look-up
    # value -> state, as well as easily readable constants
    VOR_OPTIONS = bidict({
        "Normal": 0,
        "Closed": 1,
        "Open": 2
    })

    VOR_OPTION_NORMAL = 0
    VOR_OPTION_CLOSED = 1
    VOR_OPTION_OPEN = 2

    # Setpoint functions
    SP_FUNC_RATE = 1
    SP_FUNC_BATCH = 2
    SP_FUNC_BLEND = 3

    # Setpoint sources
    SP_SOURCES = bidict({
        "Keypad/Serial": 0,
        "Serial only": 1
    })

    # "Targets", required for reading full_scale and signal_type values, that share codes between SP and PV
    # Values chosen arbitrarily
    TARGET_PV = 0x1F
    TARGET_SP = 0x2F

    # Input port types
    # type : internal code dictionary
    INPUT_PORT_TYPES = bidict({
        "Off": '0',
        "0-20mA": '7',
        "4-20mA": '8',
        "0-10V": '9',
        "2-10V": ":",
        "0-5V": ';',
        "1-5V": '<'
    })

    DECIMAL_POINTS = bidict({
        "xxx.": 0,
        "xx.x": 1,
        "x.xx": 2,
        ".xxx": 3
    })

    # Output port types
    OUTPUT_PORT_TYPES = bidict({
        "Off": 0,
        "0-20mA": 1,
        "4-20mA": 2,
        "0-10V": 3,
        "2-10V": 4,
        "0-5V": 5,
        "1-5V": 6
    })

    # Measurement units
    MEASUREMENT_UNITS = bidict({
        "ml": 0,
        "mls": 1,
        "mln": 2,
        "l": 3,
        "ls": 4,
        "ln": 5,
        "cm^3": 6,
        "cm^3s": 7,
        "cm^3n": 8,
        "m^3": 9,
        "m^3s": 10,
        "m^3n": 11,
        "g": 12,
        "lb": 13,
        "kg": 14,
        "ft^3": 15,
        "ft^3s": 16,
        "ft^3n": 17,
        "scc": 18,
        "sl": 19,
        "bar": 20,
        "mbar": 21,
        "psi": 22,
        "kPa": 23,
        "Torr": 24,
        "atm": 25,
        "Volt": 26,
        "mA": 27,
        "oC": 28,
        "oK": 29,
        "oR": 30,
        "oF": 31,
        "g/cc": 32,
        "sg": 33,
        "%": 34,
        "lb/in^3": 35,
        "lb/ft^3": 36,
        "lb/gal": 37,
        "kg/m^3": 38,
        "g/ml": 39,
        "kg/l": 40,
        "g/l": 41
    })

    # Base time units
    RATE_TIME_BASE = bidict({
        "sec": 1,
        "min": 2,
        "hrs": 3,
        "day": 4
    })

    # Polled Message types - datasheet (C-4-5-2 Message Format)
    TYPE_RESPONSE = '4'
    TYPE_BATCH_CONTROL_STATUS = '5'

    def __init__(self, channel, pyvisaConnection, deviceAddress=None):
        # Addressing parameters
        self.channel = channel
        self.__inputPort = 2 * channel - 1
        self.__outputPort = 2 * channel
        self.__address: str = deviceAddress  # this is a string because it needs to be zero-padded to be 5 chars long

        # PyVisa connection
        self.__connection: pyvisa = pyvisaConnection

        self.decimalPoint = self.DECIMAL_POINTS[self.get_decimal_point()]

    def __read_value(self, param, target=None):
        if param == Controller.PARAM_SP_FUNCTION or param == Controller.PARAM_SP_RATE or param == Controller.PARAM_SP_VOR or param == Controller.PARAM_SP_BATCH or param == Controller.PARAM_SP_BLEND or param == Controller.PARAM_SP_SOURCE or \
                (param == Controller.PARAM_SP_FULL_SCALE or param == Controller.PARAM_SP_SIGNAL_TYPE and target == Controller.TARGET_SP):
            # Create and send ascii encoded command via serial, wait for response
            if self.__address is None:
                command = f'AZ.{self.__outputPort}P{param}?'
            else:
                command = f'AZ{self.__address}.{self.__outputPort}P{param}?'
            response = self.__connection.query(command).split(sep=',')

            if response[2] == Controller.TYPE_RESPONSE:
                return self.__parse_response(param, response[4])
            else:
                return None
        elif param == Controller.PARAM_PV_MEASURE_UNITS or param == Controller.PARAM_PV_TIME_BASE or param == Controller.PARAM_PV_DECIMAL_POINT or param == Controller.PARAM_PV_GAS_FACTOR or \
                (param == Controller.PARAM_PV_SIGNAL_TYPE or param == Controller.PARAM_PV_FULL_SCALE and target == Controller.TARGET_PV):
            if self.__address is None:
                command = f'AZ.{self.__inputPort}P{param}?'
            else:
                command = f'AZ{self.__address}.{self.__inputPort}P{param}?'
            response = self.__connection.query(command).split(sep=',')

            if response[2] == Controller.TYPE_RESPONSE:
                return self.__parse_response(param, response[4])
            else:
                return None
        else:
            return None

    # This is an internal write functions to be used by the public functions
    # Returns whatever was written to the variable, None if some error occurred
    def __write_value(self, param, value, target=None):
        # The only difference for writing is the input or output port, which are addressed differently
        if param == Controller.PARAM_SP_FUNCTION or param == Controller.PARAM_SP_RATE or param == Controller.PARAM_SP_VOR or param == Controller.PARAM_SP_BATCH or param == Controller.PARAM_SP_BLEND or param == Controller.PARAM_SP_SOURCE or \
                (param == Controller.PARAM_SP_FULL_SCALE or param == Controller.PARAM_SP_SIGNAL_TYPE and target == Controller.TARGET_SP):
            # Create and send ascii encoded command via serial, wait for response
            if self.__address is None:
                command = f'AZ.{self.__outputPort}P{param}={value}'
            else:
                command = f'AZ{self.__address}.{self.__outputPort}P{param}={value}'
            response = self.__connection.query(command).split(sep=',')

            if response[2] == Controller.TYPE_RESPONSE:
                return self.__parse_response(param, response[4])
            else:
                return None
        elif param == Controller.PARAM_PV_MEASURE_UNITS or param == Controller.PARAM_PV_TIME_BASE or param == Controller.PARAM_PV_DECIMAL_POINT or param == Controller.PARAM_PV_GAS_FACTOR or \
                (param == Controller.PARAM_PV_SIGNAL_TYPE or param == Controller.PARAM_PV_FULL_SCALE and target == Controller.TARGET_PV):
            if self.__address is None:
                command = f'AZ.{self.__inputPort}P{param}={value}'
            else:
                command = f'AZ{self.__address}.{self.__outputPort}P{param}={value}'
            response = self.__connection.query(command).split(sep=',')

            if response[2] == Controller.TYPE_RESPONSE:
                return self.__parse_response(param, response[4])
            else:
                return None
        else:
            return None

    @staticmethod
    def __parse_response(param, value):
        value = value.strip()
        if param == Controller.PARAM_SP_VOR:
            return Controller.VOR_OPTIONS.inverse[int(value)]
        elif param == Controller.PARAM_PV_GAS_FACTOR:
            return float(value)
        elif param == Controller.PARAM_PV_SIGNAL_TYPE:
            return Controller.INPUT_PORT_TYPES.inverse[value[len(value)-2:len(value)-1]]    # second char to last is the value
        elif param == Controller.PARAM_SP_SIGNAL_TYPE:
            return Controller.OUTPUT_PORT_TYPES.inverse[value[len(value)-2:len(value)-1]]
        elif param == Controller.PARAM_SP_SOURCE:
            return Controller.SP_SOURCES.inverse[int(value)]
        elif param == Controller.PARAM_PV_DECIMAL_POINT:
            return Controller.DECIMAL_POINTS.inverse[int(value)]
        elif param == Controller.PARAM_PV_MEASURE_UNITS:
            return Controller.MEASUREMENT_UNITS.inverse[int(value)]
        elif param == Controller.PARAM_PV_TIME_BASE:
            return Controller.RATE_TIME_BASE.inverse[int(value)]
        else:
            return value

    # Function that generates a 'gather measurements' command and returns the data as a triple of values
    # current PV, total PV and timestamp
    def get_measurements(self):
        if self.__address is None:
            command = f'AZ.{self.__inputPort}K'
        else:
            command = f'AZ{self.__address}.{self.__outputPort}K'
        response = self.__connection.query(command).split(sep=',')

        if response[2] == Controller.TYPE_RESPONSE:
            return np.float16(response[5]), np.float32(response[4]), datetime.now()
        else:
            return None

    # Process configuration setters
    # Public function to control manual valve override option
    def set_valve_override(self, state):
        assert (
                state == Controller.VOR_OPTION_NORMAL or state == Controller.VOR_OPTION_CLOSED or state == Controller.VOR_OPTION_OPEN)
        return self.__write_value(Controller.PARAM_SP_VOR, state)

    # From manual: "scale factor by which interpolated channel units are multiplied"
    def set_gas_factor(self, value):
        assert 0 <= value <= 999.999
        value = int(value*1000)  # value is written to serial as XXXXXX without the decimal
        response = self.__write_value(Controller.PARAM_PV_GAS_FACTOR, value)
        return response

    # DS: "Analog interpolator representing the eng. units of the greater measured signal"
    def set_pv_full_scale(self, value):
        assert (-999.999 <= value <= 999.999)  # Possible setpoint values according to the datasheet (section C-5-4)
        value = int(value * 10**self.decimalPoint)  # Value is written to serial factoring in the decimal point
        return self.__write_value(Controller.PARAM_PV_FULL_SCALE, value, target=Controller.TARGET_PV)

    # Set the input signal type
    def set_pv_signal_type(self, sigtype):
        assert (self.INPUT_PORT_TYPES.keys().__contains__(sigtype))
        return self.__write_value(Controller.PARAM_PV_SIGNAL_TYPE, Controller.INPUT_PORT_TYPES[sigtype],
                                  target=Controller.TARGET_PV)

    # DS: "Analog de-interpolator representing the eng. units of the greatest measured signal"
    def set_sp_full_scale(self, value):
        assert (-999.999 <= value <= 999.999)  # Possible setpoint values according to the datasheet (section C-5-4)
        value = int(value * 10**self.decimalPoint)  # Value is written to serial factoring in the decimal point
        return self.__write_value(Controller.PARAM_SP_FULL_SCALE, value, target=Controller.TARGET_SP)

    # Set the output signal type
    def set_sp_signal_type(self, sigtype):
        assert (self.OUTPUT_PORT_TYPES.keys().__contains__(sigtype))
        return self.__write_value(Controller.PARAM_SP_SIGNAL_TYPE, Controller.OUTPUT_PORT_TYPES[sigtype],
                                  target=Controller.TARGET_SP)

    # Set the setpoint source
    def set_source(self, source):
        assert (source in Controller.SP_SOURCES.keys())
        return self.__write_value(Controller.PARAM_SP_SOURCE, Controller.SP_SOURCES.get(source))

    def set_decimal_point(self, point):
        assert point in Controller.DECIMAL_POINTS.keys()
        value = Controller.DECIMAL_POINTS.get(point)
        response = self.__write_value(Controller.PARAM_PV_DECIMAL_POINT, value)
        self.decimalPoint = Controller.DECIMAL_POINTS[point]
        return response

    def set_measurement_units(self, units):
        assert units in Controller.MEASUREMENT_UNITS.keys()
        value = Controller.MEASUREMENT_UNITS.get(units)
        response = self.__write_value(Controller.PARAM_PV_MEASURE_UNITS, value)
        return response

    def set_time_base(self, base):
        assert base in Controller.RATE_TIME_BASE.keys()
        value = Controller.RATE_TIME_BASE.get(base)
        response = self.__write_value(Controller.PARAM_PV_TIME_BASE, value)
        return response

    # Public function to set the head operation point (setpoint)
    def set_setpoint(self, value):
        assert (-999.999 <= value <= 999.999)  # Possible setpoint values according to the datasheet (section C-5-4)
        value = int(value * 10**self.decimalPoint)  # Value is written to serial factoring in the decimal point
        return self.__write_value(Controller.PARAM_SP_RATE, value)

    # Sets the setpoint function, rate/batch/blend.
    # Plan is to only use rate.
    def set_function(self, function):
        assert (
                function == Controller.SP_FUNC_RATE or function == Controller.SP_FUNC_BATCH or function == Controller.SP_FUNC_BLEND)
        return self.__write_value(Controller.PARAM_SP_FUNCTION, function)

    # Batch/blend ratios setting
    def set_batch(self, value):
        assert (-999.999 <= value <= 999.999)  # Possible setpoint values according to the datasheet (section C-5-4)
        value = int(value * 10**self.decimalPoint)  # Value is written to serial factoring in the decimal point
        return self.__write_value(Controller.PARAM_SP_BATCH, value)

    # Documentation does not whether blending is also affected by blending, leaving unchanged
    def set_blend(self, value):
        assert (-999.999 <= value <= 999.999)  # Possible setpoint values according to the datasheet (section C-5-4)
        value = int(value * 1000)  # value is written to serial as XXXXXX without the decimal
        return self.__write_value(Controller.PARAM_SP_BLEND, value)

    # Process configuration getters
    def get_valve_override(self):
        return self.__read_value(Controller.PARAM_SP_VOR)

    def get_gas(self):
        return self.__read_value(Controller.PARAM_PV_GAS_FACTOR)

    def get_pv_full_scale(self):
        return self.__read_value(Controller.PARAM_PV_FULL_SCALE, target=Controller.TARGET_PV)

    def get_pv_signal_type(self):
        return self.__read_value(Controller.PARAM_PV_SIGNAL_TYPE, target=Controller.TARGET_PV)

    def get_sp_full_scale(self):
        return self.__read_value(Controller.PARAM_SP_FULL_SCALE, target=Controller.TARGET_SP)

    def get_sp_signal_type(self):
        return self.__read_value(Controller.PARAM_SP_SIGNAL_TYPE, target=Controller.TARGET_SP)

    def get_source(self):
        return self.__read_value(Controller.PARAM_SP_SOURCE)

    def get_decimal_point(self):
        return self.__read_value(Controller.PARAM_PV_DECIMAL_POINT)

    def get_measurement_units(self):
        return self.__read_value(Controller.PARAM_PV_MEASURE_UNITS)

    def get_time_base(self):
        return self.__read_value(Controller.PARAM_PV_TIME_BASE)

    def get_setpoint(self):
        return self.__read_value(Controller.PARAM_SP_RATE)
