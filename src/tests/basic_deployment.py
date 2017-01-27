# Copyright 2016 Canonical Ltd
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#  http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import amulet
import json
import subprocess
import time


import charmhelpers.contrib.openstack.amulet.deployment as amulet_deployment
import charmhelpers.contrib.openstack.amulet.utils as os_amulet_utils

# Use DEBUG to turn on debug logging
u = os_amulet_utils.OpenStackAmuletUtils(os_amulet_utils.DEBUG)


class SDNCharmDeployment(amulet_deployment.OpenStackAmuletDeployment):
    """Amulet tests on a basic sdn_charm deployment."""

    def __init__(self, series, openstack=None, source=None, stable=False):
        """Deploy the entire test environment."""
        super(SDNCharmDeployment, self).__init__(series, openstack,
                                                       source, stable)
        self._add_services()
        self._add_relations()
        self._configure_services()
        self._deploy()

        u.log.info('Waiting on extended status checks...')
        exclude_services = ['mysql', 'mongodb']
        self._auto_wait_for_status(exclude_services=exclude_services)

        self._initialize_tests()

    def _add_services(self):
        """Add services

           Add the services that we're testing, where sdn_charm is local,
           and the rest of the service are from lp branches that are
           compatible with the local charm (e.g. stable or next).
           """
        this_service = {'name': 'sdn_charm'}
        other_services = [
            {
                'name': 'nova-compute',
                'constraints': {'mem': '4G'},
            },
            {
                'name': 'neutron-api',
            },
            {
                'name': 'neutron-gateway',
            },
            {'name': 'mysql'},
            {'name': 'rabbitmq-server'},
            {'name': 'keystone'},
            {'name': 'nova-cloud-controller'},
            {'name': 'glance'},
        ]
        super(SDNCharmDeployment, self)._add_services(this_service,
                                                      other_services)

    def _add_relations(self):
        """Add all of the relations for the services."""
        relations = {
            'nova-compute:neutron-plugin': 'sdn_charm:neutron-plugin',
            'keystone:shared-db': 'mysql:shared-db',
            'nova-cloud-controller:shared-db': 'mysql:shared-db',
            'nova-cloud-controller:amqp': 'rabbitmq-server:amqp',
            'nova-cloud-controller:image-service': 'glance:image-service',
            'nova-cloud-controller:identity-service':
            'keystone:identity-service',
            'nova-compute:cloud-compute':
            'nova-cloud-controller:cloud-compute',
            'nova-compute:amqp': 'rabbitmq-server:amqp',
            'nova-compute:image-service': 'glance:image-service',
            'glance:shared-db': 'mysql:shared-db',
            'glance:identity-service': 'keystone:identity-service',
            'glance:amqp': 'rabbitmq-server:amqp',
            'neutron-api:shared-db': 'mysql:shared-db',
            'neutron-api:amqp': 'rabbitmq-server:amqp',
            'neutron-api:neutron-api': 'nova-cloud-controller:neutron-api',
            'neutron-api:identity-service': 'keystone:identity-service',
            'neutron-gateway:amqp': 'rabbitmq-server:amqp',
            'neutron-gateway:neutron-plugin-api':
            'neutron-api:neutron-plugin-api',
            'neutron-gateway:quantum-network-service':
            'nova-cloud-controller:quantum-network-service',
            'neutron-gateway:juju-info': 'sdn_charm:container',
        }
        super(SDNCharmDeployment, self)._add_relations(relations)

    def _configure_services(self):
        """Configure all of the services."""
        keystone_config = {'admin-password': 'openstack',
                           'admin-token': 'ubuntutesting'}
        configs = {'keystone': keystone_config}
        super(SDNCharmDeployment, self)._configure_services(configs)

    def _get_token(self):
        return self.keystone.service_catalog.catalog['token']['id']

    def _initialize_tests(self):
        """Perform final initialization before tests get run."""
        # Access the sentries for inspecting service units
        self.sdn_charm_sentry = self.d.sentry['sdn_charm'][0]
        self.mysql_sentry = self.d.sentry['mysql'][0]
        self.keystone_sentry = self.d.sentry['keystone'][0]
        self.rabbitmq_sentry = self.d.sentry['rabbitmq-server'][0]
        self.sdn_charm_svcs = [
            'sdn_charm-agent', 'sdn_charm-api']

        # Authenticate admin with keystone endpoint
        self.keystone = u.authenticate_keystone_admin(self.keystone_sentry,
                                                      user='admin',
                                                      password='openstack',
                                                      tenant='admin')

    def check_and_wait(self, check_command, interval=2, max_wait=200,
                       desc=None):
        waited = 0
        while not check_command() or waited > max_wait:
            if desc:
                u.log.debug(desc)
            time.sleep(interval)
            waited = waited + interval
        if waited > max_wait:
            raise Exception('cmd failed {}'.format(check_command))

    def _run_action(self, unit_id, action, *args):
        command = ["juju", "action", "do", "--format=json", unit_id, action]
        command.extend(args)
        print("Running command: %s\n" % " ".join(command))
        output = subprocess.check_output(command)
        output_json = output.decode(encoding="UTF-8")
        data = json.loads(output_json)
        action_id = data[u'Action queued with id']
        return action_id

    def _wait_on_action(self, action_id):
        command = ["juju", "action", "fetch", "--format=json", action_id]
        while True:
            try:
                output = subprocess.check_output(command)
            except Exception as e:
                print(e)
                return False
            output_json = output.decode(encoding="UTF-8")
            data = json.loads(output_json)
            if data[u"status"] == "completed":
                return True
            elif data[u"status"] == "failed":
                return False
            time.sleep(2)

    def test_100_services(self):
        """Verify the expected services are running on the corresponding
           service units."""
        u.log.debug('Checking system services on units...')

        service_names = {
            self.sdn_charm_sentry: self.sdn_charm_svcs,
        }

        ret = u.validate_services_by_name(service_names)
        if ret:
            amulet.raise_status(amulet.FAIL, msg=ret)

        u.log.debug('OK')
