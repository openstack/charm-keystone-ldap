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

from __future__ import absolute_import
from __future__ import print_function

import mock

from charms_openstack.test_mocks import charmhelpers as ch
ch.contrib.openstack.utils.OPENSTACK_RELEASES = ('mitaka', )

import reactive.keystone_ldap_handlers as handlers

import charms_openstack.test_utils as test_utils


class TestRegisteredHooks(test_utils.TestRegisteredHooks):

    def test_hooks(self):
        defaults = [
            'charm.installed',
            'update-status']
        hook_set = {
            'when': {
                'configure_domain_name': ('domain-backend.connected',
                                          'config.complete'),
                'keystone_departed': ('domain-name-configured',),
                'config_changed': ('domain-backend.connected',),
                'render_config': ('config.complete',
                                  'domain-backend.connected',
                                  'domain-name-configured'),
            },
            'when_not': {
                'assess_status': ('always.run',),
                'configure_domain_name': ('domain-name-configured',),
                'keystone_departed': ('domain-backend.connected',),
                'config_changed': ('config.complete',),
                'render_config': ('config.rendered',),
            }
        }
        # test that the hooks were registered via the
        # reactive.keystone_ldap_handlers
        self.registered_hooks_test_helper(handlers, hook_set, defaults)


class TestKeystoneLDAPCharmHandlers(test_utils.PatchHelper):

    def _patch_provide_charm_instance(self):
        kldap_charm = mock.MagicMock()
        self.patch('charms_openstack.charm.provide_charm_instance',
                   name='provide_charm_instance',
                   new=mock.MagicMock())
        self.provide_charm_instance().__enter__.return_value = kldap_charm
        self.provide_charm_instance().__exit__.return_value = None
        return kldap_charm

    def test_configure_domain_name_application(self):
        self.patch_object(handlers.hookenv, 'config')
        self.config.return_value = None

        self.patch_object(handlers.hookenv, 'service_name')
        self.service_name.return_value = 'keystone-ldap'

        self.patch_object(handlers.flags, 'set_flag')

        domain = mock.MagicMock()

        handlers.configure_domain_name(domain)

        domain.domain_name.assert_called_with(
            'keystone-ldap'
        )
        self.set_flag.assert_called_once_with('domain-name-configured')

    def test_keystone_departed(self):
        kldap_charm = self._patch_provide_charm_instance()
        self.patch_object(kldap_charm, 'remove_config')

        self.patch_object(handlers.flags, 'clear_flag')

        handlers.keystone_departed()

        self.clear_flag.assert_called_once_with('domain-name-configured')

        kldap_charm.remove_config.assert_called_once()

    def test_configure_domain_name_config(self):
        self.patch_object(handlers.hookenv, 'config')
        self.config.return_value = 'mydomain'

        domain = mock.MagicMock()

        handlers.configure_domain_name(domain)

        domain.domain_name.assert_called_with(
            'mydomain'
        )

    def test_config_changed(self):
        kldap_charm = self._patch_provide_charm_instance()
        self.patch_object(kldap_charm, 'render_config')

        # assume that configuration is complete to test config.rendered
        kldap_charm.configuration_complete.return_value = True

        self.patch_object(handlers.flags, 'set_flag')

        domain = mock.MagicMock()

        handlers.config_changed(domain)

        self.set_flag.assert_called_once_with('config.complete')
        self.render_config.assert_not_called()

    def test_render_config(self):
        kldap_charm = self._patch_provide_charm_instance()
        self.patch_object(kldap_charm, 'render_config')

        self.patch_object(handlers.flags, 'set_flag')

        domain = mock.MagicMock()

        handlers.render_config(domain)

        self.set_flag.assert_called_once_with('config.rendered')

        kldap_charm.render_config.assert_called_with(
            domain.trigger_restart
        )

    def test_assess_status(self):
        kldap_charm = self._patch_provide_charm_instance()
        self.patch_object(kldap_charm, 'assess_status')

        handlers.assess_status()

        kldap_charm.assess_status.assert_called_once()
