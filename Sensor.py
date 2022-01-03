import itertools

import numpy as np
import serial
from collections import deque


# Class representing a sensor object that sends data in form of a string
# over a serial connection. Optional header will be added to saved csv file
class Sensor:
    def __init__(self, comport='COM1', baudrate=9600, parity=serial.PARITY_NONE, databits=serial.EIGHTBITS,
                 stopbits=serial.STOPBITS_ONE, dataHeader='', bufferSize=64, command=":MEAS?"):
        self.__serial = serial.Serial(baudrate=baudrate,
                                      parity=parity,
                                      bytesize=databits,
                                      stopbits=stopbits,
                                      timeout=100,
                                      port=comport)
        self.header = dataHeader
        self.buffer = deque(maxlen=bufferSize)
        self.command = command

    # Close serial connection
    def close(self):
        if self.__serial.is_open:
            self.__serial.close()
        else:
            print(f"Tried to close port {self.__serial.port} when it was closed")
        return self.__serial.is_open

    # This function reads all available data and saves it to the sensor buffer
    # It assumes that data is passed as a newline-terminated string, and the interpretation is up to the user
    def get_data(self):
        assert self.__serial.is_open
        self.__serial.write(f"{self.command}\n".encode())
        response = self.__serial.readline()
        if len(response) > 0:
            self.buffer.append(response.decode('utf-8'))

    # function to change the amount of stored samples without losing previously gathered samples
    def change_buffer_size(self, value):
        if value > self.buffer.maxlen:
            newBuffer = deque(maxlen=value)
            newBuffer.extend(self.buffer)

        elif value < self.buffer.maxlen:
            newBuffer = deque(maxlen=value)
            newBuffer.extend(itertools.islice(self.buffer, np.clip(len(self.buffer) - value, 0, None), len(self.buffer)))
            self.buffer = newBuffer
