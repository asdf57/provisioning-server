import yaml
import json
import logging
from pathlib import Path

from ansible.inventory.manager import InventoryManager as AnsibleInventoryManager
from ansible.parsing.dataloader import DataLoader

from utils.ansible.manager import AnsibleManager, AnsibleObject
from utils.repo import RepoManager


logger = logging.getLogger(__name__)

yaml.SafeDumper.add_representer(
    type(None),
    lambda dumper, value: dumper.represent_scalar(u'tag:yaml.org,2002:null', '')
)

class Inventory(AnsibleObject):
    """
    Domain model that wraps the internal Ansible InventoryManager.
    It delegates host/group operations to the internal manager while
    exposing domain-specific methods.
    """
    def __init__(self, inventory_file: Path):
        self.data_loader = DataLoader()
        self.inventory_file = inventory_file
        self.inventory = AnsibleInventoryManager(loader=self.data_loader, sources=[str(inventory_file)])

    def add_host(self, host_name: str, groups: list, ip: str, mac: str, port: int, ansible_user: str) -> None:
        """
        Add a new host to the inventory. Uses the internal methods to:
          - Add the host to the default 'all' group.
          - Set host variables.
          - Add the host to additional groups.
        Raises a ValueError if the host already exists.
        """
        self.inventory.refresh_inventory()
        self.inventory.add_group('all')

        if host_name in [h.name for h in self.inventory.get_hosts()]:
            raise ValueError(f"Host '{host_name}' already exists.")

        # Add host to the default 'all' group.
        self.inventory.add_host(host_name, group="all", port=port)
        host_entry = self.inventory.get_host(host_name)
        host_entry.set_variable("ansible_host", ip)
        host_entry.set_variable("ansible_user", ansible_user)
        host_entry.set_variable("ansible_port", port)
        host_entry.set_variable("primary_mac", mac)
        
        # Add host to each additional group.
        for group in groups:
            if group in ["all", "ungrouped", ""]:
                continue

            self.inventory.add_group(group)
            self.inventory.add_host(host_name, group)
            logger.debug(f"Added host '{host_name}' to group '{group}'")

    def remove_host(self, host_name):
        """Remove a host from the inventory."""
        self.inventory.refresh_inventory()

        host = self.inventory.get_host(host_name)
        if host is None:
            logger.warning(f"Host '{host_name}' not found in the inventory.")
            return

        self.inventory._inventory.remove_host(host)

        for group in self.inventory.groups:
            logger.info(f"Group: {group}")
            logger.info(f"Hosts: {self.inventory.get_groups_dict()[group]}")

        groups_to_remove = [group for group in self.inventory.groups if not self.inventory.get_groups_dict()[group]]
        for group in groups_to_remove:
            self.inventory._inventory.remove_group(group)

        logger.info(f"Host '{host_name}' removed from the inventory.")

    def update_host_vars(self, host_name: str, new_vars: dict) -> None:
        """
        Update host variables for an existing host.
        Raises a ValueError if the host is not found.
        """
        self.inventory.refresh_inventory()

        host_entry = self.inventory.get_host(host_name)
        if not host_entry:
            raise ValueError(f"Host '{host_name}' not found.")
        for key, value in new_vars.items():
            host_entry.set_variable(key, value)
        logger.debug(f"Updated host '{host_name}' with variables: {new_vars}")

    def to_dict(self) -> dict:
        """
        Convert the internal inventory state into a dictionary structure of the form:
            {
                "all": {
                    "hosts": { ... },
                    "children": { ... }
                }
            }
        This is useful for persisting the inventory to disk.
        """
        logger.info(f"Existing hosts: {self.inventory.get_hosts()}")

        inventory_dict = {"all": {"hosts": {}, "children": {}}}
        groups_dict = self.inventory.get_groups_dict()

        # Populate the 'hosts' section from the "all" group.
        for host in groups_dict.get("all", []):
            host_entry = self.inventory.get_host(host)
            if host_entry:
                hostvars = host_entry.vars.copy()
                hostvars.pop("inventory_file", None)
                hostvars.pop("inventory_dir", None)
                inventory_dict["all"]["hosts"][host] = hostvars

        # Populate the 'children' groups.
        for group, hosts in groups_dict.items():
            if group in ["all", "ungrouped"]:
                continue
            inventory_dict["all"]["children"][group] = {"hosts": {}}
            for host in hosts:
                inventory_dict["all"]["children"][group]["hosts"][host] = None

        return inventory_dict


class InventoryManager(AnsibleManager):
    """
    Handles loading and saving the Inventory domain model from/to a YAML file
    in the repository. It leverages the Inventory domain model (which itself uses
    the internal Ansible inventory methods) to perform domain operations.
    """
    def __init__(self, repo: RepoManager):
        super().__init__(repo)
        self.inventory_file = self.repo.repo_path / "inventory.yml"

    def load(self) -> Inventory:
        """
        Pull the latest repository data and instantiate the Inventory domain model.
        """
        self.repo.pull()
        inventory = Inventory(inventory_file=self.inventory_file)
        logger.debug("Inventory loaded via internal Ansible InventoryManager.")
        return inventory

    def save(self, inventory: Inventory) -> None:
        """
        Save the Inventory domain model by converting it to a dictionary, writing it
        to the YAML file, and then committing/pushing changes via the repository.
        """
        inventory_dict = inventory.to_dict()
        json_data = json.loads(json.dumps(inventory_dict))
        logger.info(f"Inventory: {json_data}")
        with open(self.inventory_file, "w") as f:
            yaml.safe_dump(json_data, f, default_flow_style=False)
        self.repo.commit_and_push_all("Update inventory")
        logger.info("Inventory saved and changes pushed.")

    def add_host(self, host_name: str, groups: list, ip: str, mac: str, port: int, ansible_user: str) -> None:
        """
        Load the current inventory, delegate the host addition to the domain model,
        and save the updated inventory.
        """
        inventory = self.load()
        try:
            inventory.add_host(host_name, groups, ip, mac, port, ansible_user)
            logger.info(f"Host '{host_name}' added successfully.")
        except ValueError as e:
            logger.warning(e)
            return

        self.save(inventory)

    def remove_host(self, host_name: str) -> None:
        """
        Load the current inventory, delegate the host removal to the domain model,
        and save the updated inventory.
        """
        inventory = self.load()
        try:
            inventory.remove_host(host_name)
            logger.info(f"Host '{host_name}' removed successfully.")
        except ValueError as e:
            logger.warning(e)
            return
        self.save(inventory)

    def update_host_vars(self, host_name: str, new_vars: dict) -> None:
        """
        Load the current inventory, delegate the host variable update to the domain model,
        and save the updated inventory.
        """
        inventory = self.load()
        try:
            inventory.update_host_vars(host_name, new_vars)
            logger.info(f"Host variables for '{host_name}' updated successfully.")
        except ValueError as e:
            logger.warning(e)
            return
        self.save(inventory)
