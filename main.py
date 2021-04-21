import serial
from serial.tools.list_ports import comports

# This code is to be reused by the GUI later on

# communication parameters from datasheet
serialCon = serial.Serial(baudrate=19200,
                          parity=serial.PARITY_NONE,
                          stopbits=serial.STOPBITS_ONE,
                          bytesize=serial.EIGHTBITS)
# setting the COM port after the constructor prevents automatic attempts at connecting
serialCon.port = 'COM3'


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


def get_com_ports():
    return list(comports())
