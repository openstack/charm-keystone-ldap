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
                'clear_domain_name_configured': ('domain-name-configured', ),
            },
            'when_not': {
                'check_configuration': ('always.run', ),
                'configure_domain_name': ('domain-name-configured', ),
                'clear_domain_name_configured': ('domain-backend.connected', ),
            }
        }
        # test that the hooks were registered via the
        # reactive.keystone_ldap_handlers
        self.registered_hooks_test_helper(handlers, hook_set, defaults)


class TestKeystoneLDAPCharmHandlers(test_utils.PatchHelper):

    def patch(self, obj, attr, return_value=None, side_effect=None):
        mocked = mock.patch.object(obj, attr)
        self._patches[attr] = mocked
        started = mocked.start()
        started.return_value = return_value
        started.side_effect = side_effect
        self._patches_start[attr] = started
        setattr(self, attr, started)

    def test_configure_domain_name_application(self):
        self.patch(handlers.keystone_ldap, 'render_config')
        self.patch(handlers.hookenv, 'config')
        self.patch(handlers.hookenv, 'service_name')
        self.patch(handlers.reactive, 'set_state')
        self.config.return_value = None
        self.service_name.return_value = 'keystone-ldap'
        domain = mock.MagicMock()
        handlers.configure_domain_name(domain)
        self.render_config.assert_called_with(
            domain.trigger_restart
        )
        domain.domain_name.assert_called_with(
            'keystone-ldap'
        )
        self.set_state.assert_called_once_with('domain-name-configured')

    def test_clear_domain_name_configured(self):
        self.patch(handlers.reactive, 'remove_state')
        domain = mock.MagicMock()
        handlers.clear_domain_name_configured(domain)
        self.remove_state.assert_called_once_with('domain-name-configured')

    def test_configure_domain_name_config(self):
        self.patch(handlers.keystone_ldap, 'render_config')
        self.patch(handlers.hookenv, 'config')
        self.patch(handlers.hookenv, 'service_name')
        self.config.return_value = 'mydomain'
        self.service_name.return_value = 'keystone-ldap'
        domain = mock.MagicMock()
        handlers.configure_domain_name(domain)
        self.render_config.assert_called_with(
            domain.trigger_restart
        )
        domain.domain_name.assert_called_with(
            'mydomain'
        )

    def test_check_configuration(self):
        self.patch(handlers.keystone_ldap, 'configuration_complete')
        self.patch(handlers.reactive, 'set_state')
        self.patch(handlers.reactive, 'remove_state')
        self.patch(handlers.keystone_ldap, 'assess_status')
        self.configuration_complete.return_value = True
        handlers.check_configuration()
        self.set_state.assert_called_with('config.complete')
        self.configuration_complete.return_value = False
        handlers.check_configuration()
        self.remove_state.assert_called_with('config.complete')
        self.assertTrue(self.assess_status.called)
