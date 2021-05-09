import serial

ser = serial.Serial(port=None,
                    baudrate=9600,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=None)

ser.port = 'COM3'
ser.open()
print(f"Is serial open? {ser.isOpen()}")
assert ser.isOpen()

print("Trying identity command...")
ser.write("AZI\r".encode('ascii'))
response = ser.read_until('\n'.encode('ascii')).decode()
print(f"Identity response: {response}")

print("Trying measurement command...")
ser.write("AZ.1K\r".encode('ascii'))
response = ser.read_until('\n'.encode('ascii')).decode()
print(f"Controller 1 response: {response}")

ser.write("AZ.3K\r".encode('ascii'))
response = ser.read_until('\n'.encode('ascii')).decode()
print(f"Controller 2 response: {response}")

ser.write("AZ.5K\r".encode('ascii'))
response = ser.read_until('\n'.encode('ascii')).decode()
print(f"Controller 3 response: {response}")

ser.write("AZ.7K\r".encode('ascii'))
response = ser.read_until('\n'.encode('ascii')).decode()
print(f"Controller 4 response: {response}")
