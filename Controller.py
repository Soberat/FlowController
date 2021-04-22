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
# Class representing a single Brooks 4850 Mass Flow Controller,
# Handling communication according to the datasheets


class Controller:

    # Process value codes
    PARAM_PV_MEASURE_UNITS = 0x04
    PARAM_PV_TIME_BASE = 0x0A
    PARAM_PV_DECIMAL_POINT = 0x03
    PARAM_PV_GAS_FACTOR = 0x1B
    PARAM_PV_LOG_TYPE = 0x1C
    PARAM_PV_SIGNAL_TYPE = 0x00
    PARAM_PV_FULL_SCALE = 0x09

    # Setpoint value codes
    PARAM_SP_FUNCTION = 0x02
    PARAM_SP_RATE = 0x01
    PARAM_SP_VOR = 0x1D
    PARAM_SP_BATCH = 0x2C
    PARAM_SP_BLEND = 0x2D
    PARAM_SP_SOURCE = 0x2E

    # Response codes - not very well documented, so the meaning is assumed
    RESPONSE_OK = '4'

    def __init__(self, channel, serialConnection, sampleBufferSize=64):
        # Addressing parameters
        self.__channel = channel
        self.__inputPort = 2 * channel - 1
        self.__outputPort = 2 * channel

        # Internal parameters
        self.__sampleBufferSize = sampleBufferSize
        self.__samples = RingBuffer(capacity=self.__sampleBufferSize, dtype=np.uint16)
        self.__sampleTimestamps = RingBuffer(capacity=self.__sampleBufferSize, dtype=np.uint64)

        # Physical device measurements
        self.__temperatureReadout = 0
        self.__flowReadout = 0
        self.__maxFlow = 0
        self.__gasId = 0
        self.__gasDensity = 0

        # PySerial connection
        self.__serial: serial.Serial = serialConnection

    def read_value(self, param):
        if param == Controller.PARAM_SP_FUNCTION or param == Controller.PARAM_SP_RATE or param == Controller.PARAM_SP_VOR or param == Controller.PARAM_SP_BATCH or param == Controller.PARAM_SP_BLEND or param == Controller.PARAM_SP_SOURCE:
            # Create and send ascii encoded command via serial, wait for response
            command = f'AZ.{self.__outputPort}P{param}?\r'
            self.__serial.write(command.encode('ascii'))

            response = self.__serial.read(self.__serial.in_waiting).decode('ascii').split(sep=',')
            if response[2] == Controller.RESPONSE_OK:
                return response[4]
        elif param == Controller.PARAM_PV_MEASURE_UNITS or param == Controller.PARAM_PV_TIME_BASE or param == Controller.PARAM_PV_DECIMAL_POINT or param == Controller.PARAM_PV_GAS_FACTOR or param == Controller.PARAM_PV_LOG_TYPE or param == Controller.PARAM_PV_SIGNAL_TYPE or param == Controller.PARAM_PV_FULL_SCALE:
            command = f'AZ.{self.__inputPort}P{param}?\r'
            self.__serial.write(command.encode('ascii'))

            response = self.__serial.read(self.__serial.in_waiting).decode('ascii').split(sep=',')
            if response[2] == Controller.RESPONSE_OK:
                return response[4]
        else:
            return None

    # This is an internal write functions to be used by the public functions
    # Returns whatever was written to the variable, None if some error occurred
    def __write_value(self, param, value):
        if param == Controller.PARAM_SP_FUNCTION or param == Controller.PARAM_SP_RATE or param == Controller.PARAM_SP_VOR or param == Controller.PARAM_SP_BATCH or param == Controller.PARAM_SP_BLEND or param == Controller.PARAM_SP_SOURCE:
            # Create and send ascii encoded command via serial, wait for response
            command = f'AZ.{self.__outputPort}P{param}={value}\r'
            self.__serial.write(command.encode('ascii'))

            response = self.__serial.read(self.__serial.in_waiting).decode('ascii').split(sep=',')
            if response[2] == Controller.RESPONSE_OK:
                return response[4]
        elif param == Controller.PARAM_PV_MEASURE_UNITS or param == Controller.PARAM_PV_TIME_BASE or param == Controller.PARAM_PV_DECIMAL_POINT or param == Controller.PARAM_PV_GAS_FACTOR or param == Controller.PARAM_PV_LOG_TYPE or param == Controller.PARAM_PV_SIGNAL_TYPE or param == Controller.PARAM_PV_FULL_SCALE:
            command = f'AZ.{self.__inputPort}P{param}={value}\r'
            self.__serial.write(command.encode('ascii'))

            response = self.__serial.read(self.__serial.in_waiting).decode('ascii').split(sep=',')
            if response[2] == Controller.RESPONSE_OK:
                return response[4]
        else:
            return None

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
