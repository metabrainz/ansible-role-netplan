from collections.abc import Mapping
from copy import deepcopy

from ansible.errors import AnsibleFilterTypeError
from ansible.plugins.filter.core import flatten, to_nice_yaml


def render_netplan_config(config, version=2, renderer=None):
    if not isinstance(config, Mapping):
        raise AnsibleFilterTypeError("render_netplan_config requires a dictionary, got %s instead" % type(config))

    new_config = {
        "network": {
            "version": version
        },
    }

    if renderer:
        new_config["network"]["renderer"] = renderer

    for device_type, definition_map in config.items():
        # skip empty definition maps
        if not definition_map:
            continue

        new_definition_map = {}

        for configuration_id, definition in definition_map.items():
            # skip empty definitions
            if not definition:
                continue

            # duplicate `definition` to avoid modifying the reference
            # deepcopy is required because `definition` can include nested dicts and lists
            new_definition = deepcopy(definition)

            # a special key named "_interface" can be specified to override the configuration ID
            # this is required because dict keys cannot be templated in Ansible
            configuration_id = new_definition.pop("_interface", configuration_id)

            # skip this definition if it is empty after removing the `_interface` key
            if not new_definition:
                continue

            addresses = new_definition.pop("addresses", None)
            if isinstance(addresses, list) and addresses:
                # flatten addresses to support nested lists
                addresses = flatten(addresses, levels=2)
            # skip empty values
            if addresses:
                new_definition["addresses"] = addresses

            # add the definition to the map providing it is not empty
            if new_definition:
                new_definition_map[configuration_id] = new_definition

        # skip empty definition maps
        if new_definition_map:
            new_config["network"][device_type] = new_definition_map

    return to_nice_yaml(new_config, indent=2)


def get_netplan_interfaces(config, device_type="ethernets"):
    if not isinstance(config, Mapping):
        raise AnsibleFilterTypeError("get_netplan_interfaces requires a dictionary, got %s instead" % type(config))

    if device_type not in config:
        return []

    retval = []
    for configuration_id, definition in config[device_type].items():
        interface = definition.get("_interface", configuration_id)

        if interface:
            retval.append(interface)

    return retval


class FilterModule(object):

    def filters(self):
        return {
            "get_netplan_interfaces": get_netplan_interfaces,
            "render_netplan_config": render_netplan_config,
        }
