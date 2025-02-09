import yaml
import logging
from utils.repo import RepoManager
from models.hostvars_model import HostvarsModel
from models.state_model import StateModel
from models.storage_model import StorageModel
from returns.maybe import Maybe, Nothing, Some
from returns.pipeline import is_successful
from returns.result import Failure, Result, Success
from enum import Enum

from utils.validator import ValidationMode, validate_model

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HostvarType(Enum):
    STATE = "state"
    STORAGE = "storage"
    ANY = "any"

class Hostvars:
    def __init__(self, hostvar_data_repo: RepoManager):
        self.hostvar_data_repo = hostvar_data_repo

    def update(self, host: str, data: dict):

        hostvar_file = self.hostvar_data_repo.repo_path / f"{host}.yml"
        if not hostvar_file.exists():
            return Failure(f"Hostvar file for {host} does not exist")

        with open(hostvar_file, "r") as f:
            hostvar_data = yaml.safe_load(f)

        hostvar_data.update(data)

        # logger.info(f"Updating hostvars for {host}: {hostvar_data}")

        with open(hostvar_file, "w") as f:
            yaml.safe_dump(hostvar_data, f)

        return Success(hostvar_data)
    
    def update_hostvars(self, host: str, type: HostvarType, validation_mode: ValidationMode, data: dict):
        self.hostvar_data_repo.pull()

        try:
            hostvar_data = self.get(host).unwrap()
            if type == HostvarType.STATE:
                logger.info(f"Updating state for {host}: {data}")
                parsed_data = validate_model(StateModel, data, validation_mode)
                return self.update(host, {'state': parsed_data.model_dump(exclude_none=True)})
            elif type == HostvarType.STORAGE:
                parsed_data = validate_model(StorageModel, data, validation_mode)
                updated_storage = {**hostvar_data['storage'], **parsed_data.model_dump(exclude_none=True)}
                return self.update(host, {'storage': updated_storage})
            elif type == HostvarType.ANY:
                return self.update(host, data)
            else:
                return Failure("Invalid hostvar type")
        except Exception as e:
            return Failure(f"Failed to update hostvars: {e}")
        
    def get(self, host: str):
        # Always pull first to avoid conflicts
        self.hostvar_data_repo.pull()

        hostvar_file = self.hostvar_data_repo.repo_path / f"{host}.yml"
        if not hostvar_file.exists():
            return Failure(f"Hostvar file for {host} does not exist")

        with open(hostvar_file, "r") as f:
            hostvar_data = yaml.safe_load(f) or {}

        return Success(hostvar_data)
    
    def get_section(self, host: str, section: HostvarType):
        # Always pull first to avoid conflicts
        self.hostvar_data_repo.pull()

        try:
            hostvar_data = {}
            hostvar_file = self.hostvar_data_repo.repo_path / f"{host}.yml"
            if not hostvar_file.exists():
                return Failure(f"Hostvar file for {host} does not exist")
            
            with open(hostvar_file, "r") as f:
                hostvar_data = yaml.safe_load(f) or {}
            
            data = hostvar_data.get(section.value, {})

            return Success(data)
        except Exception as e:
            return Failure(f"Failed to get section: {e}")

    def save(self):
        self.hostvar_data_repo.commit_and_push_all("Update hostvars")
