import pathlib

import pycardano
import pytest

from plutus_bench import MockChainContext, MockUser

from tests.gift import spend_from_gift_contract
from plutus_bench.tool import address_from_script, load_contract, ScriptType

own_path = pathlib.Path(__file__)


def test_spend_from_gift_contract():
    context = MockChainContext()
    payment_key = MockUser(context)
    payment_key.fund(100_000_000)
    gift_contract_path = own_path.parent / "gift.plutus"
    gift_address = address_from_script(
        load_contract(gift_contract_path, ScriptType.PlutusV2), network=context.network
    )
    context.add_txout(
        pycardano.TransactionOutput(
            address=gift_address,
            amount=pycardano.Value(coin=1000000),
            datum=payment_key.verification_key.hash().payload,
        ),
    )
    spend_from_gift_contract(payment_key.signing_key, gift_contract_path, context)


def test_other_user_spend_from_gift_contract():
    context = MockChainContext()
    payment_key = MockUser(context)
    payment_key.fund(100_000_000)

    owning_user = MockUser(context)
    gift_contract_path = own_path.parent / "gift.plutus"
    gift_address = address_from_script(
        load_contract(gift_contract_path, ScriptType.PlutusV2), network=context.network
    )
    context.add_txout(
        pycardano.TransactionOutput(
            address=gift_address,
            amount=pycardano.Value(coin=1000000),
            datum=owning_user.verification_key.hash().payload,
        ),
    )
    pytest.raises(
        RuntimeError,
        spend_from_gift_contract,
        payment_key.signing_key,
        gift_contract_path,
        context,
        enforce_true_owner=False,
        set_required_signers=True,
    )
    pytest.raises(
        RuntimeError,
        spend_from_gift_contract,
        payment_key.signing_key,
        gift_contract_path,
        context,
        enforce_true_owner=False,
        set_required_signers=False,
    )


if __name__ == "__main__":
    test_spend_from_gift_contract()
    test_other_user_spend_from_gift_contract()
