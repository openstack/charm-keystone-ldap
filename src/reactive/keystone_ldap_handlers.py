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

import charms_openstack.charm as charm
import charms.reactive as reactive

import charm.openstack.keystone_ldap as keystone_ldap  # noqa

import charmhelpers.core.hookenv as hookenv

charm.use_defaults(
    'charm.installed',
    'update-status')


@reactive.when('domain-backend.connected')
@reactive.when_not('domain-name-configured')
@reactive.when('config.complete')
def configure_domain_name(domain):
    keystone_ldap.render_config(domain.trigger_restart)
    domain.domain_name(hookenv.config('domain-name') or
                       hookenv.service_name())
    reactive.set_state('domain-name-configured')


@reactive.when_not('domain-backend.connected')
@reactive.when('domain-name-configured')
def clear_domain_name_configured(domain):
    reactive.remove_state('domain-name-configured')


@reactive.when_not('always.run')
def check_configuration():
    '''Validate required configuration options at set state'''
    if keystone_ldap.configuration_complete():
        reactive.set_state('config.complete')
    else:
        reactive.remove_state('config.complete')
    keystone_ldap.assess_status()
