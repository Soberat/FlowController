import serial
from serial.tools.list_ports import comports

# communication parameters from datasheet
serialCon = serial.Serial(baudrate=9600,
                          parity=serial.PARITY_NONE,
                          stopbits=serial.STOPBITS_ONE,
                          bytesize=serial.EIGHTBITS)
# setting the COM port after the constructor prevents automatic attempts at connecting
serialCon.port = 'COM3'
