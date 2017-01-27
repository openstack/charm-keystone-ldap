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

by default, the name of the application ('keystone-ldap') is the name of
the domain for which a domain specific configuration will be configured;
you can change this using the domain-name option:

    juju config keystone-ldap domain-name="myorganisationname"

The keystone charm will automatically create a domain to support the backend
once deployed.
