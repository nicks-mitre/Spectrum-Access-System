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
		return self._CbsdRequest('registration', request, ssl_cert, ssl_key)

	def SpectrumInquiry(
		self,
		request: Dict,
		ssl_cert: OptStr = None,
		ssl_key: OptStr = None
	) -> Dict:
		return self._CbsdRequest('spectrumInquiry', request, ssl_cert, ssl_key)

	def Grant(
		self,
		request: Dict,
		ssl_cert: OptStr = None,
		ssl_key: OptStr = None
	) -> Dict:
		return self._CbsdRequest('grant', request, ssl_cert, ssl_key)

	def Heartbeat(
		self,
		request: Dict,
		ssl_cert: OptStr = None,
		ssl_key: OptStr = None
	) -> Dict:
		return self._CbsdRequest('heartbeat', request, ssl_cert, ssl_key)

	def Relinquishment(
		self,
		request: Dict,
		ssl_cert: OptStr = None,
		ssl_key: OptStr = None
	) -> Dict:
		return self._CbsdRequest('relinquishment', request, ssl_cert, ssl_key)

	def Deregistration(
		self,
		request: Dict,
		ssl_cert: OptStr = None,
		ssl_key: OptStr = None
	) -> Dict:
		return self._CbsdRequest('deregistration', request, ssl_cert, ssl_key)

	def GetEscSensorRecord(
		self,
		request: Dict,
		ssl_cert: OptStr = None,
		ssl_key: OptStr = None
	) -> Dict:
		return self._SasRequest('esc_sensor', request, ssl_cert, ssl_key)

	def GetFullActivityDump(
		self,
		ssl_cert: OptStr = None,
		ssl_key: OptStr = None
	) -> Dict:
		return self._SasRequest('dump', None, ssl_cert, ssl_key)

	def _SasRequest(
		self,
		method_name: str,
		request: Dict,
		ssl_cert: OptStr = None,
		ssl_key: OptStr = None
	) -> Dict: # Functions using _Request() return a dict repr. a JSON response
		# url = 'https://%s/%s/%s' % (self.sas_sas_active_base_url, self.sas_sas_version, method_name)
		url = f'https://{self.sas_sas_active_base_url}/{self.sas_sas_version}/{method_name}'
		
		if request is not None:
			# url += '/%s' % request
			url = str.join(url, f'/{request}')
		
		cert_path = ssl_cert or GetDefaultSasSSLCertPath() # if ssl_cert is None, then use default
		key_path = ssl_key or GetDefaultSasSSLKeyPath()
		tlsconf = self._tls_config.WithClientCertificate(cert_path, key_path))
		
		return RequestGet(url, tlsconf)

	def _CbsdRequest(
		self,
		method_name: str,
		request: Dict,
		ssl_cert: OptStr = None,
		ssl_key: OptStr = None
	) -> Dict:
		# url = 'https://%s/%s/%s' % (self.cbsd_sas_active_base_url, self.cbsd_sas_version, method_name)
		url = f'https://{self.cbsd_sas_active_base_url}/{self.cbsd_sas_version}/{method_name}'
		
		cert_path = ssl_cert or GetDefaultDomainProxySSLCertPath()
		key_path = ssl_key or GetDefaultDomainProxySSLKeyPath()
		
		return RequestPost(
			url, 
			request, 
			self._tls_config.WithClientCertificate(cert_path, key_path)
		)

	def DownloadFile(
		self,
		url: str,
		ssl_cert: OptStr = None,
		ssl_key: OptStr = None
	) -> Dict:
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
				self._GetDefaultAdminSSLCertPath(), self._GetDefaultAdminSSLKeyPath())
		self.injected_fcc_ids = set()
		self.injected_user_ids = set()

	def Reset(self) -> None:
		RequestPost('https://%s/admin/reset' % self._base_url, None, self._tls_config)

	def InjectFccId(self, request: Dict) -> None:
		# Avoid injecting the same FCC ID twice in the same test case.
		if request['fccId'] in self.injected_fcc_ids:
			 return
		if 'fccMaxEirp' not in request:
			request['fccMaxEirp'] = 47
		RequestPost('https://%s/admin/injectdata/fcc_id' % self._base_url, request,
				self._tls_config)
		self.injected_fcc_ids.add(request['fccId'])

	def InjectUserId(self, request: Dict) -> Dict:
		# Avoid injecting the same user ID twice in the same test case.
		if request['userId'] in self.injected_user_ids:
			return
		RequestPost('https://%s/admin/injectdata/user_id' % self._base_url, request,
				self._tls_config)
		self.injected_user_ids.add(request['userId'])

	def InjectEscZone(self, request: Dict) -> Dict:
		return RequestPost('https://%s/admin/injectdata/esc_zone' % self._base_url,
				request, self._tls_config)

	def InjectExclusionZone(self, request: Dict) -> Dict:
		return RequestPost(
				'https://%s/admin/injectdata/exclusion_zone' % self._base_url, request,
				self._tls_config)

	def InjectZoneData(self, request: Dict) -> Dict:
		return RequestPost('https://%s/admin/injectdata/zone' % self._base_url,
				request, self._tls_config)

	def InjectPalDatabaseRecord(self, request: Dict) -> None:
		RequestPost(
				'https://%s/admin/injectdata/pal_database_record' % self._base_url,
				request, self._tls_config)

	def InjectClusterList(self, request: Dict) -> None:
		RequestPost('https://%s/admin/injectdata/cluster_list' % self._base_url,
				request, self._tls_config)

	def BlacklistByFccId(self, request: Dict) -> None:
		RequestPost('https://%s/admin/injectdata/blacklist_fcc_id' % self._base_url,
				request, self._tls_config)

	def BlacklistByFccIdAndSerialNumber(self, request: Dict) -> None:
		RequestPost('https://%s/admin/injectdata/blacklist_fcc_id_and_serial_number'
				% self._base_url, request, self._tls_config)

	def TriggerEscZone(self, request: Dict) -> None:
		RequestPost('https://%s/admin/trigger/esc_detection' % self._base_url,
				request, self._tls_config)

	def ResetEscZone(self, request: Dict) -> None:
		RequestPost('https://%s/admin/trigger/esc_reset' % self._base_url, request,
				self._tls_config)

	def PreloadRegistrationData(self, request: Dict) -> None:
		RequestPost(
				'https://%s/admin/injectdata/conditional_registration' % self._base_url,
				request, self._tls_config)

	def InjectFss(self, request: Dict) -> None:
		RequestPost('https://%s/admin/injectdata/fss' % self._base_url, request,
				self._tls_config)

	def InjectWisp(self, request: Dict) -> None:
		RequestPost('https://%s/admin/injectdata/wisp' % self._base_url, request,
				self._tls_config)

	def InjectSasAdministratorRecord(self, request: Dict) -> None:
		RequestPost('https://%s/admin/injectdata/sas_admin' % self._base_url,
				request, self._tls_config)

	def TriggerMeasurementReportRegistration(self) -> None:
		RequestPost('https://%s/admin/trigger/meas_report_in_registration_response'
				% self._base_url, None, self._tls_config)

	def TriggerMeasurementReportHeartbeat(self) -> None:
		RequestPost('https://%s/admin/trigger/meas_report_in_heartbeat_response' %
				self._base_url, None, self._tls_config)

	def InjectEscSensorDataRecord(self, request: Dict) -> None:
		RequestPost('https://%s/admin/injectdata/esc_sensor' % self._base_url,
				request, self._tls_config)

	def TriggerPpaCreation(self, request: Dict) -> Dict:
		return RequestPost('https://%s/admin/trigger/create_ppa' % self._base_url,
				request, self._tls_config)

	def TriggerDailyActivitiesImmediately(self) -> None:
		RequestPost('https://%s/admin/trigger/daily_activities_immediately' %
				self._base_url, None, self._tls_config)

	def TriggerEnableScheduledDailyActivities(self) -> None:
		RequestPost('https://%s/admin/trigger/enable_scheduled_daily_activities' %
				self._base_url, None, self._tls_config)

	def QueryPropagationAndAntennaModel(self, request: Dict) -> Dict:
		return RequestPost('https://%s/admin/query/propagation_and_antenna_model' %
				self._base_url, request, self._tls_config)

	def TriggerEnableNtiaExclusionZones(self) -> None:
		RequestPost('https://%s/admin/trigger/enable_ntia_15_517' %
				self._base_url, None, self._tls_config)

	def GetDailyActivitiesStatus(self) -> Dict:
		return RequestPost(
				'https://%s/admin/get_daily_activities_status' % self._base_url, None,
				self._tls_config)

	def InjectCpiUser(self, request: Dict) -> None:
		RequestPost('https://%s/admin/injectdata/cpi_user' % self._base_url,
				request, self._tls_config)

	def TriggerLoadDpas(self) -> None:
		RequestPost('https://%s/admin/trigger/load_dpas' % self._base_url, None,
				self._tls_config)

	def TriggerBulkDpaActivation(self, request: Dict) -> None:
		RequestPost('https://%s/admin/trigger/bulk_dpa_activation' % self._base_url,
				request, self._tls_config)

	def TriggerDpaActivation(self, request: Dict) -> None:
		RequestPost('https://%s/admin/trigger/dpa_activation' % self._base_url,
				request, self._tls_config)

	def TriggerDpaDeactivation(self, request: Dict) -> None:
		RequestPost('https://%s/admin/trigger/dpa_deactivation' % self._base_url,
				request, self._tls_config)

	def TriggerEscDisconnect(self) -> None:
		RequestPost('https://%s/admin/trigger/disconnect_esc' % self._base_url,
				None, self._tls_config)

	def TriggerFullActivityDump(self) -> None:
		RequestPost(
				'https://%s/admin/trigger/create_full_activity_dump' % self._base_url,
				None, self._tls_config)

	def _GetDefaultAdminSSLCertPath(self) -> str:
		return os.path.join('certs', 'admin.cert')

	def _GetDefaultAdminSSLKeyPath(self) -> str:
		return os.path.join('certs', 'admin.key')

	def InjectPeerSas(self, request: Dict) -> None:
		RequestPost('https://%s/admin/injectdata/peer_sas' % self._base_url,
				request, self._tls_config)

	def GetPpaCreationStatus(self) -> Dict:
		return RequestPost(
				'https://%s/admin/get_ppa_status' % self._base_url, None,
				self._tls_config)

	def InjectDatabaseUrl(self, request: Dict) -> None:
		RequestPost('https://%s/admin/injectdata/database_url' % self._base_url,
				request, self._tls_config)
