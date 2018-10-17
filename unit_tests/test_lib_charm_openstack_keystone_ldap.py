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
import textwrap

import charms_openstack.test_utils as test_utils

import charm.openstack.keystone_ldap as keystone_ldap

from charms_openstack.charm import provide_charm_instance


class Helper(test_utils.PatchHelper):

    def setUp(self):
        super().setUp()
        self.patch_release(keystone_ldap.KeystoneLDAPCharm.release)


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

        with provide_charm_instance() as kldap_charm:
            self.assertTrue(kldap_charm.configuration_complete())

            for required_config in reply:
                orig = reply[required_config]
                reply[required_config] = None
                self.assertFalse(kldap_charm.configuration_complete())
                reply[required_config] = orig

            self.assertTrue(kldap_charm.configuration_complete())

    @mock.patch('charmhelpers.core.hookenv.service_name')
    @mock.patch('charmhelpers.core.hookenv.config')
    def test_domain_name(self, config,
                         service_name):
        config.return_value = None
        service_name.return_value = 'testdomain'
        with provide_charm_instance() as kldap_charm:
            self.assertEqual('testdomain',
                             kldap_charm.domain_name)
            self.assertEqual(
                '/etc/keystone/domains/keystone.testdomain.conf',
                kldap_charm.configuration_file)
            config.assert_called_with('domain-name')

            config.return_value = 'userdomain'
            self.assertEqual('userdomain',
                             kldap_charm.domain_name)
            self.assertEqual(
                '/etc/keystone/domains/keystone.userdomain.conf',
                kldap_charm.configuration_file)

    @mock.patch('charmhelpers.contrib.openstack.utils.is_unit_upgrading_set')
    @mock.patch('charmhelpers.contrib.openstack.utils.snap_install_requested')
    @mock.patch('charmhelpers.core.hookenv.config')
    @mock.patch('charmhelpers.core.hookenv.status_set')
    @mock.patch('charmhelpers.core.hookenv.application_version_set')
    def test_assess_status(self,
                           application_version_set,
                           status_set,
                           config, snap_install_requested,
                           is_unit_upgrading_set):
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

        snap_install_requested.return_value = False
        is_unit_upgrading_set.return_value = False

        with provide_charm_instance() as kldap_charm:
            # Check that active status is set correctly
            kldap_charm.assess_status()
            status_set.assert_called_with('active', mock.ANY)
            application_version_set.assert_called_with(
                kldap_charm.application_version
            )

            # Check that blocked status is set correctly
            reply['ldap-server'] = None
            kldap_charm.assess_status()
            status_set.assert_called_with('blocked', mock.ANY)
            application_version_set.assert_called_with(
                kldap_charm.application_version
            )

    @mock.patch('charmhelpers.core.hookenv.config')
    def test_render_config(self, config):
        self.patch_object(keystone_ldap.ch_host, 'file_hash')
        self.patch_object(keystone_ldap.core.templating, 'render')

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

        self.file_hash.side_effect = ['aaa', 'aaa']
        mock_trigger = mock.MagicMock()

        with provide_charm_instance() as kldap_charm:
            # Ensure a basic level of function from render_config
            kldap_charm.render_config(mock_trigger)
            self.render.assert_called_with(
                source=keystone_ldap.KEYSTONE_CONF_TEMPLATE,
                template_loader=mock.ANY,
                target='/etc/keystone/domains/keystone.userdomain.conf',
                context=mock.ANY
            )
            self.assertFalse(mock_trigger.called)

            # Ensure that change in file contents results in call
            # to restart trigger function passed to render_config
            self.file_hash.side_effect = ['aaa', 'bbb']
            kldap_charm.render_config(mock_trigger)
            self.assertTrue(mock_trigger.called)

    @mock.patch('charmhelpers.core.hookenv.config')
    @mock.patch('charmhelpers.core.hookenv.service_name')
    def test_render_config_tls(self, service_name, config):
        self.patch_object(keystone_ldap.ch_host, 'file_hash')
        self.patch_object(keystone_ldap.ch_host, 'write_file')
        self.patch_object(keystone_ldap.core.templating, 'render')
        self.patch_object(keystone_ldap.core.templating, 'render')

        reply = {
            'ldap-server': 'myserver',
            'ldap-user': 'myusername',
            'ldap-password': 'mypassword',
            'ldap-suffix': 'suffix',
            'domain-name': 'userdomain',
            'tls-ca-ldap': textwrap.dedent("""
            -----BEGIN CERTIFICATE-----
            MIIEIDCCAwigAwIBAgIQNE7VVyDV7exJ9C/ON9srbTANBgkqhkiG9w0BAQUFADCB
            qTELMAkGA1UEBhMCVVMxFTATBgNVBAoTDHRoYXd0ZSwgSW5jLjEoMCYGA1UECxMf
            Q2VydGlmaWNhdGlvbiBTZXJ2aWNlcyBEaXZpc2lvbjE4MDYGA1UECxMvKGMpIDIw
            MDYgdGhhd3RlLCBJbmMuIC0gRm9yIGF1dGhvcml6ZWQgdXNlIG9ubHkxHzAdBgNV
            BAMTFnRoYXd0ZSBQcmltYXJ5IFJvb3QgQ0EwHhcNMDYxMTE3MDAwMDAwWhcNMzYw
            NzE2MjM1OTU5WjCBqTELMAkGA1UEBhMCVVMxFTATBgNVBAoTDHRoYXd0ZSwgSW5j
            LjEoMCYGA1UECxMfQ2VydGlmaWNhdGlvbiBTZXJ2aWNlcyBEaXZpc2lvbjE4MDYG
            A1UECxMvKGMpIDIwMDYgdGhhd3RlLCBJbmMuIC0gRm9yIGF1dGhvcml6ZWQgdXNl
            IG9ubHkxHzAdBgNVBAMTFnRoYXd0ZSBQcmltYXJ5IFJvb3QgQ0EwggEiMA0GCSqG
            SIb3DQEBAQUAA4IBDwAwggEKAoIBAQCsoPD7gFnUnMekz52hWXMJEEUMDSxuaPFs
            W0hoSVk3/AszGcJ3f8wQLZU0HObrTQmnHNK4yZc2AreJ1CRfBsDMRJSUjQJib+ta
            3RGNKJpchJAQeg29dGYvajig4tVUROsdB58Hum/u6f1OCyn1PoSgAfGcq/gcfomk
            6KHYcWUNo1F77rzSImANuVud37r8UVsLr5iy6S7pBOhih94ryNdOwUxkHt3Ph1i6
            Sk/KaAcdHJ1KxtUvkcx8cXIcxcBn6zL9yZJclNqFwJu/U30rCfSMnZEfl2pSy94J
            NqR32HuHUETVPm4pafs5SSYeCaWAe0At6+gnhcn+Yf1+5nyXHdWdAgMBAAGjQjBA
            MA8GA1UdEwEB/wQFMAMBAf8wDgYDVR0PAQH/BAQDAgEGMB0GA1UdDgQWBBR7W0XP
            r87Lev0xkhpqtvNG61dIUDANBgkqhkiG9w0BAQUFAAOCAQEAeRHAS7ORtvzw6WfU
            DW5FvlXok9LOAz/t2iWwHVfLHjp2oEzsUHboZHIMpKnxuIvW1oeEuzLlQRHAd9mz
            YJ3rG9XRbkREqaYB7FViHXe4XI5ISXycO1cRrK1zN44veFyQaEfZYGDm/Ac9IiAX
            xPcW6cTYcvnIc3zfFi8VqT79aie2oetaupgf1eNNZAqdE8hhuvU5HIe6uL17In/2
            /qxAeeWsEG89jxt5dovEN7MhGITlNgDrYyCZuen+MwS7QcjBAvlEYyCegc5C09Y/
            LHbTY5xZ3Y+m4Q6gLkH3LpVHz7z9M/P2C2F+fpErgUfCJzDupxBdN49cOSvkBPB7
            jVaMaA==
            -----END CERTIFICATE-----
            """)
        }

        def mock_config(key=None):
            if key:
                return reply.get(key)
            return reply
        config.side_effect = mock_config

        svc_name = 'keystone_ldap'
        service_name.return_value = svc_name

        self.file_hash.side_effect = [
            'templatehash',
            'templatehash',
            'de3d5930e6e6b3fdb385f60a05206588',
            'de3d5930e6e6b3fdb385f60a05206588',
        ]
        mock_trigger = mock.MagicMock()

        with provide_charm_instance() as kldap_charm:
            # Ensure a basic level of function from render_config
            kldap_charm.render_config(mock_trigger)
            self.render.assert_called_with(
                source=keystone_ldap.KEYSTONE_CONF_TEMPLATE,
                template_loader=mock.ANY,
                target='/etc/keystone/domains/keystone.userdomain.conf',
                context=mock.ANY
            )
            self.write_file.assert_called_with(
                keystone_ldap.BACKEND_CA_CERT.format(svc_name),
                reply['tls-ca-ldap'],
                owner='root',
                group='root',
                perms=0o644,
            )
            self.assertFalse(mock_trigger.called)

            # template file change leads to restart without a change
            # in a cert
            self.file_hash.side_effect = [
                'oldtemplatehash',
                'newtemplatehash',
                'de3d5930e6e6b3fdb385f60a05206588',
                'de3d5930e6e6b3fdb385f60a05206588',
            ]

            kldap_charm.render_config(mock_trigger)
            self.assertTrue(mock_trigger.called)

            # cert change without template change
            self.file_hash.side_effect = [
                'templatehash',
                'templatehash',
                'deadbeefdeadbeefdeadbeefdeadbeef',
                'de3d5930e6e6b3fdb385f60a05206588',
            ]
            kldap_charm.render_config(mock_trigger)
            self.assertTrue(mock_trigger.called)

    @mock.patch('charmhelpers.core.hookenv.config')
    @mock.patch('os.path.exists')
    @mock.patch('os.unlink')
    def test_remove_config(self, unlink, exists, config):
        exists.return_value = True

        self.patch_object(keystone_ldap.ch_host, 'file_hash')

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

        with provide_charm_instance() as kldap_charm:
            # Ensure a basic level of function from render_config
            cf = keystone_ldap.DOMAIN_CONF.format(reply['domain-name'])
            kldap_charm.remove_config()
            exists.assert_called_once_with(cf)
            unlink.assert_called_once_with(cf)


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
