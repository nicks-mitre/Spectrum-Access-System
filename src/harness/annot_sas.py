#		Copyright 2018 SAS Project Authors. All Rights Reserved.
#
#		Licensed under the Apache License, Version 2.0 (the "License");
#		you may not use this file except in compliance with the License.
#		You may obtain a copy of the License at
#
#				http://www.apache.org/licenses/LICENSE-2.0
#
#		Unless required by applicable law or agreed to in writing, software
#		distributed under the License is distributed on an "AS IS" BASIS,
#		WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#		See the License for the specific language governing permissions and
#		limitations under the License.
"""Implementation of SasInterface."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os

from six.moves import configparser

from request_handler import TlsConfig, RequestPost, RequestGet
import sas_interface

from typing import Dict, List, Tuple, Any, Optional, Union

# Type alias to annotate that a param is of str type, but also optional
# The "Optional" annotation is only necessary when the default is None
OptStr = Optional[str]


def GetTestingSas() -> SasImpl:
	config_parser = configparser.RawConfigParser()
	config_parser.read(['sas.cfg'])
	admin_api_base_url = config_parser.get('SasConfig', 'AdminApiBaseUrl')
	cbsd_sas_rsa_base_url = config_parser.get('SasConfig', 'CbsdSasRsaBaseUrl')
	cbsd_sas_ec_base_url = config_parser.get('SasConfig', 'CbsdSasEcBaseUrl')
	sas_sas_rsa_base_url = config_parser.get('SasConfig', 'SasSasRsaBaseUrl')
	sas_sas_ec_base_url = config_parser.get('SasConfig', 'SasSasEcBaseUrl')
	cbsd_sas_version = config_parser.get('SasConfig', 'CbsdSasVersion')
	sas_sas_version = config_parser.get('SasConfig', 'SasSasVersion')
	sas_admin_id = config_parser.get('SasConfig', 'AdminId')
	maximum_batch_size = config_parser.get('SasConfig', 'MaximumBatchSize')
	return SasImpl(
			cbsd_sas_rsa_base_url,
			cbsd_sas_ec_base_url,
			sas_sas_rsa_base_url,
			sas_sas_ec_base_url,
			cbsd_sas_version,
			sas_sas_version,
			sas_admin_id,
			maximum_batch_size), SasAdminImpl(admin_api_base_url)


def GetDefaultDomainProxySSLCertPath() -> str:
	return os.path.join('certs', 'domain_proxy.cert')


def GetDefaultDomainProxySSLKeyPath() -> str:
	return os.path.join('certs', 'domain_proxy.key')


def GetDefaultSasSSLCertPath() -> str:
	return os.path.join('certs', 'sas.cert')


def GetDefaultSasSSLKeyPath() -> str:
	return os.path.join('certs', 'sas.key')


class SasImpl(sas_interface.SasInterface):
	"""Implementation of SasInterface for SAS certification testing."""

	def __init__(self, cbsd_sas_rsa_base_url, cbsd_sas_ec_base_url,
			sas_sas_rsa_base_url, sas_sas_ec_base_url, cbsd_sas_version,
			sas_sas_version, sas_admin_id, maximum_batch_size):
		self._cbsd_sas_rsa_base_url = cbsd_sas_rsa_base_url
		self._cbsd_sas_ec_base_url = cbsd_sas_ec_base_url
		self._sas_sas_rsa_base_url = sas_sas_rsa_base_url
		self._sas_sas_ec_base_url = sas_sas_ec_base_url
		self.cbsd_sas_active_base_url = cbsd_sas_rsa_base_url
		self.sas_sas_active_base_url = sas_sas_rsa_base_url
		self.cbsd_sas_version = cbsd_sas_version
		self.sas_sas_version = sas_sas_version
		self._tls_config = TlsConfig()
		self._sas_admin_id = sas_admin_id
		self.maximum_batch_size = int(maximum_batch_size)

	def Registration(
		self,
		request: Dict,
		ssl_cert: OptStr = None,
		ssl_key: OptStr = None
	) -> Dict:
		"""SAS-CBSD Registration interface implementation for SAS Certification testing.

		Registers CBSDs.

		Request and response are both lists of dictionaries. Each dictionary
		contains all fields of a single request/response.

		Args:
			request: A dictionary with a single key-value pair where the key is
				"registrationRequest" and the value is a list of individual CBSD
				registration requests (each of which is itself a dictionary).
			ssl_cert: Path to SSL cert file, if None, will use default cert file.
			ssl_key: Path to SSL key file, if None, will use default key file.
		Returns:
			A dictionary with a single key-value pair where the key is
			"registrationResponse" and the value is a list of individual CBSD
			registration responses (each of which is itself a dictionary).
		"""
		return self._CbsdRequest('registration', request, ssl_cert, ssl_key)

	def SpectrumInquiry(
		self,
		request: Dict,
		ssl_cert: OptStr = None,
		ssl_key: OptStr = None
	) -> Dict:
		"""SAS-CBSD SpectrumInquiry interface implementation for SAS Certification testing.

		Performs spectrum inquiry for CBSDs.

		Request and response are both lists of dictionaries. Each dictionary
		contains all fields of a single request/response.

		Args:
			request: A dictionary with a single key-value pair where the key is
				"spectrumInquiryRequest" and the value is a list of individual CBSD
				spectrum inquiry requests (each of which is itself a dictionary).
			ssl_cert: Path to SSL cert file, if None, will use default cert file.
			ssl_key: Path to SSL key file, if None, will use default key file.
		Returns:
			A dictionary with a single key-value pair where the key is
			"spectrumInquiryResponse" and the value is a list of individual CBSD
			spectrum inquiry responses (each of which is itself a dictionary).
		"""
		return self._CbsdRequest('spectrumInquiry', request, ssl_cert, ssl_key)

	def Grant(
		self,
		request: Dict,
		ssl_cert: OptStr = None,
		ssl_key: OptStr = None
	) -> Dict:
		"""SAS-CBSD Grant interface implementation for SAS Certification testing.

		Request and response are both lists of dictionaries. Each dictionary
		contains all fields of a single request/response.

		Args:
			request: A dictionary with a single key-value pair where the key is
				"grantRequest" and the value is a list of individual CBSD
				grant requests (each of which is itself a dictionary).
			ssl_cert: Path to SSL cert file, if None, will use default cert file.
			ssl_key: Path to SSL key file, if None, will use default key file.
		Returns:
			A dictionary with a single key-value pair where the key is
			"grantResponse" and the value is a list of individual CBSD
			grant responses (each of which is itself a dictionary).
		"""
		return self._CbsdRequest('grant', request, ssl_cert, ssl_key)

	def Heartbeat(
		self,
		request: Dict,
		ssl_cert: OptStr = None,
		ssl_key: OptStr = None
	) -> Dict:
		"""SAS-CBSD Heartbeat interface implementation for SAS Certification testing.

		Requests heartbeat for a grant for CBSDs.

		Request and response are both lists of dictionaries. Each dictionary
		contains all fields of a single request/response.

		Args:
			request: A dictionary with a single key-value pair where the key is
				"heartbeatRequest" and the value is a list of individual CBSD
				heartbeat requests (each of which is itself a dictionary).
			ssl_cert: Path to SSL cert file, if None, will use default cert file.
			ssl_key: Path to SSL key file, if None, will use default key file.
		Returns:
			A dictionary with a single key-value pair where the key is
			"heartbeatResponse" and the value is a list of individual CBSD
			heartbeat responses (each of which is itself a dictionary).
		"""
		return self._CbsdRequest('heartbeat', request, ssl_cert, ssl_key)

	def Relinquishment(
		self,
		request: Dict,
		ssl_cert: OptStr = None,
		ssl_key: OptStr = None
	) -> Dict:
		"""SAS-CBSD Relinquishment interface implementation for SAS Certification testing.

		Relinquishes grant for CBSDs.

		Request and response are both lists of dictionaries. Each dictionary
		contains all fields of a single request/response.

		Args:
			request: A dictionary with a single key-value pair where the key is
				"relinquishmentRequest" and the value is a list of individual CBSD
				relinquishment requests (each of which is itself a dictionary).
			ssl_cert: Path to SSL cert file, if None, will use default cert file.
			ssl_key: Path to SSL key file, if None, will use default key file.
		Returns:
			A dictionary with a single key-value pair where the key is
			"relinquishmentResponse" and the value is a list of individual CBSD
			relinquishment responses (each of which is itself a dictionary).
		"""
		return self._CbsdRequest('relinquishment', request, ssl_cert, ssl_key)

	def Deregistration(
		self,
		request: Dict,
		ssl_cert: OptStr = None,
		ssl_key: OptStr = None
	) -> Dict:
		"""SAS-CBSD Deregistration interface implementation for SAS Certification testing.

		Deregisters CBSDs.

		Request and response are both lists of dictionaries. Each dictionary
		contains all fields of a single request/response.

		Args:
			request: A dictionary with a single key-value pair where the key is
				"deregistrationRequest" and the value is a list of individual CBSD
				deregistration requests (each of which is itself a dictionary).
			ssl_cert: Path to SSL cert file, if None, will use default cert file.
			ssl_key: Path to SSL key file, if None, will use default key file.
		Returns:
			A dictionary with a single key-value pair where the key is
			"deregistrationResponse" and the value is a list of individual CBSD
			deregistration responses (each of which is itself a dictionary).
		"""
		return self._CbsdRequest('deregistration', request, ssl_cert, ssl_key)

	def GetEscSensorRecord(
		self,
		request: Dict,
		ssl_cert: OptStr = None,
		ssl_key: OptStr = None
	) -> Dict:
		"""SAS-SAS ESC Sensor Record Exchange interface implementation for SAS Certification testing.

		Requests a Pull Command to get the ESC Sensor Data Message

		Args:
			request: A string containing Esc Sensor Record Id
			ssl_cert: Path to SSL cert file, if None, will use default cert file.
			ssl_key: Path to SSL key file, if None, will use default key file.
		Returns:
			A dictionary of Esc Sensor Data Message object specified in
			WINNF-16-S-0096
		"""
		return self._SasRequest('esc_sensor', request, ssl_cert, ssl_key)

	def GetFullActivityDump(
		self,
		ssl_cert: OptStr = None,
		ssl_key: OptStr = None
	) -> Dict:
		"""SAS-SAS Full Activity Dump interface implementation for SAS Certification testing.

		Requests a Pull Command to get Full Activity Dump Message.

		Args:
			ssl_cert: Path to SSL cert file, if None, will use default cert file.
			ssl_key: Path to SSL key file, if None, will use default key file.
		Returns:
			A dictionary containing the FullActivityDump object specified in WINNF-16-S-0096
		"""
		return self._SasRequest('dump', None, ssl_cert, ssl_key)

	def _SasRequest(
		self,
		method_name: str,
		request: Optional[Dict],
		ssl_cert: OptStr = None,
		ssl_key: OptStr = None
	) -> Dict: # Functions using _Request() return a dict repr. a JSON response
		url = f'https://{self.sas_sas_active_base_url}/{self.sas_sas_version}/{method_name}'
		
		if request is not None:
			url = str.join(url, f'/{request}')
		
		# if ssl_cert or key_path is None, then use default
		cert_path = ssl_cert or GetDefaultSasSSLCertPath()
		key_path = ssl_key or GetDefaultSasSSLKeyPath()
		tlsconf = self._tls_config.WithClientCertificate(cert_path, key_path)

		return RequestGet(url, tlsconf)

	def _CbsdRequest(
		self,
		method_name: str,
		request: Dict,
		ssl_cert: OptStr = None,
		ssl_key: OptStr = None
	) -> Dict:
		url = f'https://{self.cbsd_sas_active_base_url}/{self.cbsd_sas_version}/{method_name}'
		
		# if ssl_cert or key_path is None, then use default
		cert_path = ssl_cert or GetDefaultDomainProxySSLCertPath()
		key_path = ssl_key or GetDefaultDomainProxySSLKeyPath()
		tlsconf = self._tls_config.WithClientCertificate(cert_path, key_path)
		
		return RequestPost(url, request, tlsconf)

	def DownloadFile(
		self,
		url: str,
		ssl_cert: OptStr = None,
		ssl_key: OptStr = None
	) -> Dict:
		""" SAS-SAS Get data from json files after generate the Full Activity Dump Message
		Returns:
			the message as a "json data" object specified in WINNF-16-S-0096
		"""
		cert_path = ssl_cert or GetDefaultSasSSLCertPath()
		key_path = ssl_key or GetDefaultSasSSLKeyPath()
		tlsconf = self._tls_config.WithClientCertificate(cert_path, key_path)
		
		return RequestGet(url, tlsconf)
	
	def UpdateSasRequestUrl(self, cipher) -> None:
		if 'ECDSA' in cipher:
			self.sas_sas_active_base_url = self._sas_sas_ec_base_url
		else:
			self.sas_sas_active_base_url = self._sas_sas_rsa_base_url

	def UpdateCbsdRequestUrl(self, cipher) -> None:
		if 'ECDSA' in cipher:
			self.cbsd_sas_active_base_url = self._cbsd_sas_ec_base_url
		else:
			self.cbsd_sas_active_base_url = self._cbsd_sas_rsa_base_url


class SasAdminImpl(sas_interface.SasAdminInterface):
	"""Implementation of SasAdminInterface for SAS certification testing."""

	def __init__(self, base_url: str):
		self._base_url = base_url
		self._tls_config = TlsConfig().WithClientCertificate(
			self._GetDefaultAdminSSLCertPath(),
			self._GetDefaultAdminSSLKeyPath()
		)
		self.injected_fcc_ids = set()
		self.injected_user_ids = set()

	def Reset(self) -> None:
		"""SAS admin interface implementation to reset the SAS between test cases."""
		RequestPost(f'https://{self._base_url}/admin/reset', None, self._tls_config)

	def InjectFccId(self, request: Dict) -> None:
		"""SAS admin interface implementation to inject fcc id information into SAS under test.

		Args:
			request: A dictionary with the following key-value pairs:
				"fccId": (string) valid fccId to be injected into SAS under test
				"fccMaxEirp": (double) optional; default value of 47 dBm/10 MHz
		"""
		# Avoid injecting the same FCC ID twice in the same test case.
		if request['fccId'] in self.injected_fcc_ids:
			return
		if 'fccMaxEirp' not in request:
			request['fccMaxEirp'] = 47
		
		url = f'https://{self._base_url}/admin/injectdata/fcc_id'
		RequestPost(url, request, self._tls_config)
		
		self.injected_fcc_ids.add(request['fccId'])

	def InjectUserId(self, request: Dict) -> None:
		"""SAS admin interface implementation to whitelist a user ID in the SAS under test.

		Args:
			request: A dictionary with a single key-value pair where the key is
				"userId" and the value is a string of valid userId to be whitelisted by
				the SAS under test.
		"""
		# Avoid injecting the same user ID twice in the same test case.
		if request['userId'] in self.injected_user_ids:
			return
		
		url = f'https://{self._base_url}/admin/injectdata/user_id'
		RequestPost(url, request, self._tls_config)
		
		self.injected_user_ids.add(request['userId'])

	def InjectEscZone(self, request: Dict) -> Dict:
		url = f'https://{self._base_url}/admin/injectdata/esc_zone'
		return RequestPost(url, request, self._tls_config)

	def InjectExclusionZone(self, request: Dict) -> Dict:
		"""Inject exclusion zone information into SAS under test.

		Args:
			request: A dictionary with the following key-value pairs:
				"zone": A GeoJSON object defining the exclusion zone to be injected to SAS UUT.
				"frequencyRanges": A list of frequency ranges for the exclusion zone.
		"""
		url = f'https://{self._base_url}/admin/injectdata/exclusion_zone'
		return RequestPost(url, request, self._tls_config)

	def InjectZoneData(self, request: Dict) -> Dict:
		"""Inject PPA or NTIA zone information into SAS under test.

		Args:
			request: A dictionary with a single key-value pair where the key is
				"record" and the value is ZoneData object to be injected into
				SAS under test. For more information about ZoneData please see
				the SAS-SAS TS (WINNF-16-S-0096) - Section 8.7.
		"""
		url = f'https://{self._base_url}/admin/injectdata/zone'
		return RequestPost(url, request, self._tls_config)

	def InjectPalDatabaseRecord(self, request: Dict) -> None:
		"""Inject a PAL Database record into the SAS under test.

		Args:
			request:
			For the contents of this request, please refer to the PAL Database TS
			(WINNF-16-S-0245) - Section 6.x.
		"""
		url = f'https://{self._base_url}/admin/injectdata/pal_database_record'
		RequestPost(url, request, self._tls_config)

	def InjectClusterList(self, request: Dict) -> None:
		url = f'https://{self._base_url}/admin/injectdata/cluster_list'
		RequestPost(url, request, self._tls_config)

	def BlacklistByFccId(self, request: Dict) -> None:
		"""Inject an FCC ID which will be blacklisted by the SAS under test.

		Args:
			request: A dictionary with a single key-value pair where the key is
				"fccId" and the value is the FCC ID (string) to be blacklisted.
		"""
		url = f'https://{self._base_url}/admin/injectdata/blacklist_fcc_id'
		RequestPost(url, request, self._tls_config)

	def BlacklistByFccIdAndSerialNumber(self, request: Dict) -> None:
		"""Inject an (FCC ID, serial number) pair which will be blacklisted by the SAS under test.
		
		Args:
			request: A dictionary with the following key-value pairs:
				"fccId": (string) blacklisted FCC ID
				"serialNumber": (string) blacklisted serial number
		"""
		url = f'https://{self._base_url}/admin/injectdata/blacklist_fcc_id_and_serial_number'
		RequestPost(url, request, self._tls_config)

	def TriggerEscZone(self, request: Dict) -> None:
		url = f'https://{self._base_url}/admin/trigger/esc_detection'
		RequestPost(url, request, self._tls_config)

	def ResetEscZone(self, request: Dict) -> None:
		url = f'https://{self._base_url}/admin/trigger/esc_reset'
		RequestPost(url, request, self._tls_config)

	def PreloadRegistrationData(self, request: Dict) -> None:
		"""SAS admin interface implementation to preload registration data into SAS under test.

		Args:
			request: A dictionary with a single key-value pair where the key is
				"registrationData" and the value is a list of individual CBSD
				registration data which need to be preloaded into SAS (each of which is
				itself a dictionary). The dictionary is a RegistrationRequest object,
				the fccId and cbsdSerialNumber fields are required, other fields are
				optional.
		"""
		url = f'https://{self._base_url}/admin/injectdata/conditional_registration'
		RequestPost(url, request, self._tls_config)

	def InjectFss(self, request: Dict) -> None:
		"""SAS admin interface implementation to inject FSS information into SAS under test.

		Args:
			request: A dictionary with a single key-value pair where the key is
			"record" and the value is a fixed satellite service object
			(which is itself a dictionary). The dictionary is an
			IncumbentProtectionData object (specified in SAS-SAS TS) -- WINNF-16-S-0096: Section 8.5.
		"""
		url = f'https://{self._base_url}/admin/injectdata/fss'
		RequestPost(url, request, self._tls_config)

	def InjectWisp(self, request: Dict) -> None:
		"""SAS admin interface implementation to inject WISP information into SAS under test.

		Args:
			request: A dictionary with two key-value pairs where the keys are "record" and "zone" with the values
					IncumbentProtectionData object (specified in SAS-SAS TS) and a GeoJSON Object respectively
		Note: Required Field in IncumbentProtectionData are id, type,
				deploymentParam->operationParam->operationFrequencyRange->lowFrequency, highFrequency
		"""
		url = f'https://{self._base_url}/admin/injectdata/wisp'
		RequestPost(url, request, self._tls_config)

	def InjectSasAdministratorRecord(self, request: Dict) -> None:
		"""SAS admin interface implementation to inject SAS Administrator Record into SAS under test.

		Args:
			request: A dictionary with a single key-value pair where the key is
				"record" and the value is a SAS Administrator information (which is
				itself a dictionary). The dictionary is an SASAdministrator object
				(Specified in SAS-SAS TS WINNF-16-S-0096) - Section 8.1.
		"""
		url = f'https://{self._base_url}/admin/injectdata/sas_admin' 
		RequestPost(url, request, self._tls_config)

	def TriggerMeasurementReportRegistration(self) -> None:
		"""SAS admin interface implementation to trigger measurement report request for all subsequent
		registration request

		Note: The SAS should request a measurement report in the RegistrationResponse
		(if status == 0)
		"""
		url = f'https://{self._base_url}/admin/trigger/meas_report_in_registration_response'
		RequestPost(url, None, self._tls_config)

	def TriggerMeasurementReportHeartbeat(self) -> None:
		"""SAS admin interface implementation to trigger measurement report request for all subsequent
		heartbeat request

		Note: The SAS should request a measurement report in the HeartbeatResponse
		(if status == 0)
		"""
		url = f'https://{self._base_url}/admin/trigger/meas_report_in_heartbeat_response'
		RequestPost(url, None, self._tls_config)

	def InjectEscSensorDataRecord(self, request: Dict) -> None:
		"""SAS admin interface implementation to inject ESC Sensor Data Record into SAS under test.

		Args:
			request: A dictionary with a single key-value pair where the key is
				"record" and the value is a EscSensorData object (which is
				itself a dictionary specified in SAS-SAS TS WINNF-16-S-0096) - Section 8.6.
		Behavior: SAS should act as if it is connected to an ESC sensor with
		the provided parameters.
		"""
		url = f'https://{self._base_url}/admin/injectdata/esc_sensor'
		RequestPost(url, request, self._tls_config)

	def TriggerPpaCreation(self, request: Dict) -> Dict:
		"""SAS admin interface implementation to trigger PPA creation based on the CBSD Ids, Pal Ids and Provided Contour

		Args:
			request: A dictionary with multiple key-value pairs where the keys are
				cbsdIds: array of string containing CBSD Id
				palIds: array of string containing PAL Id
				providedContour(optional): GeoJSON Object

		Returns:
			PPA Id in string format
		"""
		url = f'https://{self._base_url}/admin/trigger/create_ppa'
		return RequestPost(url, request, self._tls_config)

	def TriggerDailyActivitiesImmediately(self) -> None:
		"""SAS admin interface implementation to trigger daily activities immediately which will
		execute the following activities:
			1. Pull from all External Database and other SASes (URLs will be injected to
			SAS UUT using another RPC Call)
			2. Run IAP and DPA Calculations
			3. Apply EIRP updates to devices
		"""
		url = f'https://{self._base_url}/admin/trigger/daily_activities_immediately'
		RequestPost(url, None, self._tls_config)

	def TriggerEnableScheduledDailyActivities(self) -> None:
		"""SAS admin interface implementation to trigger the daily activities according to the 
			schedule agreed upon by SAS admins.
		"""
		url = f'https://{self._base_url}/admin/trigger/enable_scheduled_daily_activities'
		RequestPost(url, None, self._tls_config)

	def QueryPropagationAndAntennaModel(self, request: Dict) -> Dict:
		"""SAS admin interface implementation to query propagation and antenna gains for CBSD and FSS	or Provided PPA Contour

		Args:
			request: A dictionary with multiple key-value pairs where the keys are
				reliabilityLevel: (permitted values: -1, 0.05, 0.95)
				cbsd: dictionary defining cbsd
				fss(optional): dictionary defining fss
				ppa(optional): GeoJSON Object

		Returns:
			double pathlossDb (pathloss in dB)
			double txAntennaGainDbi (transmitter antenna gain in dBi in the direction of the receiver)
			double rxAntennaGainDbi (optional) (receiver antenna gain in dBi in the direction of the transmitter)

		"""
		url = f'https://{self._base_url}/admin/query/propagation_and_antenna_model'
		return RequestPost(url, request, self._tls_config)

	def TriggerEnableNtiaExclusionZones(self) -> None:
		"""SAS admin interface implementation to trigger enforcement of the NTIA exclusion zones 
		"""
		url = f'https://{self._base_url}/admin/trigger/enable_ntia_15_517'
		RequestPost(url, None, self._tls_config)

	def GetDailyActivitiesStatus(self) -> Dict:
		"""SAS admin interface implementation to get the daily activities' status
		Returns:
			A dictionary with a single key-value pair where the key is "completed" and the
			value is a boolean with value as true if the daily activities is completed and
			false if the daily activities is running/failing.
		"""
		url = f'https://{self._base_url}/admin/get_daily_activities_status'
		return RequestPost(url, None, self._tls_config)

	def InjectCpiUser(self, request: Dict) -> None:
		"""SAS admin interface implementation to add a CPI User as if it came directly from the CPI database.

		Args:
			request: A dictionary with the following key-value pairs:
				"cpiId": (string) valid cpiId to be injected into SAS under test
				"cpiName": (string) valid name for cpi user to be injected into SAS under test
				"cpiPublicKey": (string) public key value for cpi user to be injected into SAS under test
		"""
		url = f'https://{self._base_url}/admin/injectdata/cpi_user'
		RequestPost(url, request, self._tls_config)

	def TriggerLoadDpas(self) -> None:
		"""SAS admin interface implementation to load all ESC-monitored DPAs and immediately activate all of them.
		"""
		url = f'https://{self._base_url}/admin/trigger/load_dpas'
		RequestPost(url, None, self._tls_config)

	def TriggerBulkDpaActivation(self, request: Dict) -> None:
		"""SAS admin interface implementation to bulk DPA activation/deactivation
		Args:
			request: A dictionary with the following key-value pairs:
				"activate": (boolean) if True, activate all ESC-monitored DPAs on all channels
						else deactivate all ESC-monitored DPAs on all channels
		"""
		url = f'https://{self._base_url}/admin/trigger/bulk_dpa_activation'
		RequestPost(url, request, self._tls_config)

	def TriggerDpaActivation(self, request: Dict) -> None:
		"""SAS admin interface implementation to activate specific DPA on specific channel
		Args:
			request: A dictionary with the following key-value pairs:
				"dpaId": (string) it represents the field "name" in the kml file of DPAs
				"frequencyRange": frequencyRange of DPA Channel with lowFrequency, highFrequency

		"""
		url = f'https://{self._base_url}/admin/trigger/dpa_activation'
		RequestPost(url, request, self._tls_config)

	def TriggerDpaDeactivation(self, request: Dict) -> None:
		"""SAS admin interface implementation to deactivate specific DPA on specific channel
		Args:
			request: A dictionary with the following key-value pairs:
				"dpaId": (string) it represents the field "name" in the kml file of DPAs
				"frequencyRange": frequencyRange of DPA Channel with lowFrequency, highFrequency
		"""
		url = f'https://{self._base_url}/admin/trigger/dpa_deactivation'
		RequestPost(url, request, self._tls_config)

	def TriggerEscDisconnect(self) -> None:
		"""Simulates the ESC (ESC-DE) being disconnected from the SAS UUT."""
		url = f'https://{self._base_url}/admin/trigger/disconnect_esc'
		RequestPost(url, None, self._tls_config)

	def TriggerFullActivityDump(self) -> None:
		"""SAS admin interface implementation to trigger generation of a Full Activity Dump.

		Note: SAS does not need to complete generation before returning HTTP 200.
		See the testing API specification for more details.
		"""
		url = f'https://{self._base_url}/admin/trigger/create_full_activity_dump'
		RequestPost(url, None, self._tls_config)

	def _GetDefaultAdminSSLCertPath(self) -> str:
		return os.path.join('certs', 'admin.cert')

	def _GetDefaultAdminSSLKeyPath(self) -> str:
		return os.path.join('certs', 'admin.key')

	def InjectPeerSas(self, request: Dict) -> None:
		"""SAS admin interface implementation to inject a peer SAS into the SAS UUT.

		Args:
			request: A dictionary with the following key-value pairs:
				"certificateHash": the sha1 fingerprint of the certificate
				"url": base URL of the peer SAS.
		"""
		url = f'https://{self._base_url}/admin/injectdata/peer_sas'
		RequestPost(url, request, self._tls_config)

	def GetPpaCreationStatus(self) -> Dict:
		"""SAS admin interface implementation to get the most recent PPA creation status
		Returns:
			A dictionary with a two key-value pairs where the keys are "completed" and
			"withError". The values are of boolean type. The value for "completed" flag
			set to True if the ppa creation(for the most recent ppa creation) has completed or
			to False if the PPA creation is still in progress. The value for "withError" flag is
			set to True if the PPA creation has completed with error(s) else it is set to False.
		"""
		url = f'https://{self._base_url}/admin/get_ppa_status'
		return RequestPost(url, None, self._tls_config)

	def InjectDatabaseUrl(self, request: Dict) -> None:
		"""Inject the Database URL into SAS.

		Args:
			request: Contains database url to be injected.
		"""
		url = f'https://{self._base_url}/admin/injectdata/database_url'
		RequestPost(url, request, self._tls_config)
