import serial
from serial.tools.list_ports import comports


def get_com_ports():
    return list(comports())
