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

    # function that reads a given amount of bytes (8 bit frames), handles transmission errors,
    # verifies the checksum and returns the read data (if no errors occurred)
    def __get_response(self, frames):
        response = self.__serial.read(frames)

        # If the request code indicates an error, we just notify the user and don't do anything
        if response[0] == self.REQUEST_ERROR:
            print(f"Controller returned an error code: {response[1]}")
            return None

        # Verify checksum by taking the sum of all relevant bytes modulo 256, and checking it against sent checksum
        # (last byte of the response) and returning the relevant data (None is returned if errors occurred)
        if np.sum(response[0:len(response) - 1]) % 256 == response[-1]:
            values = response[1:len(response) - 1]
            if len(values) == 1:
                return values[0]
            elif len(values) == 2:
                return values[0] << 8 + values[1]  # 16 bit value, MSB first
            else:
                return values  # if for some reason the response is longer than 2 bytes return the whole list
        else:
            print(f"Error while verifying checksum: {response}")
            return None

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

    # Tries to write given value(s) to the given variable ID
    # val2 is ignored if the given variable ID requires 1 byte
    # This returns if writing was successful according to __get_response to maintain the function signature
    def __write_var(self, varid, val1, val2=0):
        assert self.__serial.is_open
        # All writeable variables are of type uint
        assert val1 >= 0
        assert val2 >= 0

        # Setpoint is the only 16bit writeable variable, others are 8bit
        if varid == Controller.VAR_SETPOINT:
            # The checksum is sum of all message bytes including request byte, modulo 256
            checksum = (Controller.REQUEST_WRITE_VAR_INT16 + varid + val1 + val2) % 256
            self.__serial.write([Controller.REQUEST_WRITE_VAR_INT16, varid, val1, val2, checksum])
            response = self.__get_response(2)  # we expect a request code and a checksum
            return response is not None
        elif varid == Controller.VAR_OFFSET or varid == Controller.VAR_GAS_TYPE or varid == Controller.VAR_OVERRIDE or varid == Controller.VAR_SETPOINT_SOURCE:
            checksum = (Controller.REQUEST_WRITE_VAR_CHAR + varid + val1) % 256
            self.__serial.write([Controller.REQUEST_WRITE_VAR_CHAR, varid, val1, checksum])
            response = self.__get_response(2)  # we expect a request code and a checksum
            return response is not None
        else:
            raise ValueError(
                "Unknown variable code was passed to __write_var (might be Output Select, which is not currently "
                "supported) (ID: {value})".format(
                    value=varid))

    # Reads a value/values from the given variable ID
    # Returns an integer with the requested value or None when an error occurred
    # Since VAR_OFFSET_VAL is of type int16 there is a possibility that offset of -1
    # might be interpreted as a wrong checksum, but that probability is very low.
    def __read_var(self, varid):
        assert self.__serial.is_open

        # 8bit variables
        if varid == Controller.VAR_OFFSET or varid == Controller.VAR_CALIB_GAS or varid == Controller.VAR_GAS_TYPE or varid == Controller.VAR_OVERRIDE or varid == Controller.VAR_SETPOINT_SOURCE or varid == Controller.VAR_VALVE_STATE:
            checksum = (Controller.REQUEST_READ_VAR_CHAR + varid) % 256
            self.__serial.write([Controller.REQUEST_READ_VAR_CHAR, varid, checksum])
            return self.__get_response(3) # we expect a request code, a value and a checksum
        elif varid == Controller.VAR_SN or varid == Controller.VAR_SW_VERSION or varid == Controller.VAR_OFFSET_VAL or varid == Controller.VAR_ADC_TEMP or varid == Controller.VAR_SETPOINT:
            checksum = (Controller.REQUEST_READ_VAR_INT16 + varid) % 256
            self.__serial.write([Controller.REQUEST_READ_VAR_INT16, varid, checksum])
            return self.__get_response(4)  # request code, two 8 bit values and a checksum
        else:
            raise ValueError(
                "Unknown variable code was passed to __read_var (might be Output Select, which is not currently "
                "supported) (ID: {value})".format(
                    value=varid))

    # Returns real flow in sccm using the formula from the datasheet
    def get_real_flow(self):
        self.get_percentage_flow()  # this updates the flowReadout, so we avoid duplicating code
        # save the readout to the buffers
        self.__samples.append(self.__maxFlow * self.__flowReadout)
        self.__sampleTimestamps.append(np.uint64(datetime.now().timestamp() * 1000))
        return self.__maxFlow * self.__flowReadout

    # Return a percentage of the flow value, in reference to the maximum flow value
    def get_percentage_flow(self):
        assert self.__serial.is_open
        # this request takes no parameters, therefore the request ID is also the checksum
        self.__serial.write([Controller.REQUEST_SEND_ONE_DATA,
                             Controller.REQUEST_SEND_ONE_DATA])
        response = self.__get_response(3)
        if response is not None:
            self.__flowReadout = response[1] / 10000.0
        else:
            self.__flowReadout = -1.0
        return self.__flowReadout

    # Returns the LM50 sensor temperature in Celsius degrees using the formula from the datasheet
    def get_temperature(self):
        assert self.__serial.is_open

        self.__temperatureReadout = self.__read_var(Controller.VAR_ADC_TEMP)
        return 100 * ((self.__temperatureReadout / 65535) + 1. / 6)

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

    # Set the valve override mode either to open, closed or normal (setpoint controlled)
    def set_valve_override(self, state):
        if state == self.CONST_VALVE_OPEN or state == self.CONST_VALVE_CLOSED or state == self.CONST_VALVE_NORMAL:
            return self.__write_var(self.REQUEST_WRITE_VAR_CHAR, self.VAR_OVERRIDE, state)
        else:
            print("Wrong valve override state selected")
            return False

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
