import pathlib

import cbor2
import pycardano
from pycardano import ChainContext
from plutus_bench.tool import load_contract, ScriptType, address_from_script


def give(
    payment_key: pycardano.PaymentSigningKey,
    script: pycardano.PlutusV1Script,
    context: ChainContext,
    give_value: int,
):
    network = context.network
    script_address = pycardano.Address(pycardano.script_hash(script), network=network)
    payment_vkey_address = payment_key.to_verification_key().hash()
    payment_address = pycardano.Address(
        payment_part=payment_vkey_address, network=network
    )

    builder = pycardano.TransactionBuilder(context)
    builder.add_input_address(payment_address)
    datum = pycardano.Unit()
    builder.add_output(
        pycardano.TransactionOutput(
            script_address, give_value, datum_hash=pycardano.datum_hash(datum)
        )
    )
    signed_tx = builder.build_and_sign(
        [
            payment_key,
        ],
        payment_address,
    )
    context.submit_tx(signed_tx)


def take(
    taker_key: pycardano.PaymentSigningKey,
    script: pycardano.PlutusV1Script,
    redeemer: pycardano.Redeemer,
    context: ChainContext,
    value: int,
):
    network = context.network
    script_address = pycardano.Address(pycardano.script_hash(script), network=network)
    taker_address = pycardano.Address(
        taker_key.to_verification_key().hash(), network=network
    )

    utxo_to_spend = context.utxos(script_address)[0]
    datum = pycardano.Unit()

    builder = pycardano.TransactionBuilder(context)
    builder.add_input_address(taker_address)
    builder.add_script_input(utxo_to_spend, script, datum, redeemer)
    builder.add_output(pycardano.TransactionOutput(taker_address, value))

    signed_tx = builder.build_and_sign([taker_key], taker_address)
    context.submit_tx(signed_tx)
