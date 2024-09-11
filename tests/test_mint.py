import pathlib

import pycardano
import pytest
from pycardano import TransactionFailedException

from plutus_bench import MockChainContext, MockUser
from plutus_bench.mock import MockFrostApi

from tests.mint import mint_coin_with_contract
from plutus_bench.tool import address_from_script, load_contract, ScriptType

own_path = pathlib.Path(__file__)


def test_mint_contract():
    api = MockFrostApi()
    context = MockChainContext(api=api)
    minting_user = MockUser(api)
    minting_user.fund(100_000_000)


    mint_coin_with_contract('My_token', 100, minting_user.signing_key, minting_user.verification_key, context)

def test_wrong_signature_mint_contract():
    api = MockFrostApi()
    context = MockChainContext(api=api)
    minting_user = MockUser(api)
    minting_user.fund(100_000_000)

    other_user = MockUser(api)
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
    test_wrong_signature_mint_contract()
