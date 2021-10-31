from Controller import Controller
from bidict import bidict
import pyvisa


class Brooks025X:
    BOOL_OPTIONS = bidict({
        True: '1',
        False: '0'
    })

    PARAM_ZERO_SUPPRESS = 0x20
    PARAM_POWER_SP_CLEAR = 0x21
    PARAM_AUDIO_BEEP = 0x27
    PARAM_RECORD_COUNT = 0x2b
    PARAM_SAMPLE_RATE = 0x19
    PARAM_DATE_TIME = 0x16
    PARAM_NETWORK_ADDRESS = 0x11

    # `controllers` argument describes which controller numbers should be created
    def __init__(self, pyvisaConnection, controllers, deviceAddress=None):
        self.__connection = pyvisaConnection
        self.__address = deviceAddress
        self.__controllers = controllers
        self.controller1 = None
        self.controller2 = None
        self.controller3 = None
        self.controller4 = None

        if controllers[0]:
            try:
                self.controller1 = Controller(channel=1, pyvisaConnection=pyvisaConnection, deviceAddress=self.__address)
            except pyvisa.errors.VisaIOError as vioe:
                print(f"Error while creating controller 1: {vioe}")

        if controllers[1]:
            try:
                self.controller2 = Controller(channel=2, pyvisaConnection=pyvisaConnection, deviceAddress=self.__address)
            except pyvisa.errors.VisaIOError as vioe:
                print(f"Error while creating controller 2: {vioe}")

        if controllers[2]:
            try:
                self.controller3 = Controller(channel=3, pyvisaConnection=pyvisaConnection, deviceAddress=self.__address)
            except pyvisa.errors.VisaIOError as vioe:
                print(f"Error while creating controller 3: {vioe}")

        if controllers[3]:
            try:
                self.controller4 = Controller(channel=4, pyvisaConnection=pyvisaConnection, deviceAddress=self.__address)
            except pyvisa.errors.VisaIOError as vioe:
                print(f"Error while creating controller 4: {vioe}")

    def set_audio_beep(self, value: bool):
        value = self.BOOL_OPTIONS[value]

        # Create and send ascii encoded command via serial, wait for response
        if self.__address is None:
            command = f'AZ.9P{self.PARAM_AUDIO_BEEP}={value}'
        else:
            command = f'AZ{self.__address}.9P{self.PARAM_AUDIO_BEEP}={value}'
        response = self.__connection.query(command).split(sep=',')

        return response[2] == Controller.TYPE_RESPONSE

    def set_zero_suppress(self, value: bool):
        value = self.BOOL_OPTIONS[value]

        # Create and send ascii encoded command via serial, wait for response
        if self.__address is None:
            command = f'AZ.9P{self.PARAM_ZERO_SUPPRESS}={value}'
        else:
            command = f'AZ{self.__address}.9P{self.PARAM_ZERO_SUPPRESS}={value}'
        response = self.__connection.query(command).split(sep=',')

        return response[2] == Controller.TYPE_RESPONSE

    def set_power_sp_clear(self, value: bool):
        value = self.BOOL_OPTIONS[value]

        # Create and send ascii encoded command via serial, wait for response
        if self.__address is None:
            command = f'AZ.9P{self.PARAM_POWER_SP_CLEAR}={value}'
        else:
            command = f'AZ{self.__address}.9P{self.PARAM_POWER_SP_CLEAR}={value}'
        response = self.__connection.query(command).split(sep=',')

        return response[2] == Controller.TYPE_RESPONSE

    def get_audio_beep(self):
        if self.__address is None:
            command = f'AZ.9P{self.PARAM_AUDIO_BEEP}?'
        else:
            command = f'AZ{self.__address}.9P{self.PARAM_AUDIO_BEEP}?'
        response = self.__connection.query(command).split(sep=',')

        if response[2] == Controller.TYPE_RESPONSE:
            return self.BOOL_OPTIONS.inverse[response[4]]
        else:
            return None

    def get_zero_suppress(self):
        if self.__address is None:
            command = f'AZ.9P{self.PARAM_ZERO_SUPPRESS}?'
        else:
            command = f'AZ{self.__address}.9P{self.PARAM_ZERO_SUPPRESS}?'
        response = self.__connection.query(command).split(sep=',')

        if response[2] == Controller.TYPE_RESPONSE:
            return self.BOOL_OPTIONS.inverse[response[4]]
        else:
            return None

    def get_power_sp_clear(self):
        if self.__address is None:
            command = f'AZ.9P{self.PARAM_POWER_SP_CLEAR}?'
        else:
            command = f'AZ{self.__address}.9P{self.PARAM_POWER_SP_CLEAR}?'
        response = self.__connection.query(command).split(sep=',')

        if response[2] == Controller.TYPE_RESPONSE:
            return self.BOOL_OPTIONS.inverse[response[4]]
        else:
            return None

    def get_network_address(self):
        if self.__address is None:
            command = f'AZ.9P{self.PARAM_NETWORK_ADDRESS}?'
        else:
            command = f'AZ{self.__address}.9P{self.PARAM_NETWORK_ADDRESS}?'
        response = self.__connection.query(command).split(sep=',')

        if response[2] == Controller.TYPE_RESPONSE:
            return response[4]
        else:
            return None
