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

import charmhelpers.contrib.openstack.vaultlocker as vaultlocker
import charmhelpers.core.unitdata as unitdata

from socket import gethostname

charm.use_defaults(
    'charm.installed',
    'update-status',
    'upgrade-charm',
)

# if config has been changed we need to re-evaluate flags
# config.changed is set and cleared (atexit) in layer-basic
flags.register_trigger(when='config.changed',
                       clear_flag='config.rendered')
flags.register_trigger(when='config.changed',
                       clear_flag='config.complete')

VAULT_CTX_KEY = 'vault.kv.context'


def _store_vault_context(ctxt):
    db = unitdata.kv()
    db.set(VAULT_CTX_KEY, ctxt)
    db.flush()


@reactive.when_not('secrets-storage.available')
@reactive.when('secrets-storage.connected')
def secrets_storage_connected():
    """Request access to vault once relation is up."""
    secrets = reactive.endpoint_from_flag('secrets-storage.connected')
    hookenv.log('Requesting access to vault ({})'.format(secrets.vault_url),
                level=hookenv.INFO)

    try:
        addr = hookenv.network_get_primary_address('secrets-storage')
    except (hookenv.NoNetworkBinding, NotImplementedError):
        addr = hookenv.unit_private_ip()

    for relation in secrets.relations:
        relation.to_publish['secret_backend'] = 'charm-keystone-ldap'
        relation.to_publish['access_address'] = addr
        relation.to_publish['hostname'] = gethostname()
        relation.to_publish['isolated'] = False
        relation.to_publish['unit_name'] = hookenv.local_unit()


@reactive.when('secrets-storage.available')
def secrets_storage_available():
    """Unwrap secret-id and cache vault context for render."""
    vault_ctxt = vaultlocker.VaultKVContext(
        secret_backend='charm-keystone-ldap')()
    if vault_ctxt:
        _store_vault_context(vault_ctxt)
        flags.clear_flag('config.rendered')


@reactive.when_not('secrets-storage.connected')
def secrets_storage_departed():
    """Clear cached vault context if relation drops."""
    db = unitdata.kv()
    db.unset(VAULT_CTX_KEY)
    db.flush()
    flags.clear_flag('config.rendered')


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
