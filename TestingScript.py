import pyvisa

rm = pyvisa.ResourceManager()
print(sorted(set(rm.list_resources())))
input()
brooks = rm.open_resource('ASRL3::INSTR', write_termination='\r', read_termination='\r\n')
brooks.timeout = 200

idn_response = brooks.query('AZI')

print(idn_response.split(sep=','))

command= 'AZ.1K'
response = brooks.query(command).split(sep=',')
print(response)