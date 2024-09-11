import pathlib
from multiprocessing import Process
from time import sleep

import pycardano
import pytest
import uvicorn
from pycardano import TransactionFailedException
from starlette.testclient import TestClient

from plutus_bench import MockChainContext, MockUser
from plutus_bench.mock import MockFrostApi

from tests.mint import mint_coin_with_contract
from plutus_bench.tool import address_from_script, load_contract, ScriptType
from plutus_bench.mockfrost.client import MockFrostClient, MockFrostUser
from plutus_bench.mockfrost.server import app

own_path = pathlib.Path(__file__)


def run_server():
    uvicorn.run(app, port=8000)


@pytest.fixture
def server():
    proc = Process(target=run_server, args=(), daemon=True)
    proc.start()
    sleep(1)  # Wait for server to start
    yield
    proc.kill()  # Cleanup after test


def test_mint_contract(server):
    client = MockFrostClient(base_url="http://127.0.0.1:8000")
    session = client.create_session()
    context = session.chain_context()
    minting_user = MockFrostUser(session)
    minting_user.fund(100_000_000)

    mint_coin_with_contract('My_token', 100, minting_user.signing_key, minting_user.verification_key, context)
   
def test_wrong_signature_mint_contract(server):
    client = MockFrostClient(base_url="http://127.0.0.1:8000")
    session = client.create_session()
    context = session.chain_context()
    minting_user = MockFrostUser(session)
    minting_user.fund(100_000_000)

    other_user = MockFrostUser(session)

    pytest.raises(
        TransactionFailedException,
        mint_coin_with_contract,
        'My_token',
        100,
        minting_user.signing_key,
        other_user.verification_key,
        context
    )

if __name__ == "__main__":
    test_mint_contract()
    #test_spend_from_gift_contract()
    #test_other_user_spend_from_gift_contract()
