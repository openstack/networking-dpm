# Copyright (c) 2016 IBM Corp.
#
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os
import sys

from neutron_lib import constants
from neutron_lib.utils import helpers
from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging
from oslo_service import service
import zhmcclient

from networking_dpm.ml2 import config

from neutron._i18n import _LE, _LI
from neutron.agent.linux import ip_lib
from neutron.api.rpc.handlers import securitygroups_rpc as sg_rpc
from neutron.common import config as common_config
from neutron.common import topics
from neutron.plugins.ml2.drivers.agent import _agent_manager_base as amb
from neutron.plugins.ml2.drivers.agent import _common_agent as ca

LOG = logging.getLogger(__name__)

DPM_AGENT_BINARY = "neutron-dpm-agent"
EXTENSION_DRIVER_TYPE = 'dpm'


class DPMRPCCallBack(sg_rpc.SecurityGroupAgentRpcCallbackMixin,
                         amb.CommonAgentManagerRpcCallBackBase):
    # Set RPC API version to 1.0 by default.
    # history
    #   1.1 Support Security Group RPC
    #   1.3 Added param devices_to_update to security_groups_provider_updated
    #   1.4 Added support for network_update
    target = oslo_messaging.Target(version='1.4')

    def port_update(self, context, **kwargs):
        port = kwargs['port']
        LOG.debug("port_update received for port %s ", port)
        mac = port['mac_address']
        # Put the device name in the updated_devices set.
        # Do not store port details, as if they're used for processing
        # notifications there is no guarantee the notifications are
        # processed in the same order as the relevant API requests.
        self.updated_devices.add(mac)


class DPMManager(amb.CommonAgentManagerBase):
    def __init__(self, interface_mappings):
        self.interface_mappings = interface_mappings
        self.mac_device_name_mappings = dict()

    def ensure_port_admin_state(self, device, admin_state_up):
        LOG.debug("Setting admin_state_up to %s for device %s",
                  admin_state_up, device)
        pass

    def get_agent_configurations(self):
        return {'interface_mappings': self.interface_mappings}

    def get_agent_id(self):
        return 'dpm-%s' % cfg.CONF.host

    def get_devices_modified_timestamps(self, devices):
        # TODO(kevinbenton): this should be implemented to detect
        # rapid Nova instance rebuilds.
        return {}

    def get_all_devices(self):
        devices = set()
        # TODO(andreas_s): Poll DPM API
        return devices

    def get_extension_driver_type(self):
        return EXTENSION_DRIVER_TYPE

    def get_rpc_callbacks(self, context, agent, sg_agent):
        return DPMRPCCallBack(context, agent, sg_agent)

    def get_rpc_consumers(self):
        # TODO(andreas_s): remove security group update
        consumers = [[topics.PORT, topics.UPDATE],
                     [topics.SECURITY_GROUP, topics.UPDATE]]
        return consumers

    def plug_interface(self, network_id, network_segment, device,
                       device_owner):
        return True

    def setup_arp_spoofing_protection(self, device, device_details):
        pass

    def delete_arp_spoofing_protection(self, devices):
        pass

    def delete_unreferenced_arp_protection(self, current_devices):
        pass


def parse_interface_mappings():
    return cfg.CONF.dpm.adapter_interface_mappings


def validate_interface_mappings(interface_mappings, cpc):
    for physnet, adapter_port_dict in interface_mappings.items():
        for adapter, port in adapter_port_dict.items():
            try:
                # If no port-element-id was defined, default to 0
                if not port:
                    adapter_port_dict[adapter] = 0

                #
                # TODO(andreas_s): ask REST API
                # Check if adapter exists
                # Check if port exists
                # Ensure all adapters are on the same cec
            except:
                LOG.error(_LE("Adapter/port combination %(adapt)s/%(port)s "
                              "for physical network %(net)s does not exist. "
                              "Agent terminated!"),
                          {'adapt': adapter, 'port': port, 'net': physnet})
                sys.exit(1)


def validate_firewall_driver():
    fw_driver = cfg.CONF.SECURITYGROUP.firewall_driver
    supported_fw_drivers = ['neutron.agent.firewall.NoopFirewallDriver',
                            'noop']
    if fw_driver not in supported_fw_drivers:
        LOG.error(_LE('Unsupported configuration option for "SECURITYGROUP.'
                      'firewall_driver"! Only the NoopFirewallDriver is '
                      'supported by DPM agent, but "%s" is configured. '
                      'Set the firewall_driver to "noop" and start the '
                      'agent again. Agent terminated!'),
                  fw_driver)
        sys.exit(1)


def _get_cpc(client, cpc_name):

    cpc = None
    try:
        cpc = client.cpcs.find(name=cpc_name)
        if cpc.dpm_enabled:
            return cpc
        LOG.error(_LE("CPC %s not in DPM mode.") % cpc_name)
    except zhmcclient.NotFound:
        LOG.error(_LE("Could not find CPC %s") % (cpc_name))
    sys.exit(1)



def main():
    common_config.init(sys.argv[1:])

    common_config.setup_logging()

    hmc = cfg.CONF.dpm.hmc
    userid = cfg.CONF.dpm.hmc_username
    password = cfg.CONF.dpm.hmc_password
    cpc_name = cfg.CONF.dpm.cpc_name

    session = zhmcclient.Session(hmc, userid, password)
    client = zhmcclient.Client(session)
    cpc = _get_cpc(client, cpc_name)

    interface_mappings = parse_interface_mappings()
    validate_interface_mappings(interface_mappings, cpc)

    manager = DPMManager(interface_mappings)

    polling_interval = cfg.CONF.AGENT.polling_interval
    quitting_rpc_timeout = cfg.CONF.AGENT.quitting_rpc_timeout
    agent = ca.CommonAgentLoop(manager, polling_interval,
                               quitting_rpc_timeout,
                               constants.AGENT_TYPE_MACVTAP,
                               DPM_AGENT_BINARY)
    LOG.info(_LI("Agent initialized successfully, now running... "))
    launcher = service.launch(cfg.CONF, agent)
    launcher.wait()
