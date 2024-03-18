import pycardano
from pycardano import ChainContext
from plutus_bench.tool import load_contract, ScriptType

network = pycardano.Network.TESTNET
def spend_from_gift_contract(
    payment_key: pycardano.PaymentSigningKey,
    gift_contract_path: str,
    context: ChainContext
):
    gift_contract = load_contract(gift_contract_path, ScriptType.PlutusV2)
    script_hash = pycardano.script_hash(gift_contract)
    script_address = pycardano.Address(payment_part=script_hash)
    payment_vkey_hash = payment_key.to_verification_key().hash()
    payment_address = pycardano.Address(payment_part=payment_vkey_hash)
    utxos = context.utxos(script_address)
    if not utxos:
        raise ValueError("No UTxOs found")
    spend_utxo = None
    for u in utxos:
        datum = u.output.datum
        if datum is None:
            continue
        if datum != script_hash:
            continue
        if u.output.address != script_address:
            continue
        spend_utxo = u
        break
    txbuilder = pycardano.TransactionBuilder(
        context=context,
    )
    txbuilder.add_input_address(payment_address)
    txbuilder.add_script_input(
        spend_utxo,
        gift_contract,
        None,
        pycardano.Redeemer(0),
    )
    tx = txbuilder.build_and_sign(
        signing_keys=[payment_key],
        change_address=payment_address,
    )
    context.submit_tx(tx)


