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

import unittest

import mock

import charm.openstack.keystone_ldap as keystone_ldap


class Helper(unittest.TestCase):

    def setUp(self):
        self._patches = {}
        self._patches_start = {}

    def tearDown(self):
        for k, v in self._patches.items():
            v.stop()
            setattr(self, k, None)
        self._patches = None
        self._patches_start = None

    def patch(self, obj, attr, return_value=None, **kwargs):
        mocked = mock.patch.object(obj, attr, **kwargs)
        self._patches[attr] = mocked
        started = mocked.start()
        started.return_value = return_value
        self._patches_start[attr] = started
        setattr(self, attr, started)


class TestKeystoneLDAPCharm(Helper):

    @mock.patch('charmhelpers.core.hookenv.config')
    def test_required_configuration(self, config):
        reply = {
            'ldap-server': 'myserver',
            'ldap-user': 'myusername',
            'ldap-password': 'mypassword',
            'ldap-suffix': 'suffix'
        }

        def mock_config(key=None):
            if key:
                return reply.get(key)
            return reply
        config.side_effect = mock_config
        self.assertTrue(keystone_ldap.configuration_complete())

        for required_config in reply:
            orig = reply[required_config]
            reply[required_config] = None
            self.assertFalse(keystone_ldap.configuration_complete())
            reply[required_config] = orig

        self.assertTrue(keystone_ldap.configuration_complete())

    @mock.patch('charmhelpers.core.hookenv.service_name')
    @mock.patch('charmhelpers.core.hookenv.config')
    def test_domain_name(self, config,
                         service_name):
        config.return_value = None
        service_name.return_value = 'testdomain'
        charm = keystone_ldap.KeystoneLDAPCharm()
        self.assertEqual('testdomain',
                         charm.domain_name)
        self.assertEqual('/etc/keystone/domains/keystone.testdomain.conf',
                         charm.configuration_file)
        config.assert_called_with('domain-name')

        config.return_value = 'userdomain'
        self.assertEqual('userdomain',
                         charm.domain_name)
        self.assertEqual('/etc/keystone/domains/keystone.userdomain.conf',
                         charm.configuration_file)

    @mock.patch('charmhelpers.core.hookenv.config')
    @mock.patch('charmhelpers.core.hookenv.status_set')
    @mock.patch('charmhelpers.core.hookenv.application_version_set')
    def test_assess_status(self,
                           application_version_set,
                           status_set,
                           config):
        reply = {
            'ldap-server': 'myserver',
            'ldap-user': 'myusername',
            'ldap-password': 'mypassword',
            'ldap-suffix': 'suffix'
        }

        def mock_config(key=None):
            if key:
                return reply.get(key)
            return reply
        config.side_effect = mock_config

        # Check that active status is set correctly
        keystone_ldap.assess_status()
        status_set.assert_called_with('active', mock.ANY)
        application_version_set.assert_called_with(
            keystone_ldap.KeystoneLDAPCharm.singleton.application_version
        )

        # Check that blocked status is set correctly
        reply['ldap-server'] = None
        keystone_ldap.assess_status()
        status_set.assert_called_with('blocked', mock.ANY)
        application_version_set.assert_called_with(
            keystone_ldap.KeystoneLDAPCharm.singleton.application_version
        )

    @mock.patch('charmhelpers.core.hookenv.config')
    def test_render_config(self, config):
        self.patch(keystone_ldap.ch_host, 'path_hash')
        self.patch(keystone_ldap.core.templating, 'render')

        reply = {
            'ldap-server': 'myserver',
            'ldap-user': 'myusername',
            'ldap-password': 'mypassword',
            'ldap-suffix': 'suffix',
            'domain-name': 'userdomain',
        }

        def mock_config(key=None):
            if key:
                return reply.get(key)
            return reply
        config.side_effect = mock_config

        self.path_hash.side_effect = ['aaa', 'aaa']
        mock_trigger = mock.MagicMock()

        # Ensure a basic level of function from render_config
        keystone_ldap.render_config(mock_trigger)
        self.render.assert_called_with(
            source=keystone_ldap.KEYSTONE_CONF_TEMPLATE,
            template_loader=mock.ANY,
            target='/etc/keystone/domains/keystone.userdomain.conf',
            context=mock.ANY
        )
        self.assertFalse(mock_trigger.called)

        # Ensure that change in file contents results in call
        # to restart trigger function passed to render_config
        self.path_hash.side_effect = ['aaa', 'bbb']
        keystone_ldap.render_config(mock_trigger)
        self.assertTrue(mock_trigger.called)


class TestKeystoneLDAPAdapters(Helper):

    @mock.patch('charmhelpers.contrib.openstack.utils.config_flags_parser',
                wraps=None)
    @mock.patch('charmhelpers.core.hookenv.config')
    def test_config_adapter(self, config,
                            config_flags_parser):
        reply = {
            'ldap-config-flags':
                'user_id_attribute=cn,user_name_attribute=cn',
        }
        ldap_config = {
            'user_id_attribute': 'cn',
            'user_name_attribute': 'cn'
        }

        def mock_config(key=None):
            if key:
                return reply.get(key)
            return reply
        config.side_effect = mock_config
        config_flags_parser.return_value = ldap_config
        # verify that the class is created with a
        # KeystoneLDAPConfigurationAdapter
        adapter = keystone_ldap.KeystoneLDAPConfigurationAdapter()
        # ensure that the relevant things got put on.
        self.assertEqual(ldap_config,
                         adapter.ldap_options)
        self.assertTrue(config_flags_parser.called)
