#    Copyright 2016 SAS Project Authors. All Rights Reserved.
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
import json
import os
import unittest

import sas
from util import winnforum_testcase


class DeregistrationTestcase(unittest.TestCase):

  def setUp(self):
    self._sas, self._sas_admin = sas.GetTestingSas()
    self._sas_admin.Reset()

  def tearDown(self):
    pass

  @winnforum_testcase
  def test_10_15_4_1_1(self):
    """Successful CBSD deregistration request.

    CBSD sends deregistration request to SAS with its correct and valid CBSD
    ID, the response should be SUCCESS.
    """

    # Register the device
    device_a = json.load(
        open(os.path.join('testcases', 'testdata', 'device_a.json')))
    self._sas_admin.InjectFccId({'fccId': device_a['fccId']})
    request = {'registrationRequest': [device_a]}
    response = self._sas.Registration(request)['registrationResponse'][0]
    # Check registration response
    self.assertEqual(response['response']['responseCode'], 0)
    cbsd_id = response['cbsdId']
    del request, response

    # Deregister the device
    request = {'deregistrationRequest': [{'cbsdId': cbsd_id}]}
    response = self._sas.Deregistration(request)['deregistrationResponse'][0]
    # Check the deregistration response
    self.assertEqual(response['cbsdId'], cbsd_id)
    self.assertEqual(response['response']['responseCode'], 0)

  @winnforum_testcase
  def test_WINFF_FT_S_DER_2(self):
    """Valid and correct CBSD ID: two deregistrationRequest objects


    CBSD sends deregistration request to SAS with two deregistrationRequest
    objects that contain correct and valid CBSD ID, the response should be
    SUCCESS.
    """

    # Register the devices
    device_1 = json.load(
        open(os.path.join('testcases', 'testdata', 'device_a.json')))
    device_2 = json.load(
        open(os.path.join('testcases', 'testdata', 'device_a.json')))
    device_1['fccId'] = "test_fcc_id_1"
    device_2['fccId'] = "test_fcc_id_2"
    self._sas_admin.InjectFccId({'fccId': device_1['fccId']})
    self._sas_admin.InjectFccId({'fccId': device_2['fccId']})
    request = {'registrationRequest': [device_1, device_2]}
    response = self._sas.Registration(request)['registrationResponse']
    # Check registration response
    cbsd_id = []
    for x in range (0, 2) :
      self.assertEqual(response[x]['response']['responseCode'], 0)
      cbsd_id.append(response[x]['cbsdId'])
    del request, response

    # Deregister the device
    request = {'deregistrationRequest': [
        {'cbsdId': cbsd_id[0]},
        {'cbsdId': cbsd_id[1]}]}
    response = self._sas.Deregistration(request)['deregistrationResponse']
    # Check the deregistration response
    for x in range (0, 2):
      self.assertEqual(response[x]['cbsdId'], cbsd_id[x])
      self.assertEqual(response[x]['response']['responseCode'], 0)

  @winnforum_testcase
  def test_10_15_4_2_1(self):
    """CBSD deregistration request with missing required parameter.

    The required parameter 'cbsdId' is missing in a deregistration request,
    the response should be FAIL.
    """

    # Register the device
    device_a = json.load(
        open(os.path.join('testcases', 'testdata', 'device_a.json')))
    self._sas_admin.InjectFccId({'fccId': device_a['fccId']})
    request = {'registrationRequest': [device_a]}
    response = self._sas.Registration(request)['registrationResponse'][0]
    # Check registration response
    self.assertEqual(response['response']['responseCode'], 0)
    del request, response

    # Deregister the device
    request = {'deregistrationRequest': [{}]}
    response = self._sas.Deregistration(request)['deregistrationResponse'][0]
    # Check the deregistration response
    self.assertFalse('cbsdId' in response)
    self.assertEqual(response['response']['responseCode'], 102)
