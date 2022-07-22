#		Copyright 2016 SAS Project Authors. All Rights Reserved.
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
"""Specialized implementation of SasTestCase for all SCS/SDS/SSS testcases."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import inspect
import json
import logging
import os
import re
import subprocess
import socket

import six
from six.moves.urllib import parse as urllib
import inspect

from OpenSSL import SSL, crypto

import sas
import sas_testcase
import util
import request_handler

import typing
from typing import Dict, List, Tuple, Any, Optional, Union, NoReturn
# Type alias to annotate that a param is of str type, but also optional
# The "Optional" annotation is only necessary when the default is None
OptStr = Optional[str]
# StrList = List[str]


class CiphersOverload(object):
	"""Overloads the ciphers and client certificate used by the SAS client.
	Upon destruction, restores the original ciphers and certificate.
	"""
	
	# sas: sas.SasImpl ?
	def __init__(self, sas, ciphers: StrList, client_cert: str, client_key:str):
		self.sas = sas
		self.ciphers: StrList = ciphers
		self.client_cert: str = client_cert
		self.client_key: str = client_key
		self.original_ciphers: StrList = None
		self.original_client_cert: str = None
		self.original_client_key: str = None

	def __enter__(self):
		self.original_ciphers: StrList = self.sas._tls_config.ciphers
		self.original_client_cert: str = self.sas._tls_config.client_cert
		self.original_client_key: str = self.sas._tls_config.client_key
		self.sas._tls_config.ciphers: StrList = self.ciphers
		self.sas._tls_config.client_cert: str = self.client_cert
		self.sas._tls_config.client_key: str = self.client_key
	
	def __exit__(self, type, value, traceback):
		self.sas._tls_config.ciphers: StrList = self.original_ciphers
		self.sas._tls_config.client_cert: str = self.original_client_cert
		self.sas._tls_config.client_key: str = self.original_client_key


class SecurityTestCase(sas_testcase.SasTestCase):

	def setUp(self) -> None:
		"""
		Set up the testing instances of sas and sas_admin
		
		# Note that we disable the admin.Reset(), to avoid 'unexpected' request
		# to SAS UUT before a test really starts.
		# Tests changing the SAS UUT state must explicitly call the SasReset()
		"""
		self._sas, self._sas_admin = sas.GetTestingSas()

	def SasReset(self) -> None:
		"""Resets the SAS UUT to its initial state."""
		self._sas_admin.Reset()

	def doTlsHandshake(
		self,
		base_url: str,
		client_cert: str,
		client_key: str,
		ciphers: StrList,
		ssl_method: int # OpenSSL uses module-level int consts for related vals, instead of enums...
	) -> bool:
		"""Reports the success or failure of a TLS handshake.

		Args:
			base_url: Target host (defaults to port 443) or host:port.
			client_cert: Filename of the client certificate file in PEM format.
			client_key: Filename of the PEM-formatted key to use with |client_cert|.
			ciphers: List of cipher method strings.
			ssl_method: OpenSSL.SSL.*_METHOD value to use.

		Returns:
			True if the handshake succeeded, or False if it failed.
		"""
		url = urllib.urlparse('https://' + base_url)
		client = socket.create_connection((url.hostname, url.port or 443))

		logging.debug("OPENSSL version: %s" % SSL.SSLeay_version(SSL.SSLEAY_VERSION))
		logging.debug('TLS handshake: connecting to: %s:%d', url.hostname, url.port or 443)
		logging.debug('TLS handshake: ciphers=%s', ':'.join(ciphers))
		logging.debug('TLS handshake: privatekey_file=%s', client_key)
		logging.debug('TLS handshake: certificate_file=%s', client_cert)
		logging.debug('TLS handshake: certificate_chain_file=%s', self._sas._tls_config.ca_cert)
		
		ctx = SSL.Context(ssl_method)
		ctx.set_cipher_list(six.ensure_binary(':'.join(ciphers)))
		ctx.use_certificate_file(client_cert)
		if util.get_openssl_version() >= 111:
			with open(client_cert) as f:
				if f.read().count('-----BEGIN ') > 1:
					ctx.use_certificate_chain_file(client_cert)
		ctx.use_privatekey_file(client_key)
		ctx.load_verify_locations(self._sas._tls_config.ca_cert)

		client_ssl_informations = []
		def _InfoCb(conn, where, ok):
			client_ssl_informations.append(six.ensure_text(conn.get_state_string()))
			logging.debug('TLS handshake info: %d|%d %s', where, ok, conn.get_state_string())
			return ok
		ctx.set_info_callback(_InfoCb)

		# only for potential debugging info...
		def _VerifyCb(conn, cert, errnum, depth, ok):
			certsubject = crypto.X509Name(cert.get_subject())
			commonname = certsubject.commonName
			logging.debug('TLS handshake verify: certificate: %s	-> %d', commonname, ok)
			return ok
		ctx.set_verify(SSL.VERIFY_PEER, _VerifyCb)

		client_ssl = SSL.Connection(ctx, client)
		client_ssl.set_connect_state()
		client_ssl.set_tlsext_host_name(six.ensure_binary(url.hostname))

		try:
			client_ssl.do_handshake()
			logging.debug('TLS handshake: succeed')
			handshake_ok = True
		except SSL.Error as e:
			logging.error('TLS handshake: failed:\n%s\n%s', str(e), '\n'.join(client_ssl_informations))
			handshake_ok = False
		finally:
			client_ssl.close()

		# From https://github.com/pyca/pyopenssl/blob/main/src/OpenSSL/SSL.py#L1169:
		# In OpenSSL 1.1.1 setting the cipher list will always return TLS 1.3
		# ciphers even if you pass an invalid cipher. Applications (like
		# Twisted) have tests that depend on an error being raised if an
		# invalid cipher string is passed, but without the following check
		# for the TLS 1.3 specific cipher suites it would never error.
		client_cipher_list = client_ssl.get_cipher_list()
		if util.get_openssl_version() >= 111:
			client_cipher_list.remove('TLS_AES_256_GCM_SHA384')
			client_cipher_list.remove('TLS_CHACHA20_POLY1305_SHA256')
			client_cipher_list.remove('TLS_AES_128_GCM_SHA256')
		self.assertEqual(client_cipher_list, ciphers)

		if handshake_ok:
			known_ssl_methods = {
				SSL.TLSv1_1_METHOD: 'TLSv1.1',
				SSL.TLSv1_2_METHOD: 'TLSv1.2',
			}
			self.assertEqual(client_ssl.get_protocol_version_name(), known_ssl_methods[ssl_method])
			
			# tricky part: exact logged message depends of the version of openssl...
			cipher_check_regex = re.compile(
					r"change.cipher.spec", re.I)
			finished_check_regex = re.compile(
					r"negotiation finished|finish_client_handshake", re.I)
			def findIndexMatching(array, regex):
				for i, x in enumerate(array):
					if regex.search(x):
						return i
				return -1
			cipher_check_idx = findIndexMatching(
					client_ssl_informations, cipher_check_regex)
			finished_check_idx = findIndexMatching(
					client_ssl_informations, finished_check_regex)
			self.assertTrue(cipher_check_idx > 0)
			self.assertTrue(finished_check_idx > 0)
			self.assertTrue(finished_check_idx > cipher_check_idx)

		return handshake_ok

	def assertTlsHandshakeSucceed(
		self,
		base_url: str,
		ciphers: StrList,
		client_cert: str,
		client_key: str
	):
		"""Checks that the TLS handshake succeed with the given parameters.
		
		Attempts to establish a TLS session with the given |base_url|, using the
		given |ciphers| list and the given certificate key pair.
		Checks that he SAS UUT response must satisfy all of the following conditions:
		- The SAS UUT agrees to use a cipher specified in the |ciphers| list
		- The SAS UUT agrees to use TLS Protocol Version 1.2
		- Valid Finished message is returned by the SAS UUT immediately following the ChangeCipherSpec message
		"""
		self.assertTrue(
				self.doTlsHandshake(base_url, client_cert, client_key, ciphers,
						SSL.TLSv1_2_METHOD),
				"Handshake failed unexpectedly")

	def doCbsdTestCipher(
		self,
		cipher: str,
		client_cert: str,
		client_key: str
	):
		"""Does a cipher test as described in SCS/SDS tests 1 to 5 specification.

		Args:
			cipher: the cipher openSSL string name to test.
			client_cert: path to the client certificate file in PEM format to use.
			client_key: path to associated key file in PEM format to use with the
				given |client_cert|.
		"""
		self._sas.UpdateCbsdRequestUrl(cipher)
		# Using pyOpenSSL low level API, does the SAS UUT server TLS session checks.
		self.assertTlsHandshakeSucceed(self._sas.cbsd_sas_active_base_url, [cipher],
				client_cert, client_key)

		# Does a regular CBSD registration
		self.SasReset()
		device_a = util.json_load(os.path.join('testcases', 'testdata', 'device_a.json'))

		with CiphersOverload(self._sas, [cipher], client_cert, client_key):
			self.assertRegistered([device_a])

	def doSasTestCipher(
		self,
		cipher: str,
		client_cert: str,
		client_key: str,
		client_url: str
	):
		"""Does a cipher test as described in SSS tests 1 to 5 specification.

		Args:
			cipher: the cipher openSSL string name to test.
			client_cert: path to (peer) SAS client certificate file in PEM format to use.
			client_key: path to associated key file in PEM format to use.
			client_url: base URL of the (peer) SAS client.
		"""
		self._sas.UpdateSasRequestUrl(cipher)

		# Does a regular SAS registration
		self.SasReset()
		certificate_hash = util.getCertificateFingerprint(client_cert)
		self._sas_admin.InjectPeerSas({'certificateHash': certificate_hash,
				'url': client_url})
		# Using pyOpenSSL low level API, does the SAS UUT server TLS session checks.
		self.assertTlsHandshakeSucceed(self._sas.sas_sas_active_base_url, [cipher],
				client_cert, client_key)
		self._sas_admin.TriggerFullActivityDump()
		with CiphersOverload(self._sas, [cipher], client_cert, client_key):
			self._sas.GetFullActivityDump(client_cert, client_key)

	def assertTlsHandshakeFailure(
		self,
		base_url: str,
		client_cert: str,
		client_key: str,
		cipher: Optional[str] = None,
		ssl_method: Optional[int] = None
	):
		"""
		Checks that the TLS handshake failure by varying the given parameters
		Args:
			base_url: Target host (defaults to port 443) or host:port.
			client_cert: client certificate file in PEM format to use.
			client_key: associated key file in PEM format to use with the
				given |client_cert|.
			cipher: optional cipher method.
			ssl_method: optional ssl_method
		"""
		if cipher is None:
			cipher = [self._sas._tls_config.cipher[0]]
			self.assertEqual(cipher, ['AES128-GCM-SHA256'])
		else:
			cipher = [cipher]

		if ssl_method is None:
			ssl_method = SSL.TLSv1_2_METHOD

		self.assertFalse(
				self.doTlsHandshake(base_url, client_cert, client_key,
						cipher, ssl_method),
				"Handshake succeeded unexpectedly")

	def assertTlsHandshakeFailureOrHttp403(
		self,
		client_cert: str,
		client_key: str,
		cipher: Optional[str] = None,
		ssl_method: Optional[int] = None,
		is_sas: bool = False
	):
		"""
		Checks that the TLS handshake failure by varying the given parameters
		if handshake not failed make sure the next https request return error code 403

		Args:
			client_cert: client certificate file in PEM format to use.
			client_key: associated key file in PEM format to use with the
				given |client_cert|.
			cipher: optional cipher method.
			ssl_method: optional ssl_method
			is_sas: boolean to determine next request
		"""
		try:
			if is_sas:
				# This uses the same base_url as GetFullActivityDump().
				base_url = self._sas.sas_sas_active_base_url
			else:
				# This uses the same base_url as Registration().
				base_url = self._sas.cbsd_sas_active_base_url
			self.assertTlsHandshakeFailure(base_url, client_cert, client_key,
					cipher, ssl_method)
		except AssertionError as e:
			try:
				if is_sas:
					self._sas.GetFullActivityDump(client_cert, client_key)
				else:
					device_a = util.json_load(os.path.join('testcases', 'testdata', 'device_a.json'))
					request = {'registrationRequest': [device_a]}
					self._sas.Registration(request, ssl_cert=client_cert, ssl_key=client_key)
			except request_handler.HTTPError as e:
				logging.debug("TLS session established, expecting HTTP error 403; received %r", e)
				self.assertEqual(e.error_code, 403)
			else:
				self.fail(msg="TLS Handshake and HTTPS request are success. but Expected: failure")

	def createShortLivedCertificate(
		self,
		client_type: str,
		cert_name: str,
		cert_duration_minutes: int
	):
		"""Generates short lived certificate for SCS/SDS 17,18 & 19

		The function uses the root ca, cbsd ca and proxy ca certificates generated by
		"generate_fake_certs.sh" script and creates a short lived client certificate
		based on the input parameters.

		Args:
			client_type: Type of the device (CBSD or DomainProxy).
			cert_name: The name for the short lived certificate and the corresponding private key.
				It is a string value containing just the name without suffix .cert or .key.
			cert_duration_minutes: Duration of the short lived certificate validity in minutes.
		"""

		# Get the harness directory
		harness_dir = os.path.dirname(
				os.path.abspath(inspect.getfile(inspect.currentframe())))

		# Absolute path to the certs directory
		cert_path = os.path.join(harness_dir, 'certs')

		# Build short lived certificate command
		command = "cd {0} && bash ./generate_short_lived_certs.sh {1} {2} {3}".format(cert_path,
				client_type, cert_name, str(cert_duration_minutes))
		# Create the short lived certificate
		command_exit_status = subprocess.call(command, shell=True)

		# Assert the create short lived certificate command status
		self.assertEqual(command_exit_status, 0, "short lived certificate creation failed:"
				"exit_code:%s" %(command_exit_status))
