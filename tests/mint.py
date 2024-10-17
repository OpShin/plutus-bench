import pathlib
from opshin import build
import cbor2
import pycardano
from pycardano import ChainContext
from plutus_bench.tool import load_contract, ScriptType, address_from_script

own_path = pathlib.Path(__file__)


def mint_coin_with_contract(
    token_name: str,
    amount: int,
    issuer_signing_key: pycardano.PaymentSigningKey,
    required_key: pycardano.PaymentVerificationKey,
    context: ChainContext,
):
    network = context.network

    tn_bytes = bytes(token_name, encoding="utf-8")

    VerificationKey = pycardano.PaymentVerificationKey.from_signing_key(
        issuer_signing_key
    )
    payment_address = pycardano.Address(
        payment_part=VerificationKey.hash(), network=network
    )

    # get input utxo
    utxo_to_spend_or_burn = None
    if amount > 0:
        for utxo in context.utxos(payment_address):
            if utxo.output.amount.coin > 3_000_000:
                utxo_to_spend_or_burn = utxo
                break
    else:

        def f(pi: pycardano.ScriptHash, an: pycardano.AssetName, a: int) -> bool:
            return pi == script_hash and an.payload == tn_bytes and a >= -amount

        for utxo in context.utxos(payment_address):
            if utxo.output.amount.multi_asset.count(f):
                utxo_to_spend_or_burn = utxo
    assert utxo_to_spend_or_burn is not None, "UTxO not found to spend!"

    # Build script
    mint_script_path = own_path.parent / "contracts" / "signed_mint.py"
    pkh = required_key.hash()
    plutus_script = build(mint_script_path, pkh)

    script_hash = pycardano.plutus_script_hash(plutus_script)

    # Build the transaction
    builder = pycardano.TransactionBuilder(context)
    builder.add_minting_script(script=plutus_script, redeemer=pycardano.Redeemer(0))
    builder.mint = pycardano.MultiAsset.from_primitive(
        {bytes(script_hash): {tn_bytes: amount}}
    )
    builder.add_input(utxo_to_spend_or_burn)
    if amount > 0:
        # if not burning
        builder.add_output(
            pycardano.TransactionOutput(
                payment_address,
                amount=pycardano.Value(coin=amount, multi_asset=builder.mint),
            )
        )
    # builder.required_signers = [VerificationKey,]

    # sign the transation
    signed_tx = builder.build_and_sign(
        signing_keys=[
            issuer_signing_key,
        ],
        change_address=payment_address,
        auto_required_signers=True,
    )

    context.submit_tx(signed_tx)
