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

import inspect

import copy
import json
import logging
import os
import time
import datetime as dt
import re

import pycurl
import six
from six.moves import range
import six.moves.urllib.parse as urlparse

from typing import List

MAX_REQUEST_ATTEMPT_COUNT = 1
REQUEST_ATTEMPT_DELAY_SECOND = 0.25

# call the required libcurl global_init() function with SSL and WinSock support
pycurl.global_init(pycurl.GLOBAL_ALL)

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

def called_me(stack_lvl: int = 1, all_callers: bool = False, with_stk: bool = False):
  """
  return the filename and function name of the caller of this function,
  or if stack_lvl > 1, then the nth caller of this function (e.g. if stack_lvl == 2,
  then it returns the filename and function name of the caller that called the caller of this function.
  """
  if all_callers:
    caller_frame = inspect.stack()
    ret_str = "\n".join([f"{i.filename}:{i.function}" for i in caller_frame])
  else:
    caller_frame = inspect.stack()[stack_lvl]
    ret_str = f"{caller_frame.filename}:{caller_frame.function}"
  # print(ret_str)
  if with_stk:
    return ret_str, caller_frame
  return ret_str


def find_frameinfo_w_var_from_stk(
  stk: List[inspect.FrameInfo],
  local_var_name: str = 'test',
  include_index: bool = False
):
  """
  Given a list of FrameInfo objects (such as returned by inspect.stack(),
  returns the FrameInfo object corresponding to the first one that contains the given string
  ('testMethod' by default) in its locals dictionary's keys (FrameInfo.frame.f_locals.keys()).
  In other words, this function returns the first stack frame (starting from the top of the stack,
  which is indexed at 0) that contains a local variable with the given name.
  """
  if not all([isinstance(i, inspect.FrameInfo) for i in stk]):
    raise TypeError(f"stk must be a list of FrameInfo objects, e.g. as returned by inspect.stack()")
  for index, frameinfo in list(enumerate(stk)):
    if local_var_name in frameinfo.frame.f_locals.keys():
      # return the first FrameInfo object that has a local variable named <local_var_name>
      if include_index:
        return frameinfo, index
      else:
        return frameinfo

def get_calling_testmethod_name(
  stk,
  searchFor: str = 'testMethod',
  include_frame_num: bool = False
):
  """
  Returns the name of the test method that called a function, that in turn, produced a list of stack frames,
  (e.g., via inspect.stack() or called_me(all_callers=True))
  """
  frameinfo, frame_num = find_frameinfo_w_var_from_stk(stk, searchFor, True)
  frame_locals = frameinfo.frame.f_locals
  t_method = frame_locals[searchFor]
  # if the test method happens to be a decorated/wrapped function, then get its real name
  # the inner getattr call returns t_method if t_method.__wrapped__ is not found
  name = getattr(getattr(t_method, '__wrapped__', t_method), '__name__')
  if name == "decorated_testcase":
    # redefine name in case the testmethod was decorated without using functools.wraps
    # (as is the case for testcases decorated with "winnforum_testcase")
    name = getattr(getattr(t_method, '__self__'), '_testMethodName')
  return name, frame_num if include_frame_num else name

