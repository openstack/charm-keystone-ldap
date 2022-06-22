# Overview

[Keystone][keystone-upstream] is the identity service used by OpenStack for
authentication and high-level authorisation.

The keystone-ldap subordinate charm provides an LDAP domain backend for
integrating a Keystone v3 deployment with an LDAP based authentication system.
It is used in conjunction with the [keystone][keystone-charm] charm.

An external LDAP server is a prerequisite.

# Usage

## Configuration

This section covers common and/or important configuration options. See file
`config.yaml` for the full list of options, along with their descriptions and
default values. See the [Juju documentation][juju-docs-config-apps] for details
on configuring applications.

#### `domain-name`

The `domain-name` option provides the name of the Keystone domain for which a
domain-specific configuration will be generated. The default value is the name
of the application (e.g. the default being 'keystone-ldap'). The keystone charm
will automatically create a domain to support the backend once keystone-ldap is
deployed.

#### `ldap-config-flags`

The `ldap-config-flags` option allows for arbitrary LDAP server settings to be
passed to Keystone.

> **Important**: This option should only be considered when an equivalent charm
  option is not available. The explicit charm option takes precedence if
  identical parameters are set.

Such a configuration can be added post-deploy by using a string of comma
delimited key=value pairs:

    juju config keystone-ldap \
        ldap-config-flags="user_id_attribute=cn,user_name_attribute=cn"

For a more complex environment, such as Microsoft Active Directory, a YAML file
is normally used (e.g. `ldap-config.yaml`). For example:

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

In the above, values are given as a JSON-like string. A combination of double
quotes and braces are needed around the string, and single quotes are used for
individual complex values.

A file-based configuration can be added post-deploy in this way:

    juju config keystone-ldap --file ldap-config.yaml

#### `ldap-password`

The `ldap-password` option supplies the password associated with the LDAP user
(given by option `ldap-user`). For anonymous binding, leave ldap-password and
ldap-user blank.

#### `ldap-server`

The `ldap-server` option states the LDAP URL(s) of the Keystone LDAP identity
backend. Example values:

    ldap://10.10.10.10/
    ldaps://10.10.10.10/
    ldap://example.com:389,ldaps://ldaps.example.com:636

> **Note**: An `ldap://` URL will result in mandatory StartTLS usage if either
  the charm's `tls-ca-ldap` option has been specified or if the 'certificates'
  relation is present.

When the LDAP server is an Active Directory it is best practice to connect to
its [Global Catalog][microsoft-gc] ports (3268 and 3269) instead of the
standard ports (389 and 636):

    ldap://active-directory-host.com:3268/
    ldaps://active-directory-host.com:3269/

There are several reasons for this:

1. Objects can be searched without specifying the domain name. This can be
   useful for multi-(AD)domain user management.
1. Entries are returned with a single query rather than requiring Keystone to
   chase referrals. The latter can lead to connectivity issues if the referred
   server is not accessible (due to firewalls, routing, DNS resolution, etc.).
1. The Global Catalog is an optimised subsection of all of the data
   within the AD services forest. This results in faster query responses.
1. The Global Catalog is a single-source, multi-master high availability
   endpoint for the AD forest.

One reason for not doing so is when user management is being keyed off of
fields that are not populated to the Global Catalog.

#### `ldap-suffix`

The `ldap-suffix` option states the LDAP server suffix to be used by Keystone.

#### `ldap-user`

The `ldap-user` option states the username (Distinguished Name) used to bind to
the LDAP server (given by option `ldap-server`). For anonymous binding, leave
ldap-user and ldap-password blank.

# Deployment

Let file `keystone-ldap.yaml` contain the deployment configuration:

```yaml
    keystone-ldap:
        ldap-server:"ldap://10.10.10.10/"
        ldap-user:"cn=admin,dc=test,dc=com"
        ldap-password:"password"
        ldap-suffix:"dc=test,dc=com"
```

If applicable, the `ldap-config-flags` option can be added:

```yaml
    keystone-ldap:
        ldap-server:"ldap://10.10.10.10/"
        ldap-user:"cn=admin,dc=test,dc=com"
        ldap-password:"password"
        ldap-suffix:"dc=test,dc=com"
        ldap-config-flags: "{
                user_tree_dn: 'DC=dc1,DC=ad,DC=example,DC=com',
                ...,
                }"
```

Deploy keystone (requesting API v3 explicitly) and keystone-ldap:

    juju deploy --config preferred-api-version=3 keystone
    juju deploy --config keystone-ldap.yaml keystone-ldap
    juju add-relation keystone-ldap:domain-backend keystone:domain-backend

## Further reading

The below topics are covered in the upstream OpenStack documentation.

* [Keystone and LDAP integration][upstream-os-docs-keystone-ldap]: Offers more
  guidance on integrating Keystone with LDAP.

* [Keystone LDAP configuration
  options][upstream-os-docs-keystone-ldap-options]: Provides a definitive list
  of LDAP-related Keystone configuration options, including default values.

# Bugs

Please report bugs on [Launchpad][lp-bugs-charm-keystone-ldap].

For general charm questions refer to the [OpenStack Charm Guide][cg].

<!-- LINKS -->

[cg]: https://docs.openstack.org/charm-guide
[keystone-upstream]: https://docs.openstack.org/keystone/latest/
[keystone-charm]: https://jaas.ai/keystone
[juju-docs-config-apps]: https://juju.is/docs/configuring-applications
[lp-bugs-charm-keystone-ldap]: https://bugs.launchpad.net/charm-keystone-ldap/+filebug
[upstream-os-docs]: https://docs.openstack.org
[upstream-os-docs-keystone-ldap]: https://docs.openstack.org/keystone/latest/admin/configuration.html#integrate-identity-back-end-with-ldap
[upstream-os-docs-keystone-ldap-options]: https://docs.openstack.org/keystone/latest/configuration/config-options.html#ldap
[microsoft-gc]: https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-2000-server/cc978012(v=technet.10)
