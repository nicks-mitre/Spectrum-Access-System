import json
import jsonschema
from pprint import pprint
import os

from typing import Dict, List, Tuple, Optional, Union, NoReturn

# Load in a schema file in the given filename.
def loadSchema(filename: str) -> Dict:
	with open(filename) as sfile:
		schema = json.load(sfile)
		jsonschema.Draft4Validator.check_schema(schema)
		print(f'Loaded and verified schema in {filename}')
		return schema

def loadJson(filename: str) -> Dict:
	with open(filename) as jfile:
		f = json.load(jfile)
		return f

def testJsonSchema(
	schema_file: str,
	test_file: str
) -> int: # int(bool)
	schema = loadSchema(schema_file)
	data = loadJson(test_file)

	print(f'Loaded test validation JSON value from {test_file}:')

	dir = os.path.dirname(os.path.realpath(__file__))
	
	resolver = jsonschema.RefResolver(referrer=schema, base_uri='file://' + dir + '/')

	try:
		jsonschema.validate(data, schema, resolver=resolver)
	except jsonschema.exceptions.ValidationError as e:
		print(e)
		print(f'FAILED VALIDATION for {test_file}')
		pprint(data)
		return 1
	
	print('Validated.')
	return 0

def testJsonSchemaObject(
	schema_file: str,
	test_file: str,
	schemaObject: str
) -> NoReturn:
	schema = loadSchema(schema_file)
	data = loadJson(test_file)
	
	print(f'Loaded test validation JSON value for {schemaObject}:')
	pprint(data)

	jsonschema.validate(data, schema[schemaObject])
	
	print('Validated.')


errors = 0

tests = [
	('InstallationParam.schema.json', 'InstallationParamExample.json'),
	('InstallationParam.schema.json', 'InstallationParamExample2.json'),
	('Response.schema.json', 'ResponseExample.json'),
	('Response.schema.json', 'ResponseExample2.json'),
	('Response.schema.json', 'ResponseExample3.json'),
	('RegistrationRequest.schema.json', 'RegistrationRequestExample.json'),
	('RegistrationRequest.schema.json', 'RegistrationRequestExample2.json'),
	('RegistrationResponse.schema.json', 'RegistrationResponseExample.json'),
	('FrequencyRange.schema.json', 'FrequencyRangeExample.json'),
	('SpectrumInquiryRequest.schema.json', 'SpectrumInquiryRequestExample.json'),
	('SpectrumInquiryResponse.schema.json', 'SpectrumInquiryResponseExample.json'),
	('OperationParam.schema.json', 'OperationParamExample.json'),
	('RelinquishmentRequest.schema.json', 'RelinquishmentRequestExample.json'),
	('RelinquishmentResponse.schema.json', 'RelinquishmentResponseExample.json'),
	('DeregistrationRequest.schema.json', 'DeregistrationRequestExample.json'),
	('DeregistrationResponse.schema.json', 'DeregistrationResponseExample.json'),
	('GrantRequest.schema.json', 'GrantRequestExample.json'),
	('GrantResponse.schema.json', 'GrantResponseExample.json'),
	('HeartbeatRequest.schema.json', 'HeartbeatRequestExample.json'),
	('HeartbeatResponse.schema.json', 'HeartbeatResponseExample.json'),
	('MeasReport.schema.json', 'MeasReportExample.json'),
	('PalRecord.schema.json', 'PalRecordExample.json'),
	('FullActivityDump.schema.json', 'FullActivityDumpExample.json'),
	('InstallationParamData.schema.json', 'InstallationParamDataExample.json'),
	('CbsdRecordData.schema.json', 'CbsdRecordDataExample.json'),
	('GrantRecord.schema.json', 'GrantRecordExample.json'),
	('ZoneData.schema.json', 'ZoneDataOfPpaExample.json'),
	('EscSensorRecord.schema.json', 'EscSensorRecordExample.json')
]

for t in tests:
	errors += testJsonSchema(t[0], t[1])

if errors == 0:
	print('PASS')
else:
	print(f'FAIL: {errors} validation errors')


