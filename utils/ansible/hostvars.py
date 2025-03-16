from abc import ABC, abstractmethod
from pathlib import Path
import yaml
import logging
from models.state_model import StateModel
from models.storage_model import StorageModel
from models.system_model import SystemModel
from utils.ansible.manager import AnsibleManager, AnsibleObject
from utils.repo import RepoManager
from utils.dict_utils import ReplacementType, deep_merge
from enum import Enum

# Setup basic logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HostvarType(Enum):
    STATE = "state"
    STORAGE = "storage"
    SYSTEM = "system"
    ANY = "any"

class Hostvars(AnsibleObject):
    """Handles in-memory hostvars data."""
    def __init__(self, data: dict = None):
        self.data = data or {}

    def update(self, host: str, var_type: HostvarType, replace_type: ReplacementType,  new_data: dict) -> None:
        """Update hostvars for a given host and section."""

        host_data = self.data.setdefault(host, {})

        logger.info(f"Passed params: host={host}, var_type={var_type}, new_data={new_data}")

        if replace_type == ReplacementType.OVERRIDE:
            if var_type == HostvarType.ANY:
                self.data[host] = new_data
            else:
                host_data[var_type.value] = new_data

        elif replace_type == ReplacementType.IN_PLACE:
            if var_type == HostvarType.ANY:
                host_data.update(deep_merge(host_data, new_data))
            else:
                logger.info(f"Host data: {host_data}")
                host_data[var_type.value] = deep_merge(host_data.get(var_type.value, {}), new_data)
                logger.info(f"Updated host data: {host_data}")

    def get(self, host: str) -> dict:
        """Return hostvars for a specific host."""
        return self.data.get(host, {})

    def get_all(self) -> dict:
        """Return all hostvars data."""
        return self.data
    
    def get_section_by_host(self, host: str, section: HostvarType) -> dict:
        """Return a specific section of hostvars for a given host."""
        if section == HostvarType.ANY:
            return self.get(host)

        return self.data.get(host, {}).get(section.value, {})

    def get_all_by_section(self, section: HostvarType) -> dict:
        """Return a specific section of hostvars for all hosts."""
        if section == HostvarType.ANY:
            return self.get_all()

        return {host: data.get(section.value, {}) for host, data in self.get_all().items()}


class HostvarsManager(AnsibleManager):
    """
    Manages hostvars stored as YAML files in a repository.
    Instead of caching the hostvars on initialization, we reload them for every operation.
    """
    def __init__(self, repo: RepoManager):
        self.repo = repo

    def load(self) -> Hostvars:
        """Pull the latest repo data and load all YAML files as hostvars."""
        self.repo.pull()
        hostvars_data = {}
        for hostvar_file in self.repo.repo_path.glob("*.yml"):
            host = hostvar_file.stem
            try:
                with open(hostvar_file, "r") as f:
                    hostvars_data[host] = yaml.safe_load(f) or {}
            except yaml.YAMLError as e:
                logger.error(f"Error loading {hostvar_file}: {e}")
                hostvars_data[host] = {}
        logger.debug("Refreshed hostvars from repo.")
        return Hostvars(hostvars_data)

    def save(self, hostvars: Hostvars, commit_msg:str = "Update hostvars", batch_updates: bool = False) -> None:
        """
        Save all hostvars back to the repository and push changes.
        This method writes the updated data back to disk and commits it.
        """
        for host, data in hostvars.get_all().items():
            hostvar_file = self.repo.repo_path / f"{host}.yml"
            try:
                with open(hostvar_file, "w") as f:
                    yaml.safe_dump(data, f)
                logger.debug(f"Saved hostvars for host '{host}' to {hostvar_file}.")
            except Exception as e:
                logger.error(f"Error saving {hostvar_file}: {e}")
                raise

        if batch_updates:
            return

        self.repo.commit_and_push_all(commit_msg)
        logger.debug("Committed and pushed all hostvars changes.")

    def create(self, host: str, storage: StorageModel, system: SystemModel) -> None:
        """Create a new hostvars file for a given host."""
        hostvar_file = self.repo.repo_path / f"{host}.yml"
        if hostvar_file.exists():
            logger.warning(f"Hostvars file for '{host}' already exists.")
            return

        # Initialize state with all fields
        self.update(host, HostvarType.SYSTEM, ReplacementType.OVERRIDE, system.model_dump(), batch_updates=True)
        self.update(host, HostvarType.STATE, ReplacementType.OVERRIDE, StateModel().model_dump(), batch_updates=True)
        self.update(host, HostvarType.STORAGE, ReplacementType.OVERRIDE, storage.model_dump(), commit_msg="Create data", batch_updates=False)

    def delete(self, host: str) -> None:
        """Delete the hostvars file for a given host."""
        hostvar_file = self.repo.repo_path / f"{host}.yml"
        if not hostvar_file.exists():
            logger.warning(f"Hostvars file for '{host}' does not exist.")
            return

        try:
            hostvar_file.unlink()
            logger.debug(f"Deleted hostvars file for '{host}'.")
        except Exception as e:
            logger.error(f"Error deleting {hostvar_file}: {e}")
            raise

        self.repo.commit_and_push_all("Delete hostvars")

    def update(self, host: str, var_type: HostvarType, replace_type: ReplacementType, new_data: dict, commit_msg:str = "Update hostvars", batch_updates: bool = False) -> None:
        """
        Reload the latest hostvars, update the data, and then save.
        This minimizes the risk of working with outdated data.
        """
        # Refresh data
        logger.info(f"Update params: host={host}, var_type={var_type}, new_data={new_data}")
        hostvars = self.load()
        try:
            hostvars.update(host, var_type, replace_type, new_data)
        except Exception as e:
            logger.error(f"Failed to update hostvars for '{host}': {e}")
            raise

        # Save updated hostvars
        self.save(hostvars, commit_msg, batch_updates)

    def get(self, host: str) -> dict:
        """Reload and return hostvars for a specific host."""
        hostvars = self.load()
        return hostvars.get(host)

    def get_all(self) -> dict:
        """Reload and return all hostvars."""
        hostvars = self.load()
        return hostvars.get_all()

    def get_section_by_host(self, host: str, section: HostvarType) -> dict:
        """Reload and return a specific section of hostvars for a given host."""
        hostvars = self.load()
        return hostvars.get_section_by_host(host, section)

    def get_all_by_section(self, section: HostvarType) -> dict:
        """Reload and return a specific section of hostvars for all hosts."""
        hostvars = self.load()
        return hostvars.get_all_by_section(section)
