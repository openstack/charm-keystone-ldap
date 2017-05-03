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

import charmhelpers.core as core
import charmhelpers.core.host as ch_host
import charmhelpers.core.hookenv as hookenv

import charmhelpers.contrib.openstack.templating as os_templating
import charmhelpers.contrib.openstack.utils as os_utils

import charms_openstack.charm
import charms_openstack.adapters


DOMAIN_CONF = "/etc/keystone/domains/keystone.{}.conf"
KEYSTONE_CONF_TEMPLATE = "keystone.conf"


class KeystoneLDAPConfigurationAdapter(
        charms_openstack.adapters.ConfigurationAdapter):
    '''Charm specific configuration adapter to deal with ldap
    config flag parsing
    '''

    @property
    def ldap_options(self):
        return os_utils.config_flags_parser(
            hookenv.config('ldap-config-flags')
        )


class KeystoneLDAPCharm(charms_openstack.charm.OpenStackCharm):

    # Internal name of charm
    service_name = name = 'keystone-ldap'

    # Package to derive application version from
    version_package = 'keystone'

    # First release supported
    release = 'mitaka'

    # List of packages to install for this charm
    packages = ['python-ldappool']

    configuration_class = KeystoneLDAPConfigurationAdapter

    @property
    def domain_name(self):
        """Domain name for the running application

        :returns: string: containing the current domain name for the
                          application
        """
        return hookenv.config('domain-name') or hookenv.service_name()

    def configuration_complete(self):
        """Determine whether sufficient configuration has been provided
        to configure keystone for use with a LDAP backend

        :returns: boolean indicating whether configuration is complete
        """
        required_config = {
            'ldap_server': hookenv.config('ldap-server'),
            'ldap_user': hookenv.config('ldap-user'),
            'ldap_password': hookenv.config('ldap-password'),
            'ldap_suffix': hookenv.config('ldap-suffix'),
        }
        return all(required_config.values())

    @property
    def configuration_file(self):
        """Configuration file for domain configuration"""
        return DOMAIN_CONF.format(self.domain_name)

    def assess_status(self):
        """Determine the current application status for the charm"""
        hookenv.application_version_set(self.application_version)
        if not self.configuration_complete():
            hookenv.status_set('blocked',
                               'LDAP configuration incomplete')
        else:
            hookenv.status_set('active',
                               'Unit is ready')

    def render_config(self, restart_trigger):
        """Render the domain specific LDAP configuration for the application
        """
        checksum = ch_host.path_hash(self.configuration_file)
        core.templating.render(
            source=KEYSTONE_CONF_TEMPLATE,
            template_loader=os_templating.get_loader(
                'templates/', self.release),
            target=self.configuration_file,
            context=self.adapters_instance)
        if checksum != ch_host.path_hash(self.configuration_file):
            restart_trigger()


def render_config(restart_trigger):
    """Render the configuration for the charm

    :params: restart_trigger: function to call if configuration file
                              changed as a result of rendering
    """
    KeystoneLDAPCharm.singleton.render_config(restart_trigger)


def assess_status():
    """Just call the KeystoneLDAPCharm.singleton.assess_status() command
    to update status on the unit.
    """
    KeystoneLDAPCharm.singleton.assess_status()


def configuration_complete():
    """Determine whether charm configuration is actually complete"""
    return KeystoneLDAPCharm.singleton.configuration_complete()


def configuration_file():
    """Configuration file for current domain configuration"""
    return KeystoneLDAPCharm.singleton.configuration_file
