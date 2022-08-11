#    Copyright 2018 SAS Project Authors. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
"""Handles HTTP requests."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import copy
import json
import logging
import os
import time

import pycurl
import six
from six.moves import range
import six.moves.urllib.parse as urlparse

MAX_REQUEST_ATTEMPT_COUNT = 1
REQUEST_ATTEMPT_DELAY_SECOND = 0.25

class HTTPError(Exception):
  """HTTP error, ie. any HTTP code not in range [200, 299].

  Attributes:
    error_code: integer code representing the HTTP error code. Refer to:
        https://en.wikipedia.org/wiki/List_of_HTTP_status_codes
  """

  def __init__(self, error_code):
    Exception.__init__(self, 'HTTP code %d' % error_code)
    self.error_code = error_code


class CurlError(Exception):
  """Curl error, as defined in https://curl.haxx.se/libcurl/c/libcurl-errors.html.

  Attributes:
    error_code: integer code representing the pycurl error code. Refer to:
        https://curl.haxx.se/libcurl/c/libcurl-errors.html
  """

  def __init__(self, message, error_code):
    Exception.__init__(self, message)
    self.error_code = error_code


class TlsConfig(object):
  """Holds all TLS/HTTPS parameters."""

  def __init__(self):
    # self.ssl_version = pycurl.Curl().SSLVERSION_TLSv1_2
    self.ssl_version = pycurl.SSLVERSION_TLSv1_2
    # self.ssl_version = pycurl.Curl().SSLVERSION_TLSv1_3
    self.ciphers = [
        'AES128-GCM-SHA256',  # TLS_RSA_WITH_AES_128_GCM_SHA256
        'AES256-GCM-SHA384',  # TLS_RSA_WITH_AES_256_GCM_SHA384
        'ECDHE-ECDSA-AES128-GCM-SHA256',  # TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256
        'ECDHE-ECDSA-AES256-GCM-SHA384',  # TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384
        'ECDHE-RSA-AES128-GCM-SHA256',  # TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
    ]
    self.ca_cert = os.path.join('certs', 'ca.cert')
    self.client_cert = None
    self.client_key = None

  def WithClientCertificate(self, client_cert, client_key):
    """Returns a copy of the current config with the given certificate and key.

    Required for security tests.
    """
    ret = copy.copy(self)
    ret.client_key = client_key
    ret.client_cert = client_cert
    return ret


def RequestPost(url, request, config):
  return _Request(url, request, config, True)


def RequestGet(url, config):
  return _Request(url, None, config, False)


def _Request(url, request, config, is_post_method):
  """Sends HTTPS request.

  Args:
    url: Destination of the HTTPS request.
    request: Content of the request. (Can be None)
    config: a |TlsConfig| object defining the TLS/HTTPS configuration.
    is_post_method (bool): If True, use POST, else GET.
  Returns:
    A dictionary represents the JSON response received from server.
  Raises:
    CurlError: with args[0] is an integer code representing the libcurl
      SSL code response (value < 100). Refer to:
      https://curl.haxx.se/libcurl/c/libcurl-errors.html
    HTTPError: for any HTTP code not in the range [200, 299]. Refer to:
      https://en.wikipedia.org/wiki/List_of_HTTP_status_codes)
  """
  # manage case of request passed as byte
  try:
    logging.info("request is bytes object. Decoding...")
    request = request.decode('utf-8')
  except (UnicodeDecodeError, AttributeError):
    pass

  response = six.BytesIO()
  conn = pycurl.Curl()
  conn.setopt(pycurl.URL, url)
  conn.setopt(pycurl.WRITEFUNCTION, response.write)
  conn.setopt(pycurl.VERBOSE, True)
  conn.setopt(pycurl.SSL_ENABLE_ALPN, True)
  header = [
      'Host: %s' % urlparse.urlparse(url).hostname,
      # 'Host: %s' % urlparse.urlparse(url).netloc,
      'content-type: application/json'
  ]
  # conn.setopt(
  #     conn.VERBOSE,
  #     3  # Improve readability.
  #     if logging.getLogger().isEnabledFor(logging.DEBUG) else False)
  conn.setopt(pycurl.SSLVERSION, config.ssl_version)
  conn.setopt(pycurl.SSLCERTTYPE, 'PEM')
  conn.setopt(pycurl.SSLCERT, config.client_cert)
  conn.setopt(pycurl.SSLKEY, config.client_key)
  conn.setopt(pycurl.CAINFO, config.ca_cert)
  conn.setopt(pycurl.HTTPHEADER, header)
  conn.setopt(pycurl.SSL_CIPHER_LIST, ':'.join(config.ciphers))
  conn.setopt(pycurl.TCP_KEEPALIVE, 1)
  conn.setopt(pycurl.OPT_CERTINFO, 1)
  request = json.dumps(request) if request else ''
  if is_post_method:
    conn.setopt(pycurl.POST, True)
    conn.setopt(pycurl.POSTFIELDS, request)
    logging.debug('POST Request to URL %s :\n%s', url, request)
  else:
    logging.debug('GET Request to URL %s', url)

  for attempt_count in range(MAX_REQUEST_ATTEMPT_COUNT):
    try:
      conn.perform()
      error = None
      break
    except pycurl.error as e:
      # e contains a tuple (libcurl_error_code, string_description).
      # See https://curl.haxx.se/libcurl/c/libcurl-errors.html
      error = e
      logging.warning(str(CurlError(e.args[1], e.args[0])))
      time.sleep(REQUEST_ATTEMPT_DELAY_SECOND)
    except Exception as e:
      error = e
      logging.warning(str(e))
      time.sleep(REQUEST_ATTEMPT_DELAY_SECOND)

  if error:
    logging.error('Connection to Host Failed after %d attempts' %MAX_REQUEST_ATTEMPT_COUNT)
    raise error

  http_code = conn.getinfo(pycurl.HTTP_CODE)
  conn.close()
  body = response.getvalue().decode('utf-8')
  logging.debug('Response:\n' + body)

  if not (200 <= http_code <= 299):
    raise HTTPError(http_code)
  if body:
    return json.loads(body)
