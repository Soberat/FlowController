import numpy as np
import serial
from numpy_ringbuffer import RingBuffer
from datetime import datetime


# TODO: threading, as we want 4 parallel controller tabs to be constantly up-to-date with their respective info
# TODO: Saving measurements
# TODO: Setting preconfiguring parameters (head type, gas type)
# TODO: Timed dosing functions
# TODO: public functions to be used by the GUI
# TODO: checksum verification
# TODO: An initial configuration function (SP, SP func, SP Source, getting config parameters (full scale, gas type etc))
# TODO: Implement positive/negative acknowledgements
# TODO: Implement support for multiple instances (network-supporting commands)
# Class representing a single Brooks 4850 Mass Flow Controller,
# Handling communication according to the datasheets


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
    VOR_OPTION_NORMAL = 0
    VOR_OPTION_CLOSED = 1
    VOR_OPTION_OPEN = 2

    # Setpoint functions
    SP_FUNC_RATE = 1
    SP_FUNC_BATCH = 2
    SP_FUNC_BLEND = 3

    # Setpoint sources
    SP_SOURCE_KEYPAD = 0
    SP_SOURCE_SERIAL = 1

    # "Targets", required for reading full_scale and signal_type values, that share codes between SP and PV
    # Values chosen arbitrarily
    TARGET_PV = 0x1F
    TARGET_SP = 0x2F


    # Input port types
    # type : internal code dictionary
    INPUT_PORT_TYPES = {
        "Off": 0,
        "0-20mA": 7,
        "4-20mA": 8,
        "0-10V": 9,
        "2-10V": ":",
        "0-5V": ';',
        "1-5V": '<'
    }

    DECIMAL_POINTS = {
        "xxx.": 0,
        "xx.x": 1,
        "x.xx": 2,
        ".xxx": 3
    }

    # Output port types
    OUTPUT_PORT_TYPES = {
        "Off": 0,
        "0-20mA": 1,
        "4-20mA": 2,
        "0-10V": 3,
        "2-10V": 4,
        "0-5V": 5,
        "1-5V": 6
    }

    # Measurement units
    MEASUREMENT_UNITS = {
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
    }

    # Base time units
    RATE_TIME_BASE = {
        "sec": 1,
        "min": 2,
        "hrs": 3,
        "day": 4
    }

    # Polled Message types - datasheet (C-4-5-2 Message Format)
    TYPE_RESPONSE = '4'
    TYPE_BATCH_CONTROL_STATUS = '5'

    def __init__(self, channel, serialConnection, sampleBufferSize=64):
        # Addressing parameters
        self.__channel = channel
        self.__inputPort = 2 * channel - 1
        self.__outputPort = 2 * channel

        # Internal parameters
        self.__sampleBufferSize = sampleBufferSize
        self.__samples = RingBuffer(capacity=self.__sampleBufferSize, dtype=np.float16)
        self.__sampleTimestamps = RingBuffer(capacity=self.__sampleBufferSize, dtype=np.uint64)

        # Physical device measurements
        self.__temperatureReadout = 0
        self.__flowReadout = 0
        self.__maxFlow = 0
        self.__gasId = 0
        self.__gasDensity = 0

        # PySerial connection
        self.__serial: serial.Serial = serialConnection

    def __read_value(self, param, target=None):
        if param == Controller.PARAM_SP_FUNCTION or param == Controller.PARAM_SP_RATE or param == Controller.PARAM_SP_VOR or param == Controller.PARAM_SP_BATCH or param == Controller.PARAM_SP_BLEND or param == Controller.PARAM_SP_SOURCE or (param == Controller.PARAM_SP_FULL_SCALE or param == Controller.PARAM_SP_SIGNAL_TYPE and target == Controller.TARGET_SP):
            # Create and send ascii encoded command via serial, wait for response
            command = f'AZ.{self.__outputPort}P{param}?\r'
            self.__serial.write(command.encode('ascii'))

            response = self.__serial.read(self.__serial.in_waiting).decode('ascii').split(sep=',')
            if response[2] == Controller.TYPE_RESPONSE:
                return response[4]
        elif param == Controller.PARAM_PV_MEASURE_UNITS or param == Controller.PARAM_PV_TIME_BASE or param == Controller.PARAM_PV_DECIMAL_POINT or param == Controller.PARAM_PV_GAS_FACTOR or (param == Controller.PARAM_PV_SIGNAL_TYPE or param == Controller.PARAM_PV_FULL_SCALE and target == Controller.TARGET_PV):
            command = f'AZ.{self.__inputPort}P{param}?\r'
            self.__serial.write(command.encode('ascii'))

            response = self.__serial.read(self.__serial.in_waiting).decode('ascii').split(sep=',')
            if response[2] == Controller.TYPE_RESPONSE:
                return response[4]
        else:
            return None

    # This is an internal write functions to be used by the public functions
    # Returns whatever was written to the variable, None if some error occurred
    def __write_value(self, param, value, target=None):
        # The only difference for writing is the input or output port, which are addressed differently
        if param == Controller.PARAM_SP_FUNCTION or param == Controller.PARAM_SP_RATE or param == Controller.PARAM_SP_VOR or param == Controller.PARAM_SP_BATCH or param == Controller.PARAM_SP_BLEND or param == Controller.PARAM_SP_SOURCE or (param == Controller.PARAM_SP_FULL_SCALE or param == Controller.PARAM_SP_SIGNAL_TYPE and target == Controller.TARGET_SP):
            # Create and send ascii encoded command via serial, wait for response
            command = f'AZ.{self.__outputPort}P{param}={value}\r'
            self.__serial.write(command.encode('ascii'))

            response = self.__serial.read(self.__serial.in_waiting).decode('ascii').split(sep=',')
            if response[2] == Controller.TYPE_RESPONSE:
                return response[4]
        elif param == Controller.PARAM_PV_MEASURE_UNITS or param == Controller.PARAM_PV_TIME_BASE or param == Controller.PARAM_PV_DECIMAL_POINT or param == Controller.PARAM_PV_GAS_FACTOR or param == Controller.PARAM_PV_LOG_TYPE or (param == Controller.PARAM_PV_SIGNAL_TYPE or param == Controller.PARAM_PV_FULL_SCALE and target == Controller.TARGET_PV):
            command = f'AZ.{self.__inputPort}P{param}={value}\r'
            self.__serial.write(command.encode('ascii'))

            response = self.__serial.read(self.__serial.in_waiting).decode('ascii').split(sep=',')
            if response[2] == Controller.TYPE_RESPONSE:
                return response[4]
        else:
            return None

    # Function that generates a 'gather measurements' command and adds the new data to __samples
    def get_measure(self):
        command = f'AZ.{self.__inputPort}K\r'
        self.__serial.write(command.encode('ascii'))

        response = self.__serial.read(self.__serial.in_waiting).decode('ascii').split(sep=',')

        if response[2] == Controller.TYPE_RESPONSE:
            self.__samples.append(np.float16(response[3]))
            self.__sampleTimestamps.append(datetime.now())

    # From manual: "scale factor by which interpolated channel units are multiplied"
    def set_gas_factor(self, value):
        assert (-999.999 <= value <= 999.999)  # Possible setpoint values according to the datasheet (section C-5-4)
        value = int(value * 1000)  # value is written to serial as XXXXXX without the decimal
        return self.__write_value(Controller.PARAM_PV_GAS_FACTOR, value)

    # Public function to set the head operation point (setpoint)
    def set_setpoint(self, value):
        assert (-999.999 <= value <= 999.999)  # Possible setpoint values according to the datasheet (section C-5-4)
        value = int(value*1000)  # value is written to serial as XXXXXX without the decimal
        return self.__write_value(Controller.PARAM_SP_RATE, value)

    # Sets the setpoint function, rate/batch/blend.
    # Plan is to only use rate.
    def set_function(self, function):
        assert(function == Controller.SP_FUNC_RATE or function == Controller.SP_FUNC_BATCH or function == Controller.SP_FUNC_BLEND)
        return self.__write_value(Controller.PARAM_SP_FUNCTION, function)

    # Sets the maximum possible rate in reference to control signal
    def set_full_scale(self, value):
        assert (-999.999 <= value <= 999.999)  # Possible setpoint values according to the datasheet (section C-5-4)
        value = int(value * 1000)  # value is written to serial as XXXXXX without the decimal
        return self.__write_value(Controller.PARAM_PV_FULL_SCALE, value)

    # Public function to control manual valve override option
    def set_valve_override(self, state):
        assert (state == Controller.VOR_OPTION_NORMAL or state == Controller.VOR_OPTION_CLOSED or state == Controller.VOR_OPTION_OPEN)
        return self.__write_value(Controller.PARAM_SP_VOR, state)

    # Batch/blend ratios setting
    def set_batch(self, value):
        assert (-999.999 <= value <= 999.999)  # Possible setpoint values according to the datasheet (section C-5-4)
        value = int(value * 1000)  # value is written to serial as XXXXXX without the decimal
        return self.__write_value(Controller.PARAM_SP_BATCH, value)

    def set_blend(self, value):
        assert (-999.999 <= value <= 999.999)  # Possible setpoint values according to the datasheet (section C-5-4)
        value = int(value * 1000)  # value is written to serial as XXXXXX without the decimal
        return self.__write_value(Controller.PARAM_SP_BLEND, value)

    # Set the setpoint source
    def set_source(self, source):
        assert(source == Controller.SP_SOURCE_SERIAL or source == Controller.SP_SOURCE_KEYPAD)
        return self.__write_value(Controller.PARAM_SP_SOURCE, source)

    # Save samples to a csv file, named after the current time and controller number it is coming from
    def save_readouts(self):
        now = datetime.now()
        filename = now.strftime(f"controller{self.__channel}_%Y-%m-%d_%H-%M-%S.csv")
        file = open(filename, 'w')
        file.write(f"Gas density:{self.__gasDensity},Gas ID:{self.__gasId},Max flow:{self.__maxFlow}\n")
        file.write("Measurement, Unix timestamp (in milliseconds)\n")
        for i in range(0, self.__sampleBufferSize - 1):
            file.write(f'{self.__samples[i]},{self.__sampleTimestamps[i]}\n')
        file.close()

    # function to change the amount of stored samples without losing previously gathered samples
    def change_buffer_size(self, value):
        assert value >= 8

        if value > self.__sampleBufferSize:
            newBuf = RingBuffer(capacity=value, dtype=np.int16)
            newTimestampBuf = RingBuffer(capacity=value, dtype=np.uint64)

            newBuf.extend(self.__samples)
            newTimestampBuf.extend(self.__sampleTimestamps)

            self.__samples = newBuf
            self.__sampleTimestamps = newTimestampBuf
        elif value < self.__sampleBufferSize:
            newBuf = RingBuffer(capacity=value, dtype=np.int16)
            newTimestampBuf = RingBuffer(capacity=value, dtype=np.uint64)

            newBuf.extend(self.__samples[:-value])
            newTimestampBuf.extend(self.__sampleTimestamps[:-value])

            self.__samples = newBuf
            self.__sampleTimestamps = newTimestampBuf
