import pathlib

import pycardano
import pytest
from pycardano import TransactionFailedException

from plutus_bench import MockChainContext, MockUser
from plutus_bench.mock import MockFrostApi

from tests.fortytwo import *
from plutus_bench.tool import address_from_script, load_contract, ScriptType

own_path = pathlib.Path(__file__)


def test_fortytwo_v1_script():
    api = MockFrostApi()
    context = MockChainContext(api=api)
    giver = MockUser(api)
    giver.fund(100_000_000)
    gift_contract_path = own_path.parent / "contracts/fortytwo.cbor"
    with open(gift_contract_path, "r") as f:
        script_hex = f.read()
        forty_two_script = cbor2.loads(bytes.fromhex(script_hex))
    script = pycardano.PlutusV1Script(forty_two_script)

    give(giver.signing_key, script, context, 50_000_000)

    taker = MockUser(api)
    taker.fund(14_000_000)  # give collateral

    take(taker.signing_key, script, pycardano.Redeemer(42), context, 25_000_000)


if __name__ == "__main__":
    test_fortytwo_v1_script()
