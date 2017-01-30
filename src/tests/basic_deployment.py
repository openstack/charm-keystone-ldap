#
# Copyright 2017 Canonical Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

import amulet

import charmhelpers.contrib.openstack.amulet.deployment as amulet_deployment
import charmhelpers.contrib.openstack.amulet.utils as os_amulet_utils

# Use DEBUG to turn on debug logging
u = os_amulet_utils.OpenStackAmuletUtils(os_amulet_utils.DEBUG)


class KeystoneLDAPCharmDeployment(amulet_deployment.OpenStackAmuletDeployment):
    """Amulet tests on a basic sdn_charm deployment."""

    def __init__(self, series, openstack=None, source=None, stable=False):
        """Deploy the entire test environment."""
        super(KeystoneLDAPCharmDeployment, self).__init__(series, openstack,
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
        this_service = {'name': 'keystone-ldap'}
        other_services = [
            {'name': 'keystone'},
            {'name': 'percona-cluster', 'constraints': {'mem': '3072M'}},
        ]
        super(KeystoneLDAPCharmDeployment, self)._add_services(this_service,
                                                               other_services)

    def _add_relations(self):
        """Add all of the relations for the services."""
        relations = {
            'keystone:domain-backend': 'keystone-ldap:domain-backend',
            'keystone:shared-db': 'percona-cluster:shared-db',
        }
        super(KeystoneLDAPCharmDeployment, self)._add_relations(relations)

    def _configure_services(self):
        """Configure all of the services."""
        keystone_config = {
            'admin-password': 'openstack',
            'admin-token': 'ubuntutesting',
            'preferred-api-version': 3,
        }
        keystone_ldap_config = self._get_ldap_config()
        pxc_config = {
            'dataset-size': '25%',
            'max-connections': 1000,
            'root-password': 'ChangeMe123',
            'sst-password': 'ChangeMe123',
        }
        configs = {'keystone': keystone_config,
                   'keystone-ldap': keystone_ldap_config,
                   'percona-cluster': pxc_config}
        super(KeystoneLDAPCharmDeployment, self)._configure_services(configs)

    def _get_ldap_config(self):
        # NOTE(jamespage): use amulet variables for CI specific config
        keystone_ldap_config = {
            'ldap-server': os.environ.get('AMULET_LDAP_SERVER'),
            'ldap-user': os.environ.get('AMULET_LDAP_USER'),
            'ldap-password': os.environ.get('AMULET_LDAP_PASSWORD'),
            'ldap-suffix': os.environ.get('AMULET_LDAP_SUFFIX'),
            'domain-name': 'userdomain',
        }
        if all(keystone_ldap_config.values()):
            self.ldap_configured = True
            return keystone_ldap_config
        else:
            # NOTE(jamespage): Use mock values to check deployment only
            #                  as no test fixture has been supplied
            self.ldap_configured = False
            return {
                'ldap-server': 'myserver',
                'ldap-user': 'myuser',
                'ldap-password': 'mypassword',
                'ldap-suffix': 'mysuffix',
                'domain-name': 'userdomain',
            }


    def _get_token(self):
        return self.keystone.service_catalog.catalog['token']['id']

    def _initialize_tests(self):
        """Perform final initialization before tests get run."""
        # Access the sentries for inspecting service units
        self.keystone_ldap = self.d.sentry['keystone-ldap'][0]
        self.mysql_sentry = self.d.sentry['percona-cluster'][0]
        self.keystone_sentry = self.d.sentry['keystone'][0]
        # Authenticate admin with keystone endpoint
        self.keystone = u.authenticate_keystone_admin(self.keystone_sentry,
                                                      user='admin',
                                                      password='openstack',
                                                      tenant='admin')

    def test_100_services(self):
        """Verify the expected services are running on the corresponding
           service units."""
        u.log.debug('Checking system services on units...')

        service_names = {
            self.keystone_ldap: [],
        }

        ret = u.validate_services_by_name(service_names)
        if ret:
            amulet.raise_status(amulet.FAIL, msg=ret)

        u.log.debug('OK')
