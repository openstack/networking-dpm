# Copyright 2017 IBM Corp. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from neutron.tests import base

from networking_dpm.conf.types import MAPPING_REGEX
from networking_dpm.conf.types import NetworkAdapterMappingType

VALID_DPM_OBJECT_ID = "fa1f2466-12df-311a-804c-4ed2cc1d656b"
VALID_DPM_OBJECT_ID_UC = "FA1F2466-12DF-311A-804C-4ED2CC1D656B"
VALID_NETWORK_MAPPING = "physnet:" + VALID_DPM_OBJECT_ID + ":0"
VALID_NETWORK_MAPPING_NO_PORT1 = "physnet:" + VALID_DPM_OBJECT_ID + ":"
VALID_NETWORK_MAPPING_NO_PORT2 = "physnet:" + VALID_DPM_OBJECT_ID


class TestNetworkAdapterMappingType(base.BaseTestCase):
    conf_type = NetworkAdapterMappingType()

    def test_valid_mapping(self):
        net, adapter_id, port = self.conf_type(VALID_NETWORK_MAPPING)
        self.assertEqual("physnet", net)
        self.assertEqual("0", port)
        self.assertEqual(VALID_DPM_OBJECT_ID, adapter_id)

    def test_upper_case_to_lower_case_adapter_id(self):
        net, adapter_id, port = self.conf_type(
            "physnet:" + VALID_DPM_OBJECT_ID_UC + ":0")
        self.assertEqual(VALID_DPM_OBJECT_ID, adapter_id)

    def test_keep_case_physnet(self):
        net, adapter_id, port = self.conf_type(
            "PHysnet:" + VALID_DPM_OBJECT_ID_UC + ":0")
        self.assertEqual("PHysnet", net)

    def test_missing_port_default_1_ok(self):
        net, adapter_id, port = self.conf_type(VALID_NETWORK_MAPPING_NO_PORT1)
        self.assertEqual("physnet", net)
        self.assertEqual("0", port)
        self.assertEqual(VALID_DPM_OBJECT_ID, adapter_id)

    def test_missing_port_default_2_ok(self):
        net, adapter_id, port = self.conf_type(VALID_NETWORK_MAPPING_NO_PORT2)
        self.assertEqual("physnet", net)
        self.assertEqual("0", port)
        self.assertEqual(VALID_DPM_OBJECT_ID, adapter_id)

    def test_empty_value_fail(self):
        self.assertRaises(ValueError, self.conf_type, '')

    def test_invalid_value_fail(self):
        self.assertRaises(ValueError, self.conf_type, 'foobar')

    def test_invalid_port_fail(self):
        self.assertRaises(ValueError, self.conf_type,
                          VALID_NETWORK_MAPPING_NO_PORT1 + "2")

    def test_invalid_port_type_fail(self):
        self.assertRaises(ValueError, self.conf_type,
                          VALID_NETWORK_MAPPING_NO_PORT1 + "a")

    def test_invalid_adapter_id_fail(self):
        self.assertRaises(ValueError, self.conf_type, "physnet:foo:1")

    def test_invalid_pysnet_fail(self):
        invalid = ["phys:net:" + VALID_DPM_OBJECT_ID,
                   "phys:net:" + VALID_DPM_OBJECT_ID + ":",
                   "phys:net:" + VALID_DPM_OBJECT_ID + ":1",
                   "foo:phys:net:" + VALID_DPM_OBJECT_ID,
                   ":net:" + VALID_DPM_OBJECT_ID,
                   "::net:" + VALID_DPM_OBJECT_ID]
        for conf in invalid:
            self.assertRaises(ValueError, self.conf_type, conf)

    def test_repr(self):
        self.assertEqual(
            "String(regex='" + MAPPING_REGEX + "')",
            repr(self.conf_type))

    def test_equal(self):
        self.assertTrue(
            NetworkAdapterMappingType() == NetworkAdapterMappingType())
