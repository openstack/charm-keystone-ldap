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

import charmhelpers.contrib.openstack.amulet.deployment as amulet_deployment
import charmhelpers.contrib.openstack.amulet.utils as os_amulet_utils

# Use DEBUG to turn on debug logging
u = os_amulet_utils.OpenStackAmuletUtils(os_amulet_utils.DEBUG)


class KeystoneLDAPCharmDeployment(amulet_deployment.OpenStackAmuletDeployment):
    """Amulet tests on a basic sdn_charm deployment."""

    def __init__(self, series, openstack=None, source=None, stable=True):
        """Deploy the entire test environment."""
        super(KeystoneLDAPCharmDeployment, self).__init__(series, openstack,
                                                          source, stable)
        self._add_services()
        self._add_relations()
        self._deploy()
        # Run the configure post-deploy to get the ldap-server's IP
        # for use by keystone-ldap
        self._configure_services()

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
            {'name': 'percona-cluster'},
            {'name': 'ldap-server',
             'location': 'cs:~openstack-charmers/ldap-test-fixture'},
        ]
        super(KeystoneLDAPCharmDeployment, self)._add_services(
            this_service,
            other_services,
            no_origin=['keystone-ldap', 'ldap-server']
        )

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
            'max-connections': 1000,
        }
        configs = {'keystone': keystone_config,
                   'keystone-ldap': keystone_ldap_config,
                   'percona-cluster': pxc_config}
        super(KeystoneLDAPCharmDeployment, self)._configure_services(configs)

    def _get_ldap_config(self):
        self.ldap_server_sentry = self.d.sentry['ldap-server'][0]
        self.ldap_server_ip = self.ldap_server_sentry.info['public-address']

        keystone_ldap_config = {
            'ldap-server': "ldap://{}".format(self.ldap_server_ip),
            'ldap-user': 'cn=admin,dc=test,dc=com',
            'ldap-password': 'crapper',
            'ldap-suffix': 'dc=test,dc=com',
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
        self.keystone_ip = self.keystone_sentry.relation(
            'shared-db',
            'percona-cluster:shared-db')['private-address']

        # Authenticate admin with keystone
        self.keystone_session, self.keystone = u.get_default_keystone_session(
            self.keystone_sentry,
            openstack_release=self._get_openstack_release(),
            api_version=3)

    def find_keystone_v3_user(self, client, username, domain):
        """Find a user within a specified keystone v3 domain"""
        domain_users = client.users.list(
            domain=client.domains.find(name=domain).id
        )
        usernames = []
        for user in domain_users:
            usernames.append(user.name)
            if username.lower() == user.name.lower():
                return user
        u.log.debug("The user {} was not in these users: {}. Returning None."
                    "".format(username, usernames))
        return None

    def test_100_keystone_ldap_users(self):
        """Validate basic functionality of keystone API"""
        if not self.ldap_configured:
            msg = 'Skipping API tests as no LDAP test fixture'
            u.log.info(msg)
            return

        # NOTE(jamespage): Test fixture should have johndoe and janedoe
        #                  accounts
        johndoe = self.find_keystone_v3_user(self.keystone,
                                             'john doe', 'userdomain')
        assert johndoe is not None
        janedoe = self.find_keystone_v3_user(self.keystone,
                                             'jane doe', 'userdomain')
        assert janedoe is not None
