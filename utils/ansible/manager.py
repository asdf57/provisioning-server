

from abc import ABC, abstractmethod
from enum import Enum

from utils.repo import RepoManager


class AnsibleObject:
    pass

class AnsibleManager(ABC):
    def __init__(self, repo: RepoManager):
        self.repo = repo

    @abstractmethod
    def load(self) -> AnsibleObject:
        """
        Pull the latest repo data and load all YAML files as hostvars.
        """
        pass

    @abstractmethod
    def save(self, data: AnsibleObject) -> None:
        """
        Save the repository and push changes.
        """
        pass
