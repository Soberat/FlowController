import numpy as np
import serial
from numpy_ringbuffer import RingBuffer
from datetime import datetime


# TODO: threading, as we want 4 parallel controller tabs to be constantly up-to-date with their respective info
# TODO: Saving measurements
# TODO: Setting preconfiguring parameters (head type, gas type)
# TODO: Timed dosing functions
# TODO: public functions to be used by the GUI
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
        self.__sampleTimestamps = RingBuffer(capacity=self.__sampleBufferSize, dtype=np.uint64)

        # Physical device measurements
        self.__temperatureReadout = 0
        self.__flowReadout = 0
        self.__maxFlow = 0
        self.__gasId = 0
        self.__gasDensity = 0

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
        self.__serial = serial.Serial(baudrate=57600,
                                      parity=serial.PARITY_ODD,
                                      stopbits=serial.STOPBITS_ONE,
                                      bytesize=serial.EIGHTBITS,
                                      timeout=1)
        self.__serial.port = 'COM3'

    # function that opens the serial port communication and configures anything else that's required
    # TODO: should set the setpoint source and initial setpoint, get and set COM/USB parameters,
    #  get gas parameters, possibly more
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

    # Save samples to a csv file, named after the current time and controller number it is coming from
    def save_readouts(self):
        now = datetime.now()
        filename = now.strftime(f"controller{self.__controllerNumber}_%Y-%m-%d_%H-%M-%S.csv")
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