# sorry, I know that using/modifying global vars is gross
calls = {}
all_calls = []
stacks = []
def debug_cb(
  p1, p2, *,
  file_name: str = 'debug_cb_output.txt',
  file_open_mode: str ='a',
  emit_other_fds: bool = False,
  nth_caller_to_log: int = 5
):
  """
  A callback function that is set on a Curl object using:
  self.setopt(pycurl.DEBUGFUNCTION, debug_cb)
  Write everything libcurl receives and sends to the given file,
  with the UTC ISO-formatted timestamp prepended to the line

  So far, all dbg/info messages from libcurl have had p1 as 0, and all bytestrings (e.g. the binary data of certs)
  have had p1 > 2, so I'm assuming that p1 is a file/socket descriptor passed by libcurl
  Therefore, if emit_other_fds is False, we return None when we this function is called with
  p1 set as anything but 0, 1, or 2.

  This function is called by _Request(), which is called by RequestPost() or RequestGet(),
  both of which is called by some function/method in sas.py, which is called by a function in
  either a testcase or directly using a SasImpl or SasAdmin object. Therefore, if we want to log
  the filename, line number, and name of the testmethod or other callable that caused the execution
  of this callback, we need to use the called_me() with an argument of 5, to get the fifth-level caller.
  The nth_caller_to_log parameter controls which caller to log, and its default is set to 5 for the reason
  above.
  """
  global calls
  global all_calls
  global stacks
  caller = called_me(nth_caller_to_log)
  all_callers, stk = called_me(all_callers=True, with_stk=True)
  all_callers = all_callers.split('\n')
  # trim off the leading file path, leaving 'testcases/' alone
  caller_regex = re.compile(r'.*Spectrum-Access-System/src/harness/')
  trimmed_caller = caller_regex.sub('', caller)
  all_callers = [caller_regex.sub('', i) for i in all_callers]

  if trimmed_caller in calls.keys():
    calls[trimmed_caller] += 1
  else:
    calls[trimmed_caller] = 1
    all_calls.extend(all_callers)
    stacks.append(stk)

  filename_regx = re.compile(r'.*\.py:')
  tstamp = dt.datetime.utcnow().isoformat()
  tmethod_name, frame_num = get_calling_testmethod_name(stk, include_frame_num=True)

  # nth_caller = filename_regx.sub('', all_callers[nth_caller_to_log])
  # nmin1_caller = filename_regx.sub('', all_callers[nth_caller_to_log - 1])

  def get_nth_caller_name(n):
    return filename_regx.sub('', all_callers[n])

  nth_caller = get_nth_caller_name(nth_caller_to_log)
  nmin1_caller = get_nth_caller_name(nth_caller_to_log-1)

  base_out = f"{tstamp}: {tmethod_name}:"
  # get the call tree and concatenate the entries together with a colon separating callers
  middle = ':'.join([get_nth_caller_name(n) for n in range(frame_num-1, 1, -1)])
  # print(''.join([base_out, middle, end_out]))

  if emit_other_fds:
    # out = f"{tstamp}: {trimmed_caller}: ({p1}, {p2})\n"
    # out = f"{tstamp}: {tmethod_name}:{all_callers[nth_caller_to_log]}:{filename_regx.sub('', all_callers[nth_caller_to_log-1])}: ({p1}, {p2})\n"
    # out = f"{tstamp}: {tmethod_name}:{nth_caller}:{nmin1_caller}: ({p1}, {p2})\n"
    end_out = f" ({p1}, {p2})\n"
    out = ''.join([base_out, middle, end_out])
  # emit_other_fds is False, so check that we care about the message
  elif int(p1) in (0,1,2):
    # out = f"{tstamp}: {trimmed_caller}: {p2}\n"
    # out = f"{tstamp}: {tmethod_name}:{all_callers[nth_caller_to_log]}:{filename_regx.sub('', all_callers[nth_caller_to_log - 1])}: {p2}\n"
    # out = f"{tstamp}: {tmethod_name}:{nth_caller}:{nmin1_caller}: {p2}\n"
    end_out = f" {p2}\n"
    out = ''.join([base_out, middle, end_out])
  else:
    # Returning None implies that all bytes were written
     return

  with open(file_name, file_open_mode) as fp:
    fp.write(out)


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
    request = request.decode('utf-8')
    logging.info("request is bytes object. Decoding...")
  except (UnicodeDecodeError, AttributeError):
    pass

  response = six.BytesIO()
  conn = pycurl.Curl()
  conn.setopt(pycurl.URL, url)
  conn.setopt(pycurl.WRITEFUNCTION, response.write)
  conn.setopt(pycurl.DEBUGFUNCTION, debug_cb)
  conn.setopt(pycurl.VERBOSE, True)
  header = [
      # 'Host: %s' % urlparse.urlparse(url).hostname,
      'Host: %s' % urlparse.urlparse(url).netloc,
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
    # logging.debug('POST Request to URL %s :\n%s', url, request)
    logging.warning('POST Request to URL %s :\n%s', url, request)
  else:
    # logging.debug('GET Request to URL %s', url)
    logging.warning('GET Request to URL %s', url)

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
