# Overview

This subordinate charm provides ...


# Usage

With the OpenStack nova-compute and neutron-gateway charms:

    juju deploy ...
    juju deploy neutron-gateway
    juju add-relation nova-compute ...
    juju add-relation neutron-gateway ...

# Configuration Options

This charm will optionally configure the local ip address of the OVS instance to something other than the 'private-address' provided by Juju:

    juju set ... os-data-network=10.20.3.0/21


# Restrictions


