import serial
from numpy_ringbuffer import RingBuffer


# Class representing a sensor object that sends data in form of a string
# over a serial connection. Optional header will be added to saved csv file
class Sensor:
    def __init__(self, comport='COM1', baudrate=9600, parity=serial.PARITY_NONE, databits=serial.EIGHTBITS, stopbits=serial.STOPBITS_ONE, dataHeader='', bufferSize=128):
        self.__serial = serial.Serial(baudrate=baudrate,
                                      parity=parity,
                                      databits=databits,
                                      stopbits=stopbits)
        self.__serial.port = comport
        self.__bufferSize = bufferSize
        self.buffer = RingBuffer(capacity=bufferSize, dtype=str)
        self.header = dataHeader

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
    # It assumes that data is passed as a string, and the interpretation is up to the user
    def getData(self):
        assert self.__serial.is_open
        self.buffer.append(self.__serial.readall())

    # function to change the amount of stored samples without losing previously gathered samples
    def change_buffer_size(self, value):
        if value > self.__bufferSize:
            newBuffer = RingBuffer(capacity=value, dtype=str)
            newBuffer.extend(self.buffer)
            self.buffer = newBuffer
        elif value < self.__bufferSize:
            newBuffer = RingBuffer(capacity=value, dtype=str)
            newBuffer.extend(self.buffer[:-value])
            self.buffer = newBuffer

