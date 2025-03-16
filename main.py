import functools
import logging
import traceback
import uvicorn
import yaml
from pathlib import Path
from typing import List
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from returns.pipeline import is_successful
from models.state_model import StateModel
from utils.ansible.inventory import InventoryManager
from utils.repo import RepoManager
from utils.ansible.hostvars import HostvarType, HostvarsManager
from utils.dict_utils import ReplacementType
from models.inventory_model import *
from models.storage_model import *
from models.entry_model import *

"""Logging configuration"""
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

"""Configuration for the application"""
REPO_DIR: Path = Path("/app/repos")
REPO_SSH: str = "git@github.com:asdf57/hostvar_data.git"
INVENTORY_REPO_SSH: str = "git@github.com:asdf57/inventory.git"
HOSTVAR_REPO_PATH = REPO_DIR / "hostvar_data"
INVENTORY_REPO_PATH = REPO_DIR / "inventory" / "inventory.yml"

try:
    app = FastAPI()
except Exception as e:
    logger.error(f"Failed to initialize app: {e}")
    exit(1)

"""Global variables"""
try:
    hostvar_data_repo = RepoManager(REPO_SSH, HOSTVAR_REPO_PATH)
    inventory_repo = RepoManager(INVENTORY_REPO_SSH, INVENTORY_REPO_PATH)
    inventory_manager = InventoryManager(inventory_repo)
    hostvars_manager = HostvarsManager(hostvar_data_repo)
except Exception as e:
    logger.error(f"Failed to initialize global variables: {e}")
    exit(1)

def handle_exceptions(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"Exception occurred: {tb}")
            return JSONResponse(content={"status": "error", "message": str(e), "traceback": tb}, status_code=500)
    return wrapper

async def update_hostvars(host, data, hostvar_type: HostvarType, replace_type: ReplacementType):
    hostvars_manager.update(host, hostvar_type, replace_type, data)
    return JSONResponse(content={"status": "success", "message": "Hostvars updated"}, status_code=200)

async def init_host(payload: EntryModel):
    inventory = payload.inventory
    storage = payload.storage

    inventory_manager.add_host(inventory.host, [inventory.node_type] + inventory.groups, inventory.family, str(inventory.ip), inventory.mac, inventory.port, inventory.ansible_user)
    hostvars_manager.create(inventory.host, storage)

    return JSONResponse(content={"status": "success", "message": "Host initialized"}, status_code=200)

@app.post("/hostvars/{host}")
@handle_exceptions
async def post_hostvars(host: str, data: dict):
    return await update_hostvars(host, data, HostvarType.ANY, ReplacementType.OVERRIDE)

@app.put("/hostvars/{host}")
@handle_exceptions
async def post_hostvars(host: str, data: dict):
    return await update_hostvars(host, data, HostvarType.ANY, ReplacementType.IN_PLACE)


@app.get("/hostvars/{host}")
@handle_exceptions
async def get_hostvars(host: str):
    hostvars_data = hostvars_manager.get(host)
    return JSONResponse(content={"status": "success", "data": hostvars_data}, status_code=200)

@app.get("/hostvars")
@handle_exceptions
async def get_hostvars():
    hostvars_data = hostvars_manager.get_all()
    return JSONResponse(content={"status": "success", "data": hostvars_data}, status_code=200)

@app.post("/state/{host}")
@handle_exceptions
async def post_state(host: str, payload: StateModel):
    logger.info(f"payload: {payload.model_dump()}")
    return await update_hostvars(host, payload.model_dump(), HostvarType.STATE, ReplacementType.OVERRIDE)

@app.put("/state/{host}")
@handle_exceptions
async def post_state(host: str, payload: StateModel):
    logger.info(f"payload: {payload.model_dump()}")
    return await update_hostvars(host, payload.model_dump(), HostvarType.STATE, ReplacementType.IN_PLACE)

@app.get("/state/{host}")
@handle_exceptions
async def get_state(host: str):
    state_data = hostvars_manager.get_section_by_host(host, HostvarType.STATE)
    return JSONResponse(content={"status": "success", "data": state_data}, status_code=200)

@app.get("/state")
@handle_exceptions
async def get_state():
    state_data = hostvars_manager.get_all_by_section(HostvarType.STATE)
    return JSONResponse(content={"status": "success", "data": state_data}, status_code=200)

@app.post("/inventory")
@handle_exceptions
async def post_inventory(payload: InventoryModel):
    groups = [payload.node_type] + payload.groups
    inventory_manager.add_host(payload.host, groups, payload.family, str(payload.ip), payload.mac, payload.port, payload.ansible_user)
    return JSONResponse(content={"status": "success", "message": "Updated inventory"}, status_code=200)

@app.delete("/inventory")
@handle_exceptions
async def delete_inventory(payload: List[DeleteInventoryModel]):
    for entry in payload:
        logger.info(f"Removing host: {entry.host}")
        inventory_manager.remove_host(entry.host)
        logger.info(f"Deleting hosts: {entry.host}")

    return JSONResponse(content={"status": "success", "message": "Updated inventory"}, status_code=200)

@app.get("/inventory")
@handle_exceptions
async def get_inventory():
    inventory_data = inventory_manager.load().to_dict()
    return JSONResponse(content={"status": "success", "data": inventory_data}, status_code=200)

@app.post("/storage/{host}")
@handle_exceptions
async def post_storage(host: str, payload: StorageModel):
    return await update_hostvars(host, payload.model_dump(), HostvarType.STORAGE, ReplacementType.OVERRIDE)

@app.put("/storage/{host}")
@handle_exceptions
async def put_storage(host: str, payload: PartialStorageModel):
    return await update_hostvars(host, payload.model_dump(exclude_none=True), HostvarType.STORAGE, ReplacementType.IN_PLACE)

@app.get("/storage/{host}")
@handle_exceptions
async def get_storage(host: str):
    storage_data = hostvars_manager.get_section_by_host(host, HostvarType.STORAGE)
    return JSONResponse(content={"status": "success", "data": storage_data}, status_code=200)

@app.get("/storage")
@handle_exceptions
async def get_storage():
    storage_data = hostvars_manager.get_all_by_section(HostvarType.STORAGE)
    return JSONResponse(content={"status": "success", "data": storage_data}, status_code=200)

@app.post("/entry")
@handle_exceptions
async def post_init(payload: EntryModel):
    inventory = payload.inventory
    storage = payload.storage
    system  = payload.system
    inventory_manager.add_host(inventory.host, [inventory.node_type] + inventory.groups, inventory.family, str(inventory.ip), inventory.mac, inventory.port, inventory.ansible_user)
    hostvars_manager.create(inventory.host, storage, system)
    return JSONResponse(content={"status": "success", "message": "Host initialized"}, status_code=200)

@app.delete("/entry/{host}")
@handle_exceptions
async def delete_entry(host: str):
    inventory_manager.remove_host(host)
    hostvars_manager.delete(host)
    return JSONResponse(content={"status": "success", "message": "Host removed"}, status_code=200)

@app.get("/ipxe/")
@handle_exceptions
async def get_ipxe_script(mac: str):
    """
    Returns a plaintext response of the os to iPXE boot to
    """
    host = inventory_manager.get_host_by_mac(mac)
    if not host:
        return PlainTextResponse(content="Host not found", status_code=404)
    hostvars = hostvars_manager.get(host.name)
    if not hostvars:
        return PlainTextResponse(content="Hostvars not found", status_code=404)

    return PlainTextResponse(content=str(hostvars['system']['os']), status_code=200)

# App Initialization
if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=3000)
