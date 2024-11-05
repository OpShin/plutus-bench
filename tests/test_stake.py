import pathlib

import pycardano
import pytest
from pycardano import TransactionFailedException

from plutus_bench import MockChainContext, MockUser, MockPool
from plutus_bench.mock import MockFrostApi

from tests.stake import register_and_delegate
from pycardano.crypto.bech32 import decode
from opshin import build

own_path = pathlib.Path(__file__)


def test_register_and_delegate():
    api = MockFrostApi()
    context = MockChainContext(api=api)
    staking_user = MockUser(api)
    stake_pool = MockPool(api)

    staking_user.fund(100_000_000_000)
    script_path = own_path.parent / "contracts/unrealistic_staking.py"
    plutus_script = build(script_path, bytes(staking_user.verification_key.hash()))
    register_and_delegate(
        staking_user.signing_key, plutus_script, stake_pool.pool_id, context
    )


    stake_address = stake_info["stake_address"]
    script_payment_address = stake_info["script_payment_address"]


if __name__ == "__main__":
    test_register_and_delegate()
    #test_withdraw()
