# Overview

This subordinate charm provides a LDAP domain backend for integrating a
Keystone v3 deployment with an external LDAP based authentication system.

# Usage

Use this charm with the Keystone charm, running with preferred-api-version=3:

    juju deploy keystone
    juju config keystone preferred-api-version=3
    juju deploy keystone-ldap
    juju add-relation keystone-ldap keystone

# Configuration Options

LDAP configuration is provided to this charm via configuration options:

    juju config keystone-ldap ldap-server="ldap://10.10.10.10/" \
                ldap-user="cn=admin,dc=test,dc=com" \
                ldap-password="password" \
                ldap-suffix="dc=test,dc=com"

By default, the name of the application ('keystone-ldap') is the name of
the domain for which a domain specific configuration will be configured;
you can change this using the domain-name option:

    juju config keystone-ldap domain-name="myorganisationname"

The keystone charm will automatically create a domain to support the backend
once deployed.

LDAP configurations can be quite complex. The ldap-config-flags configuration
option provides the mechanism to pass arbitrary configuration options to
keystone in order to handle any given LDAP backend's specific requirements.

For very simple LDAP configurations a string of comma delimited key=value pairs
can be used:

    juju config keystone-ldap \
        ldap-config-flags="user_id_attribute=cn,user_name_attribute=cn"

For more complex configurations such as working with Active Directory use
a configuration yaml file.

    juju config keystone-ldap --file flags-config.yaml

Where flags-config.yaml has the contents similar to the following. The
ldap-config-flags value uses a json like string for the key value pairs:

keystone-ldap:
    ldap-config-flags: "{
            user_tree_dn: 'DC=dc1,DC=ad,DC=example,DC=com',
            user_filter: '(memberOf=CN=users-cn,OU=Groups,DC=dc1,DC=ad,DC=example,DC=com)',
            query_scope: sub,
            user_objectclass: person,
            user_name_attribute: sAMAccountName,
            user_id_attribute: sAMAccountName,
            user_mail_attribute: mail,
            user_enabled_attribute: userAccountControl,
            user_enabled_mask: 2,
            user_enabled_default: 512,
            user_attribute_ignore: 'password,tenant_id,tenants',
            user_allow_create: False,
            user_allow_update: False,
            user_allow_delete: False,
            }"

Note: The double quotes and braces around the whole string. And single quotes
around the individual complex values.

Please refer to the OpenStack docs at [Keystone and LDAP integration page](https://docs.openstack.org/keystone/latest/admin/configuration.html#integrate-identity-back-end-with-ldap)
for more information on how to set up the config options and at [Keystone LDAP config options reference](https://docs.openstack.org/keystone/latest/configuration/config-options.html#ldap)
for more information on their default values.

# Bugs

Please report bugs on [Launchpad](https://bugs.launchpad.net/charm-keystone-ldap/+filebug).

For general questions please refer to the OpenStack [Charm Guide](http://docs.openstack.org/developer/charm-guide/).
