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

import os

# release detection is done via keystone package given that
# openstack-origin is not present in the subordinate charm
# see https://github.com/juju/charm-helpers/issues/83
import charmhelpers.core.unitdata as unitdata
from charms_openstack.charm.core import (
    register_os_release_selector
)
OPENSTACK_RELEASE_KEY = 'charmers.openstack-release-version'

DOMAIN_CONF = "/etc/keystone/domains/keystone.{}.conf"
BACKEND_CA_CERT = "/usr/share/ca-certificates/{}.crt"
KEYSTONE_CONF_TEMPLATE = "keystone.conf"


@register_os_release_selector
def select_release():
    """Determine the release based on the keystone package version.

    Note that this function caches the release after the first install so
    that it doesn't need to keep going and getting it from the package
    information.
    """
    release_version = unitdata.kv().get(OPENSTACK_RELEASE_KEY, None)
    if release_version is None:
        release_version = os_utils.os_release('keystone')
        unitdata.kv().set(OPENSTACK_RELEASE_KEY, release_version)
    return release_version


class KeystoneLDAPConfigurationAdapter(
        charms_openstack.adapters.ConfigurationAdapter):
    '''Charm specific configuration adapter to deal with ldap
    config flag parsing
    '''

    def __init__(self, charm_instance=None):
        super(KeystoneLDAPConfigurationAdapter,
              self).__init__(charm_instance=self)

        # Return if ldap-config-flags is not set or empty string
        ldap_config_flags = hookenv.config('ldap-config-flags')
        if ldap_config_flags is None or ldap_config_flags == '':
            self.ldap_options = {}
            return

        self.ldap_options = os_utils.config_flags_parser(ldap_config_flags)
        # Get all the options that starts with ldap_
        filtered_options = [k for k in vars(self) if k.startswith('ldap_')]
        for cfg_opt in filtered_options:
            # We only override if the option is not empty
            charm_opt = cfg_opt.replace("_", "-")
            cfg_value = hookenv.config(charm_opt)
            if cfg_value in (None, ''):
                continue
            ldap_opt = cfg_opt.replace('ldap_', '')
            # Found a collision in ldap-config-flags
            if ldap_opt in self.ldap_options:
                hookenv.log(
                    "LDAP config {} specified in ldap-config-flags is being "
                    "overridden with the value specified in charm config "
                    "{}".format(ldap_opt, charm_opt), level=hookenv.WARNING)
                # Remove the one declared in ldap-config-flags
                self.ldap_options.pop(ldap_opt)

    @property
    def backend_ca_file(self):
        return BACKEND_CA_CERT.format(hookenv.service_name())

    @property
    def use_tls(self):
        ldap_srv = hookenv.config('ldap-server')
        return not ldap_srv.startswith('ldaps') if ldap_srv else False


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

    @staticmethod
    def configuration_complete():
        """Determine whether sufficient configuration has been provided
        to configure keystone for use with a LDAP backend

        :returns: boolean indicating whether configuration is complete
        """
        required_config = {
            'ldap_server': hookenv.config('ldap-server'),
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
        elif os_utils.is_unit_upgrading_set():
            hookenv.status_set('blocked',
                               'Ready for do-release-upgrade and reboot. '
                               'Set complete when finished.')
        else:
            hookenv.status_set('active',
                               'Unit is ready')

    def render_config(self, restart_trigger):
        """Render the domain specific LDAP configuration for the application
        """
        checksum = ch_host.file_hash(self.configuration_file)
        core.templating.render(
            source=KEYSTONE_CONF_TEMPLATE,
            template_loader=os_templating.get_loader(
                'templates/', self.release),
            target=self.configuration_file,
            context=self.adapters_instance)

        tmpl_changed = (checksum !=
                        ch_host.file_hash(self.configuration_file))

        cert = hookenv.config('tls-ca-ldap')

        cert_changed = False
        if cert:
            ca_file = self.options.backend_ca_file
            old_cert_csum = ch_host.file_hash(ca_file)
            ch_host.write_file(ca_file, cert,
                               owner='root', group='root', perms=0o644)
            cert_csum = ch_host.file_hash(ca_file)
            cert_changed = (old_cert_csum != cert_csum)

        if tmpl_changed or cert_changed:
            restart_trigger()

    def remove_config(self):
        """
        Remove the domain-specific LDAP configuration file and trigger
        keystone restart.
        """
        if os.path.exists(self.configuration_file):
            os.unlink(self.configuration_file)

        if (hookenv.config('tls-ca-ldap') and
           os.path.exists(self.options.backend_ca_file)):
            os.unlink(self.options.backend_ca_file)


class KeystoneLDAPCharmRocky(KeystoneLDAPCharm):

    # First release supported
    release = 'rocky'

    # List of packages to install for this charm
    # Explicitly install python3-ldap so python3-ldappool does not install
    # python-ldap
    packages = ['python3-ldap', 'python3-ldappool']

    purge_packages = ['python-ldap', 'python-ldappool']

    python_version = 3
