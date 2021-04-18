import numpy as np
import serial
from numpy_ringbuffer import RingBuffer


# TODO: threading, as we want 4 parallel controller tabs to be constantly up-to-date with their respective info
# TODO: Saving measurements
# TODO: Setting preconfiguring parameters (head type, gas type)
# TODO: Timed dosing functions
# TODO: public functions to be used by the GUI
# TODO: Timed measurements
# Class representing a single Brooks 4850 Mass Flow Controller,
# Handling communication according to the datasheets
class Controller:
    # Request codes constants
    REQUEST_SEND_ONE_DATA = 0x31
    REQUEST_SEND_N_DATA = 0x32
    REQUEST_SEND_CONTINUOUS = 0x33
    REQUEST_STOP = 0x34
    REQUEST_READ_SERIAL_MFC = 0x68
    REQUEST_READ_GASINFO = 0x72

    REQUEST_READ_VAR_INT16 = 0x61
    REQUEST_WRITE_VAR_INT16 = 0x62
    REQUEST_READ_VAR_CHAR = 0x63
    REQUEST_WRITE_VAR_CHAR = 0x64

    # Error codes constants
    REQUEST_ERROR = 0x45
    ERROR_SEND_TIMEOUT = 0x01
    ERROR_SENSOR_BUSY = 0x02
    ERROR_CHECKSUM_ERROR = 0x03
    ERROR_OVERRUN_ERROR = 0x04
    ERROR_FRAME_ERROR = 0x08
    ERROR_PARITY_ERROR = 0x10
    ERROR_START_ERROR = 0x20
    ERROR_INVALID_REQ = 0x40
    ERROR_UNKNOWN_VARID = 0xC0

    # Device variable codes (or IDs as called in the datasheet)
    VAR_SN = 0
    VAR_SW_VERSION = 1
    VAR_OFFSET = 3
    VAR_OFFSET_VAL = 4
    VAR_CALIB_GAS = 5
    VAR_GAS_TYPE = 6
    VAR_ADC_TEMP = 15
    VAR_SETPOINT = 20
    VAR_OVERRIDE = 30
    VAR_SETPOINT_SOURCE = 31
    VAR_VALVE_STATE = 33
    VAR_OUT_SELECT = 100

    # Other constants
    CONST_VALVE_OPEN = 2
    CONST_VALVE_CLOSED = 1
    CONST_VALVE_NORMAL = 0

    CONST_SETPOINT_SERIAL = 0
    CONST_SETPOINT_VOLTAGE = 1
    CONST_SETPOINT_CURRENT = 2

    def __init__(self, controllerNumber, sampleBufferSize=64):
        # Internal parameters
        self.__controllerNumber = controllerNumber
        self.__sampleBufferSize = sampleBufferSize
        self.__samples = RingBuffer(capacity=self.__sampleBufferSize, dtype=np.uint16)
        self.__sampleTimestamps = RingBuffer(capacity=self.__sampleBufferSize, dtype=np.uint32)

        # COM port parameters
        self.__deviceId = ""
        self.__deviceName = ""

        # USB device info - unknown if needed
        self.__deviceVid = 0
        self.__devicePid = 0
        self.__deviceSN = ""
        self.__deviceLoc = ""
        self.__deviceManufacturer = ""
        self.__deviceModel = ""
        self.__deviceInterface = ""

        # PySerial connection
        self.__serial = serial.Serial(port='COM3',
                                      baudrate=57600,
                                      parity=serial.PARITY_ODD,
                                      stopbits=serial.STOPBITS_ONE,
                                      bytesize=serial.EIGHTBITS,
                                      timeout=1)

    # function that opens the serial port communication and configures anything else that's required
    # TODO: should set the setpoint source and initial setpoint, get and set COM/USB parameters, possibly more
    def open(self):
        if not self.__serial.is_open:
            self.__serial.open()
        else:
            print("Tried to open port {cNum} when it was opened".format(cNum=self.__controllerNumber))
        return self.__serial.is_open

    # TODO: Should reverse what open() did - set the setpoint control to voltage, possibly more
    def close(self):
        if self.__serial.is_open:
            self.__serial.close()
        else:
            print("Tried to close port {cNum} when it was closed".format(cNum=self.__controllerNumber))
        return self.__serial.is_open

    # We assume the 'port' argument is taken from ListPortInfo.name.
    # This should preserve compatibility between operating systems
    # Even though the function checks if the serial port is already open,
    # the GUI should also prevent the users form changing the port while it's open.
    def change_port(self, port):
        if not self.__serial.is_open:
            self.__serial.port = port

    # Tries to write given value(s) to the given variable ID
    # val2 is ignored if the given variable ID requires 1 byte
    def __write_var(self, varid, val1, val2=0):
        assert self.__serial.is_open
        # All writeable variables are of type uint
        assert val1 >= 0
        assert val2 >= 0

        # Setpoint is the only 16bit writeable variable, others are 8bit
        if varid == Controller.VAR_SETPOINT:
            # The checksum is sum of all message bytes including request byte, modulo 256
            checksum = (Controller.REQUEST_WRITE_VAR_CHAR + varid + val1 + val2) % 256
            self.__serial.write([Controller.REQUEST_WRITE_VAR_CHAR, varid, val1, val2, checksum])
        elif varid == Controller.VAR_OFFSET or varid == Controller.VAR_GAS_TYPE or varid == Controller.VAR_OVERRIDE or varid == Controller.VAR_SETPOINT_SOURCE:
            checksum = (Controller.REQUEST_WRITE_VAR_CHAR + varid + val1) % 256
            self.__serial.write([Controller.REQUEST_WRITE_VAR_CHAR, varid, val1, checksum])
        else:
            raise ValueError(
                "Unknown variable code was passed to __write_var (might be Output Select, which is not currently supported) (ID: {value})".format(
                    value=varid))

    # Reads a value/values from the given variable ID
    # Returns a list of length 1 or 2 depending on the requested
    def __read_var(self, varid):
        assert self.__serial.is_open

        # 8bit variables
        if varid == Controller.VAR_OFFSET or varid == Controller.VAR_CALIB_GAS or varid == Controller.VAR_GAS_TYPE or varid == Controller.VAR_OVERRIDE or varid == Controller.VAR_SETPOINT_SOURCE or varid == Controller.VAR_VALVE_STATE:
            checksum = (Controller.REQUEST_READ_VAR_CHAR + varid) % 256
            self.__serial.write([Controller.REQUEST_READ_VAR_CHAR, varid, checksum])
            response = self.__serial.read(3)  # we expect a response code, variable value and a checksum
            return list(response[1:2])
        elif varid == Controller.VAR_SN or varid == Controller.VAR_SW_VERSION or varid == Controller.VAR_OFFSET_VAL or varid == Controller.VAR_ADC_TEMP or varid == Controller.VAR_SETPOINT:
            checksum = (Controller.REQUEST_READ_VAR_INT16 + varid) % 256
            self.__serial.write([Controller.REQUEST_READ_VAR_INT16, varid, checksum])
            response = self.__serial.read(4)  # we expect a response code, two variable values and a checksum
            return list(response[1:3])
        else:
            raise ValueError(
                "Unknown variable code was passed to __read_var (might be Output Select, which is not currently supported) (ID: {value})".format(
                    value=varid))

    # Returns real flow in sccm using the formula from the datasheet
    def get_real_flow(self):
        raise NotImplementedError

    # Returns the LM50 sensor temperature in Celsius degrees using the formula from the datasheet
    def get_temperature(self):
        raise NotImplementedError
