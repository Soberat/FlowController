import itertools

import numpy as np
import serial
from collections import deque


# Class representing a sensor object that sends data in form of a string
# over a serial connection. Optional header will be added to saved csv file
class Sensor:
    def __init__(self, comport='COM1', baudrate=9600, parity=serial.PARITY_NONE, databits=serial.EIGHTBITS,
                 stopbits=serial.STOPBITS_ONE, dataHeader='', bufferSize=64, datalen=32):
        self.__serial = serial.Serial(baudrate=baudrate,
                                      parity=parity,
                                      bytesize=databits,
                                      stopbits=stopbits,
                                      timeout=0)
        self.__serial.port = comport
        self.__datalen = datalen
        self.header = dataHeader
        self.buffer = deque(maxlen=bufferSize)

    # Open/close serial connection
    def open(self):
        if not self.__serial.is_open:
            self.__serial.open()
        else:
            print(f"Tried to open port {self.__serial.port} when it was open")
            return self.__serial.is_open

    def close(self):
        if self.__serial.is_open:
            self.__serial.close()
        else:
            print(f"Tried to close port {self.__serial.port} when it was closed")
        return self.__serial.is_open

    def change_port(self, port):
        assert not self.__serial.is_open
        self.__serial.port = port

    # This function reads all available data and saves it to the sensor buffer
    # It assumes that data is passed as a newline-terminated string, and the interpretation is up to the user
    def getData(self):
        assert self.__serial.is_open
        buffer = self.__serial.read(self.__datalen)
        if len(buffer) > 0:
            self.buffer.append(buffer.decode('ascii'))

    # function to change the amount of stored samples without losing previously gathered samples
    def change_buffer_size(self, value):
        if value > self.buffer.maxlen:
            newBuffer = deque(maxlen=value)
            newBuffer.extend(self.buffer)

        elif value < self.buffer.maxlen:
            newBuffer = deque(maxlen=value)
            newBuffer.extend(itertools.islice(self.buffer, np.clip(len(self.buffer) - value, 0, None), len(self.buffer)))
            self.buffer = newBuffer
