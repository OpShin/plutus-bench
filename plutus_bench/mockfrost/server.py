import dataclasses
import datetime
import uuid

import frozendict
from typing import Dict, Optional
from multiprocessing import Manager

import pycardano
from fastapi import FastAPI
from pycardano import (
    ProtocolParameters,
    GenesisParameters,
    TransactionInput,
    TransactionId,
)
from pydantic import BaseModel

from plutus_bench.mock import MockFrostApi
from plutus_bench.protocol_params import (
    DEFAULT_PROTOCOL_PARAMETERS,
    DEFAULT_GENESIS_PARAMETERS,
)

SESSION_MANAGER = Manager()


@dataclasses.dataclass
class Session:
    chain_state: MockFrostApi
    creation_time: datetime.datetime
    last_access_time: datetime.datetime


@dataclasses.dataclass
class SessionModel(BaseModel):
    creation_time: datetime.datetime
    last_access_time: datetime.datetime


@dataclasses.dataclass
class TransactionInputModel(BaseModel):
    tx_id: bytes
    output_index: int


SESSIONS: Dict[uuid.UUID, Session] = {}
SESSIONS = SESSION_MANAGER.dict()


app = FastAPI(
    title="MockFrost API",
    summary="A clone of the important parts of the BlockFrost API which are used to evaluate transactions. Create your own mocked environment and execute transactions in it.",
    description="""
Start by creating a session.
You will receive a session id, which creates a unique fake blockchain state for you.
Using the session id, you can use `/<session_id>/api/v1` as base url for any Blockfrost using
transaction builder (such as the BlockFrostChainContext in PyCardano, Lucid, MeshJS etc).
The `/session` route provides you with additional tools to manipulate the state of the chain such as creating transaction outputs,
spinning forward the time of the environment or changing the protocol parameters.

Refer to the [Blockfrost documentation](https://docs.blockfrost.io/) for more details about the `api/v1/` subroutes.
""",
)


@app.post("/session")
def create_session(
    seed: int = 0,
    protocol_parameters: dict = dataclasses.asdict(DEFAULT_PROTOCOL_PARAMETERS),
    genesis_parameters: dict = dataclasses.asdict(DEFAULT_GENESIS_PARAMETERS),
) -> uuid.UUID:
    """
    Create a new session.
    """
    session_id = uuid.uuid4()
    SESSIONS[session_id] = Session(
        chain_state=MockFrostApi(
            protocol_param=ProtocolParameters(**protocol_parameters),
            genesis_param=GenesisParameters(**genesis_parameters),
            seed=seed,
        ),
        creation_time=datetime.datetime.now(),
        last_access_time=datetime.datetime.now(),
    )
    return session_id


@app.get("/session/{session_id}")
def get_session_info(session_id: uuid.UUID) -> Optional[SessionModel]:
    """
    Remove a session after usage.
    """
    session = SESSIONS.get(session_id)
    if not session:
        return None
    return SessionModel(
        session.creation_time,
        session.last_access_time,
    )


@app.delete("/session/{session_id}")
def delete_session(session_id: uuid.UUID) -> bool:
    """
    Remove a session after usage.
    """
    if session_id in SESSIONS:
        del SESSIONS[session_id]
        return True
    return False


def model_from_transaction_input(tx_in: TransactionInput):
    return TransactionInputModel(
        tx_id=tx_in.transaction_id.payload, output_index=tx_in.index
    )


@app.post("/{session_id}/ledger/txo")
def add_transaction_output(
    session_id: uuid.UUID, tx_cbor: bytes
) -> TransactionInputModel:
    """
    Add a transaction output to the UTxO, without specifying the transaction hash and index (the "input").
    These will be created randomly and the corresponding CBOR is returned.
    """
    tx_in = SESSIONS[session_id].chain_state.add_txout(
        pycardano.TransactionOutput.from_cbor(tx_cbor)
    )
    return model_from_transaction_input(tx_in)


@app.put("/{session_id}/ledger/utxo")
def add_utxo(session_id: uuid.UUID, tx_cbor: bytes) -> TransactionInputModel:
    """
    Add a transaction output and input to the UTxO.
    Potentially overwrites existing inputs with the same transaction hash and index.
    Returns the created transaction input.
    """
    utxo = pycardano.UTxO.from_cbor(tx_cbor)
    SESSIONS[session_id].chain_state.add_utxo(utxo)
    return model_from_transaction_input(utxo.input)


@app.delete("/{session_id}/ledger/txo")
def delete_transaction_output(
    session_id: uuid.UUID, tx_input: TransactionInputModel
) -> bool:
    """
    Delete a transaction output from the UTxO.
    Returns whether the transaction output was in the UTxO
    """
    try:
        SESSIONS[session_id].chain_state.remove_txi(
            TransactionInput(
                transaction_id=TransactionId(tx_input.tx_id),
                index=tx_input.output_index,
            )
        )
    except:
        return False


@app.put("/{session_id}/ledger/slot")
def set_slot(session_id: uuid.UUID, slot: int) -> int:
    """
    Set the current slot of the ledger to a specified value.
    Essentially acts as a "time travel" tool.
    """
    SESSIONS[session_id].chain_state.set_block_slot(slot)
    return slot


@app.get("/{session_id}/api/v1/epochs/latest")
def latest_epoch(session_id: uuid.UUID) -> Dict[str, int]:
    """
    Return the information about the latest, therefore current, epoch.

    https://docs.blockfrost.io/#tag/Cardano-Epochs/paths/~1epochs~1latest/get
    """
    session = SESSIONS[session_id]
    return session.chain_state.epoch_latest(return_type="json")


@app.get("/{session_id}/api/v1/blocks/latest")
def latest_block(session_id: uuid.UUID) -> Dict[str, int]:
    """
    Return the latest block available to the backends, also known as the tip of the blockchain.

    https://docs.blockfrost.io/#tag/Cardano-Blocks/paths/~1blocks~1latest/get
    """
