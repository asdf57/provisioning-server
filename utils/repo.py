
import logging
from pathlib import Path
from git import Repo
from returns.result import Failure, Result, Success

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RepoManager:
    def __init__(self, ssh_url: str, repo_path: Path):
        self.ssh_url = ssh_url
        self.repo_path = repo_path
        self.repo = self.clone_repo(ssh_url, repo_path)

    @staticmethod
    def clone_repo(ssh_url: str, repo_path: Path) -> Repo:
        try:
            if repo_path.exists():
                return Repo(repo_path)
            return Repo.clone_from(ssh_url, repo_path)
        except Exception as e:
            logger.error(f"Failed to clone repo: {e}")
            exit(1)

    def is_file_exists(self, file_path: Path) -> bool:
        return file_path.exists()

    def pull(self) -> Result[None, str]:
        try:
            self.repo.remotes.origin.pull()
            logger.info("Pulled changes")
            return Success(None)
        except Exception as e:
            return Failure("Failed to pull changes")

    def commit_and_push_all(self, commit_msg: str) -> Result[None, str]:
        try:
            self.repo.git.add(".")
            if self.repo.is_dirty(untracked_files=True):
                self.repo.index.commit(commit_msg)
                self.repo.remotes.origin.push()
            
            return Success(None)
        except Exception as e:
            return Failure("Failed to commit or push changes")