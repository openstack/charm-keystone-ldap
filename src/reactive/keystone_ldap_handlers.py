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

# import to trigger openstack charm metaclass init
import charm.openstack.keystone_ldap  # noqa

import charms_openstack.charm as charm
import charms.reactive as reactive

import charms.reactive.flags as flags

import charmhelpers.core.hookenv as hookenv

charm.use_defaults(
    'charm.installed',
    'update-status')

# if config has been changed we need to re-evaluate flags
# config.changed is set and cleared (atexit) in layer-basic
flags.register_trigger(when='config.changed',
                       clear_flag='config.rendered')
flags.register_trigger(when='config.changed',
                       clear_flag='config.complete')


@reactive.when('domain-backend.connected')
@reactive.when_not('domain-name-configured')
@reactive.when('config.complete')
def configure_domain_name(domain):
    domain.domain_name(hookenv.config('domain-name') or
                       hookenv.service_name())
    flags.set_flag('domain-name-configured')


@reactive.when_not('domain-backend.connected')
@reactive.when('domain-name-configured')
def keystone_departed():
    """
    Service restart should be handled on the keystone side
    in this case.
    """
    flags.clear_flag('domain-name-configured')
    with charm.provide_charm_instance() as kldap_charm:
        kldap_charm.remove_config()


@reactive.when('domain-backend.connected')
@reactive.when_not('config.complete')
def config_changed(domain):
    with charm.provide_charm_instance() as kldap_charm:
        if kldap_charm.configuration_complete():
            flags.set_flag('config.complete')


@reactive.when('domain-backend.connected')
@reactive.when('domain-name-configured')
@reactive.when('config.complete')
@reactive.when_not('config.rendered')
def render_config(domain):
    with charm.provide_charm_instance() as kldap_charm:
        kldap_charm.render_config(domain.trigger_restart)
        flags.set_flag('config.rendered')


@reactive.when_not('always.run')
def assess_status():
    with charm.provide_charm_instance() as kldap_charm:
        kldap_charm.assess_status()
