import yaml
import json
import logging
from ansible.inventory.manager import InventoryManager as AnsibleInventoryManager
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

yaml.SafeDumper.add_representer(
    type(None),
    lambda dumper, value: dumper.represent_scalar(u'tag:yaml.org,2002:null', '')
  )

class InventoryManager:
    def __init__(self, inventory_file):
        self.dl = DataLoader()
        self.inventory_file = inventory_file
        self.inventory = AnsibleInventoryManager(
            loader=self.dl,
            sources=inventory_file,
        )
        self.variable_manager = VariableManager(loader=self.dl, inventory=self.inventory)

        # Print inventory data
        logger.info(f"Inventory data:\n {self.inventory}")
        logger.info(f"Hosts:\n {self.inventory.get_hosts()}")
        logger.info(f"Groups:\n {self.inventory.list_groups()}")

    def save(self):
        """Save the modified inventory back to the YAML file."""
        inventory_dict = {}

        inventory_dict['all'] = {
            'hosts': {},
            'children': {}
        }

        groups_hosts_dict = self.inventory.get_groups_dict()

        all_hosts = groups_hosts_dict.get('all', [])
        for host in all_hosts:
            if host is None:
                continue

            host_entry = self.inventory.get_host(host)
            if host_entry is None:
                continue

            hostvars = host_entry.vars
            hostvars.pop('inventory_file', None)
            hostvars.pop('inventory_dir', None)
            inventory_dict['all']['hosts'][host] = {**hostvars}


        for group, hosts in groups_hosts_dict.items():
            if group in ["all", "ungrouped"]:
                continue

            inventory_dict['all']['children'][group] = {
                'hosts': {},
            }

            for host in hosts:
                inventory_dict['all']['children'][group]['hosts'][host] = None

        logger.info(f"Data:\n {inventory_dict}")

        # with open(self.inventory_file, "w") as f:
        #     yaml.dump(inventory_dict, f, default_flow_style=False)

        # convert to json intermediate representation to avoid metadata issues
        json_data = json.loads(json.dumps(inventory_dict))
        with open(self.inventory_file, "w") as f:
            yaml.safe_dump(json_data, f, default_flow_style=False)

    def add_host(self, host_name, groups, ip, mac, port, ansible_user):
        """Add a new host to the inventory."""
        self.inventory.refresh_inventory()
        self.inventory.add_group('all')

        if host_name in [str(e) for e in self.inventory.get_hosts()]:
            logger.warning(f"Host '{host_name}' already exists in the inventory.")
            return

        # Add the host to the specified groups
        self.inventory.add_host(host_name, group="all", port=port)
        for group in groups:
            if group in ["all", "ungrouped", ""]:
                continue

            logger.info(f"Adding host '{host_name}' to group '{group}'")

            self.inventory.add_group(group)
            self.inventory.add_host(host_name, group)

        self.inventory.get_host(host_name).set_variable('ansible_host', ip)
        self.inventory.get_host(host_name).set_variable('ansible_user', ansible_user)
        self.inventory.get_host(host_name).set_variable('ansible_port', port)
        self.inventory.get_host(host_name).set_variable('primary_mac', mac)

        # for key, value in hostvars.items():
        #     self.inventory.get_host(host_name).set_variable(key, value)

        self.save()

    def remove_host(self, host_name):
        """Remove a host from the inventory."""
        self.inventory.refresh_inventory()
        # Remove the host
        host = self.inventory.get_host(host_name)
        if host is None:
            logger.warning(f"Host '{host_name}' not found in the inventory.")
            return

        self.inventory._inventory.remove_host(host)

        # print all groups and the host in each group
        for group in self.inventory.groups:
            logger.info(f"Group: {group}")
            logger.info(f"Hosts: {self.inventory.get_groups_dict()[group]}")

        groups_to_remove = [group for group in self.inventory.groups if not self.inventory.get_groups_dict()[group]]
        for group in groups_to_remove:
            self.inventory._inventory.remove_group(group)

        logger.info(f"Host '{host_name}' removed from the inventory.")

        self.save()
