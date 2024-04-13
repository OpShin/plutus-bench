import dataclasses
import datetime
import uuid
from typing import Union, Dict
from multiprocessing import Manager

from fastapi import FastAPI

from plutus_bench import MockChainContext
from plutus_bench.mock import MockFrostApi

SESSION_MANAGER = Manager()


@dataclasses.dataclass
class Session:
    chain_state: MockFrostApi
    creation_time: datetime.datetime
    last_access_time: datetime.datetime


SESSIONS: Dict[str, Session] = {}
SESSIONS = SESSION_MANAGER.dict()


app = FastAPI(
    title="MockFrost API",
    summary="A clone of the important parts of the BlockFrost API which are used to evaluate transactions. Create your own mocked environment and execute transactions in it.",
    description="""
Start by creating a session.
You will receive a session id, which creates a unique fake blockchain state for you.
Using the session id, you can use `/api/v1/<session_id>` as base url for any Blockfrost using
transaction builder (such as the BlockFrostChainContext in PyCardano, Lucid, MeshJS etc).
The `/session` route provides you with additional tools to manipulate the state of the chain such as creating transaction outputs,
spinning forward the time of the environment or changing the protocol parameters.

Refer to the (Blockfrost documentation)[https://docs.blockfrost.io/] for more details about the `api/v1/` subroutes.
""",
)


@app.get("/session/create")
def create_session() -> str:
    """
    Create a new session.
    """
    session_id = uuid.uuid4()
    SESSIONS[session_id.hex] = Session(
        chain_state=MockFrostApi(seed=session_id.int),
        creation_time=datetime.datetime.now(),
        last_access_time=datetime.datetime.now(),
    )
    return session_id.hex


@app.get("/session/delete")
def delete_session(session_id: str):
    """
    Remove a session after usage.
    """
    if session_id in SESSIONS:
        del SESSIONS[session_id]


@app.get("/api/v1/{session_id}/epochs/latest")
def get_latest_epoch(session_id: str) -> Dict[str, int]:
    """
    Get the latest epoch.

    Args:
        session_id (str): The session ID.

    Returns:
        dict: The latest epoch.
    """
    session = SESSIONS[session_id]
    return session.chain_state.epoch_latest(return_type="json")
