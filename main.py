import functools
import logging
import traceback
from pathlib import Path

import yaml
from flask import Flask, jsonify, request
from returns.pipeline import is_successful
from pydantic import BaseModel, Field, IPvAnyAddress, ValidationError
from utils.inventory import InventoryManager
from utils.repo import RepoManager
from utils.hostvars import Hostvars, HostvarType
from models.inventory_model import *
from models.storage_model import *
from models.entry_model import *
from dataclasses import dataclass

from utils.validator import ValidationMode

"""Logging configuration"""
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

"""Configuration for the application"""
REPO_DIR: Path = Path("/app/repos")
REPO_SSH: str = "git@github.com:asdf57/hostvar_data.git"
INVENTORY_REPO_SSH: str = "git@github.com:asdf57/inventory.git"
HOSTVAR_REPO_PATH = REPO_DIR / "hostvar_data"
INVENTORY_REPO_PATH = REPO_DIR / "inventory" / "inventory.yml"

"""Global variables"""
try:
    hostvar_data_repo = RepoManager(REPO_SSH, HOSTVAR_REPO_PATH)
    inventory_repo = RepoManager(INVENTORY_REPO_SSH, INVENTORY_REPO_PATH)
    inventory = InventoryManager(str(INVENTORY_REPO_PATH))
    hostvars = Hostvars(hostvar_data_repo)
except Exception as e:
    logger.error(f"Failed to initialize app: {e}")
    exit(1)

class FlaskApp:
    """Main Flask application class."""
    def __init__(self):
        self.app = Flask(__name__)
        self._setup_routes()

    def _setup_routes(self):
        """Setup the routes for the application."""
        self.app.route('/hostvars', methods=['POST'])(post_hostvars)
        self.app.route('/state', methods=['POST'])(post_state)
        self.app.route('/state/<host>', methods=['GET'])(get_state)
        # self.app.route('/server', methods=['POST'])(post_server)
        self.app.route('/inventory', methods=['POST'])(post_inventory)
        self.app.route('/inventory', methods=['DELETE'])(delete_inventory)
        self.app.route('/storage', methods=['POST'])(post_storage)
        self.app.route('/storage', methods=['PUT'])(put_storage)

    def run(self, host: str, port: int):
        """Run the Flask application."""
        self.app.run(host=host, port=port)

def handle_exceptions(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"Exception occurred: {tb}")
            return jsonify({"status": "error", "message": str(e), "traceback": tb}), 500

def update_hostvars(data, hostvar_type: HostvarType, validation_mode: ValidationMode):
    for host, hostvar_data in data.items():
        res = hostvars.update_hostvars(host, hostvar_type, validation_mode, hostvar_data)
        if not is_successful(res):
            return jsonify({"status": "error", "message": f"Failed to update hostvars: {res.failure()}"}), 500

    hostvars.save()

    return jsonify({"status": "success", "message": "Hostvars updated"}), 200


# Flask Routes
@handle_exceptions
def post_hostvars():
    return update_hostvars(request.get_json(), HostvarType.ANY, ValidationMode.ALL)
    # data = request.get_json()

    # for host, hostvar_data in data.items():
    #     res = hostvars.update_hostvars(host, HostvarType.ANY, ValidationMode.ALL, hostvar_data)
    #     if not is_successful(res):
    #         return jsonify({"status": "error", "message": f"Failed to update hostvars: {res.failure()}"}), 500

    # hostvars.save()

    # return jsonify({"status": "success", "message": "Hostvars updated"}), 200

@handle_exceptions
def post_state():
    return update_hostvars(request.get_json(), HostvarType.STATE, ValidationMode.FULL)
    # return jsonify({"status": "success", "message": "State updated"}), 200

@handle_exceptions
def get_state(host: str):
    state_data = hostvars.get_section(host, HostvarType.STATE)
    if not is_successful(state_data):
        return jsonify({"status": "error", "message": f"Failed to get state: {state_data.failure()}"}), 500

    return jsonify({"status": "success", "data": state_data}), 200

# def post_server():
#     try:
#         data = request.get_json()
#         parsed_data = EntryModel(**data)

#         inventory_data = parsed_data.inventory.model_dump()
#         storage_data = parsed_data.storage.model_dump()

#         return jsonify({"status": "success", "message": "Server schema updated"}), 200
#     except Exception as e:
#         tb = traceback.format_exc()

@handle_exceptions
def post_inventory():
    inventory_repo.remotes.origin.pull()
    data = request.get_json()
    hosts = [InventoryModel(**data)] if isinstance(data, dict) else [InventoryModel(**host) for host in data]

    for host in hosts:
        inventory.add_host(host.host, [host.node_type], str(host.ip), host.mac, host.port, host.ansible_user)

    inventory.save()

    if inventory_repo.is_dirty(untracked_files=True):
        inventory_repo.git.add(".")
        inventory_repo.index.commit("Updated inventory")
        inventory_repo.remotes.origin.push()
        return jsonify({"status": "success", "message": "Inventory updated"}), 200

    return jsonify({"status": "success", "message": "No updates made"}), 200

@handle_exceptions
def delete_inventory():
    inventory_repo.remotes.origin.pull()
    data = request.get_json()

    if not isinstance(data, list):
        return jsonify({"status": "error", "message": "Invalid data format"}), 400

    hosts = [DeleteInventoryModel(host=host) for host in data]

    logger.info(f"Deleting hosts: {hosts}")

    for host in hosts:
        logger.info(f"Removing host: {host.host}")
        inventory.remove_host(host.host)

    inventory.save()

    # Commit and push changes if repo is dirty
    if inventory_repo.is_dirty(untracked_files=True):
        inventory_repo.git.add(".")
        inventory_repo.index.commit("Updated inventory")
        inventory_repo.remotes.origin.push()
        return jsonify({"status": "success", "message": "Inventory updated"}), 200

    return jsonify({"status": "success", "message": "No updates made"}), 200

@handle_exceptions
def post_storage():
    return update_hostvars(request.get_json(), HostvarType.STORAGE, ValidationMode.FULL)
    # data = request.get_json()

    # for host, storage_data in data.items():
    #     res = hostvars.update_hostvars(host, HostvarType.STORAGE, ValidationMode.FULL, storage_data)
    #     if not is_successful(res):
    #         return jsonify({"status": "error", "message": f"Failed to update storage: {res.failure()}"}), 500

    # hostvars.save()
    # return jsonify({"status": "success", "message": "Storage schema updated"}), 200

@handle_exceptions
def put_storage():
    return update_hostvars(request.get_json(), HostvarType.STORAGE, ValidationMode.PARTIAL)
    # data = request.get_json()

    # for host, storage_data in data.items():
    #     res = hostvars.update_hostvars(host, HostvarType.STORAGE, ValidationMode.PARTIAL, storage_data)
    #     if not is_successful(res):
    #         return jsonify({"status": "error", "message": f"Failed to update storage: {res.failure()}"}), 500

    # hostvars.save()
    # return jsonify({"status": "success", "message": "Storage schema updated"}), 200

# App Initialization
if __name__ == '__main__':
    app = FlaskApp()
    app.run(host="0.0.0.0", port=3000)
