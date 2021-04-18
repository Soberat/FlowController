import numpy as np
import serial


# TODO: threading, as we want 4 parallel controller tabs to be constantly up-to-date with their respective info
# TODO: functions for writing and reading variables
# TODO: Saving measurements - implementation to be determined, probably a ring buffer
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

    def __init__(self):
        # Internal parameters
        self.__controllerNumber = 1

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
    # TODO: should set the setpoint source and initial setpoint, possibly more
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
    def __write_var(self, varid, val1, val2=-1):
        raise NotImplementedError

    # Reads a value/values from the given variable ID
    # May return 1 or 2 bytes - implementation to be determined
    def __read_var(self, varid):
        raise NotImplementedError

    # Returns real flow in sccm using the formula from the datasheet
    def get_real_flow(self):
        raise NotImplementedError

    # Returns the LM50 sensor temperature in Celsius degrees using the formula from the datasheet
    def get_temperature(self):
        raise NotImplementedError
