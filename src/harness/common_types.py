#  Copyright 2018 SAS Project Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

""" Contains common types definitions and type aliases (for type annotations) used by various modules. """

from typing import Dict, List, Tuple, Any, Optional, Union, NoReturn, AnyStr

from enum import Enum


# Define an enumeration class named ResponseCodes with members
# 'SUCCESS',TERMINATED_GRANT', 'SUSPENDED_GRANT'.
class ResponseCodes(Enum):
    """Contains response code."""
    SUCCESS = 0
    TERMINATED_GRANT = 500
    SUSPENDED_GRANT = 501


## type aliases

FrequencyRange = Dict[str, int] # lowest and highest frequencies in the range in Hz
OperationParam = Dict[str, Union[float, FrequencyRange]]
StrDict = Dict[str, str]
InstallationParam = Dict[str, Union[float, int, bool, str]]
RegistrationRequest = Dict[str, Union[str, StrDict, List[str], List[StrDict], InstallationParam]]
MeasReport = Dict[str, float]
GrantRequest = Dict[str, Union[str, OperationParam, MeasReport]]
HeartbeatRequest = Dict[str, Union[str, bool, MeasReport]]
PpaInfo = Dict[str, Union[str, List[str]]]
Response = Dict[str, Union[int, str]]
HeartbeatResponse = Dict[str, Union[str, float, OperationParam, Response]]
# HeartbeatResponse and GrantResponse *do* have the same signature, but since we want to be able to automatically map the signature to the alias name programmatically, so we give GrantResponse the (nearly) equivalent alias (AnyStr == Union[str, bytes]): 
GrantResponse = Dict[AnyStr, Union[float, str, OperationParam, Response]]
RelinquishmentResponse = Dict[str, Union[str, Response]]

# GroupParam = Dict[str, str]
# CbsdInfoObj = Dict[str, str]
# AirInterfaceObj = Dict[str, str]
CbsdRecordData = Dict[str, Union[str, List[str], Dict[str, str], InstallationParam]]

# from GrantRecord.schema
GrantData = Dict[str, Union[str, bool, OperationParam]]

CbsdData = Dict[str, Union[str, CbsdRecordData, List[GrantRecord]]