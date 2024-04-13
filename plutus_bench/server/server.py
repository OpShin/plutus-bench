import dataclasses
import datetime
import uuid
from typing import Union, Dict
from multiprocessing import Manager

from fastapi import FastAPI

from plutus_bench import MockChainContext

SESSION_MANAGER = Manager()


@dataclasses.dataclass
class Session:
    context: MockChainContext
    creation_time: datetime.datetime
    last_access_time: datetime.datetime


SESSIONS: Dict[str, Session] = {}

app = FastAPI()


@app.on_event("startup")
async def startup_event():
    global SESSIONS
    SESSIONS = SESSION_MANAGER.dict()


@app.get("/session/create")
def create_session():
    """
    Create a new session.

    Returns:
        str: The session ID.
    """
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = Session(
        context=MockChainContext(),
        creation_time=datetime.datetime.now(),
        last_access_time=datetime.datetime.now(),
    )
    return session_id


@app.get("/api/v1/{session_id}/epochs/latest")
def get_latest_epoch(session_id: str):
    """
    Get the latest epoch.

    Args:
        session_id (str): The session ID.

    Returns:
        dict: The latest epoch.
    """
    session = SESSIONS[session_id]
    return session.context.epoch_latest()
