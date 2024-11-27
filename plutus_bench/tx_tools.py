from functools import cache
from typing import Optional

import cbor2
import pycardano
import uplc
import uplc.cost_model
import uplc.ast
from pycardano import (
    ScriptHash,
    RedeemerTag,
    plutus_script_hash,
    datum_hash,
    PlutusV2Script,
    UTxO,
)

from .ledger.api_v2 import *


def to_staking_credential(
    sk: Union[
        pycardano.VerificationKeyHash,
        pycardano.ScriptHash,
        pycardano.PointerAddress,
        None,
    ]
):
    try:
        return SomeStakingCredential(to_staking_hash(sk))
    except NotImplementedError:
        return NoStakingCredential()


def to_staking_hash(
    sk: Union[
        pycardano.VerificationKeyHash, pycardano.ScriptHash, pycardano.PointerAddress
    ]
):
    if isinstance(sk, pycardano.PointerAddress):
        return StakingPtr(sk.slot, sk.tx_index, sk.cert_index)
    if isinstance(sk, pycardano.VerificationKeyHash):
        return StakingHash(PubKeyCredential(sk.payload))
    if isinstance(sk, pycardano.ScriptHash):
        return StakingHash(ScriptCredential(sk.payload))
    raise NotImplementedError(f"Unknown stake key type {type(sk)}")


def to_wdrl(wdrl: Optional[pycardano.Withdrawals]) -> Dict[StakingCredential, int]:
    if wdrl is None:
        return {}

    def m(k: bytes):
        sk = pycardano.Address.from_primitive(k).staking_part
        return to_staking_hash(sk)

    return {m(key): val for key, val in wdrl.to_primitive().items()}


def to_valid_range(validity_start: Optional[int], ttl: Optional[int], posix_from_slot):
    if validity_start is None:
        lower_bound = LowerBoundPOSIXTime(NegInfPOSIXTime(), FalseData())
    else:
        start = posix_from_slot(validity_start) * 1000
        lower_bound = LowerBoundPOSIXTime(FinitePOSIXTime(start), TrueData())
    if ttl is None:
        upper_bound = UpperBoundPOSIXTime(PosInfPOSIXTime(), FalseData())
    else:
        end = posix_from_slot(ttl) * 1000
        upper_bound = UpperBoundPOSIXTime(FinitePOSIXTime(end), TrueData())
    return POSIXTimeRange(lower_bound, upper_bound)


def to_pubkeyhash(vkh: pycardano.VerificationKeyHash):
    return PubKeyHash(vkh.payload)


def to_tx_id(tx_id: pycardano.TransactionId):
    return TxId(tx_id.payload)


def to_dcert(c: pycardano.Certificate) -> DCert:
    if isinstance(c, pycardano.StakeRegistration):
        return DCertDelegRegKey(to_staking_hash(c.stake_credential.credential))
    elif isinstance(c, pycardano.StakeDelegation):
        return DCertDelegDelegate(
            to_staking_hash(c.stake_credential.credential),
            PubKeyHash(c.pool_keyhash.payload),
        )
    elif isinstance(c, pycardano.StakeDeregistration):
        # TODO
        raise NotImplementedError(
            f"Certificates of type {type(c)} can not be converted yet"
        )
    elif isinstance(c, pycardano.PoolRegistration):
        # TODO
        raise NotImplementedError(
            f"Certificates of type {type(c)} can not be converted yet"
        )
    elif isinstance(c, pycardano.PoolRetirement):
        # TODO
        raise NotImplementedError(
            f"Certificates of type {type(c)} can not be converted yet"
        )
    raise NotImplementedError(f"Certificates of type {type(c)} are not implemented")


def multiasset_to_value(ma: pycardano.MultiAsset) -> Value:
    if ma is None:
        return {b"": {b"": 0}}
    return {
        PolicyId(policy_id): {
            TokenName(asset_name): quantity for asset_name, quantity in asset.items()
        }
        for policy_id, asset in ma.to_shallow_primitive().items()
    }


def value_to_value(v: pycardano.Value):
    ma = multiasset_to_value(v.multi_asset)
    ma[b""] = {b"": v.coin}
    return ma


def to_payment_credential(
    c: Union[pycardano.VerificationKeyHash, pycardano.ScriptHash]
):
    if isinstance(c, pycardano.VerificationKeyHash):
        return PubKeyCredential(PubKeyHash(c.payload))
    if isinstance(c, pycardano.ScriptHash):
        return ScriptCredential(ValidatorHash(c.payload))
    raise NotImplementedError(f"Unknown payment key type {type(c)}")


def to_address(a: pycardano.Address):
    return Address(
        to_payment_credential(a.payment_part),
        to_staking_credential(a.staking_part),
    )


def to_tx_out(o: pycardano.TransactionOutput):
    if o.datum is not None:
        output_datum = SomeOutputDatum(o.datum)
    elif o.datum_hash is not None:
        output_datum = SomeOutputDatumHash(o.datum_hash.payload)
    else:
        output_datum = NoOutputDatum()
    if o.script is None:
        script = NoScriptHash()
    else:
        script = SomeScriptHash(pycardano.script_hash(o.script).payload)
    return TxOut(
        to_address(o.address),
        value_to_value(o.amount),
        output_datum,
        script,
    )


def to_tx_out_ref(i: pycardano.TransactionInput):
    return TxOutRef(
        TxId(i.transaction_id.payload),
        i.index,
    )


def to_tx_in_info(i: pycardano.TransactionInput, o: pycardano.TransactionOutput):
    return TxInInfo(
        to_tx_out_ref(i),
        to_tx_out(o),
    )


def to_redeemer_purpose(
    r: Union[pycardano.RedeemerKey, pycardano.Redeemer],
    tx_body: pycardano.TransactionBody,
):
    v = r.tag
    if v == pycardano.RedeemerTag.SPEND:
        spent_input = tx_body.inputs[r.index]
        return Spending(to_tx_out_ref(spent_input))
    elif v == pycardano.RedeemerTag.MINT:
        minted_id = sorted(tx_body.mint.data.keys())[r.index]
        return Minting(PolicyId(minted_id.payload))
    elif v == pycardano.RedeemerTag.CERTIFICATE:
        certificate = tx_body.certificates[r.index]
        return Certifying(to_dcert(certificate))
    elif v == pycardano.RedeemerTag.WITHDRAWAL:
        withdrawal = sorted(tx_body.withdraws.keys())[r.index]
        script_hash = pycardano.Address.from_primitive(withdrawal).staking_part
        return Rewarding(to_staking_hash(script_hash))
    else:
        raise NotImplementedError()


def to_tx_info(
    tx: pycardano.Transaction,
    resolved_inputs: List[pycardano.TransactionOutput],
    resolved_reference_inputs: List[pycardano.TransactionOutput],
    posix_from_slot,
):
    tx_body = tx.transaction_body
    datums = [
        o.datum
        for o in tx_body.outputs + resolved_inputs + resolved_reference_inputs
        if o.datum is not None
    ]
    if tx.transaction_witness_set.plutus_data:
        datums += tx.transaction_witness_set.plutus_data

    redeemers = (
        tx.transaction_witness_set.redeemer
        if tx.transaction_witness_set.redeemer
        else []
    )
    return TxInfo(
        [to_tx_in_info(i, o) for i, o in zip(tx_body.inputs, resolved_inputs)],
        (
            [
                to_tx_in_info(i, o)
                for i, o in zip(tx_body.reference_inputs, resolved_reference_inputs)
            ]
            if tx_body.reference_inputs is not None
            else []
        ),
        [to_tx_out(o) for o in tx_body.outputs],
        value_to_value(pycardano.Value(tx_body.fee)),
        multiasset_to_value(tx_body.mint),
        [to_dcert(c) for c in tx_body.certificates] if tx_body.certificates else [],
        to_wdrl(tx_body.withdraws),
        to_valid_range(tx_body.validity_start, tx_body.ttl, posix_from_slot),
        (
            [to_pubkeyhash(s) for s in tx_body.required_signers]
            if tx_body.required_signers
            else []
        ),
        (
            {to_redeemer_purpose(k, tx_body): v.data for k, v in redeemers.items()}
            if isinstance(redeemers, pycardano.RedeemerMap)
            else {to_redeemer_purpose(r, tx_body): r.data for r in redeemers}
        ),
        {pycardano.datum_hash(d).payload: d for d in datums},
        to_tx_id(tx_body.id),
    )


@dataclass
class ScriptInvocation:
    script: pycardano.ScriptType
    datum: Optional[pycardano.Datum]
    redeemer: Union[pycardano.Redeemer, pycardano.RedeemerMap]
    script_context: ScriptContext


def generate_script_contexts(tx_builder: pycardano.TransactionBuilder):
    """Generates for each evaluated script, with which parameters it should be called"""
    # TODO this only handles PlutusV2, no other script contexts are currently supported

    tx = tx_builder._build_full_fake_tx()
    # we assume that reference inputs are UTxO objects!
    input_to_resolved_output = {}
    for utxo in tx_builder.inputs + list(tx_builder.reference_inputs):
        assert isinstance(utxo, pycardano.UTxO)
        input_to_resolved_output[utxo.input] = utxo.output
    # input_to_resolved_output = {
    #     utxo.input: utxo.output
    #     for utxo in tx_builder.inputs + tx_builder.reference_inputs
    # }
    resolved_inputs = [
        UTxO(i, input_to_resolved_output[i]) for i in tx.transaction_body.inputs
    ]
    resolved_reference_inputs = [
        UTxO(i, input_to_resolved_output[i])
        for i in tx.transaction_body.reference_inputs
    ]
    return generate_script_contexts_resolved(
        tx, resolved_inputs, resolved_reference_inputs
    )


def as_redeemer(
    r: Union[pycardano.Redeemer, pycardano.RedeemerKey], redeemers: pycardano.Redeemers
):
    if isinstance(r, pycardano.RedeemerKey):
        v = redeemers[r]
        new_r = pycardano.Redeemer(data=v.data, ex_units=v.ex_units)
        new_r.tag = r.tag
        new_r.index = r.index
        return new_r
    else:
        return r


def generate_script_contexts_resolved(
    tx: pycardano.Transaction,
    resolved_inputs: List[UTxO],
    resolved_reference_inputs: List[UTxO],
    posix_from_slot,
):
    tx_info = to_tx_info(
        tx,
        [i.output for i in resolved_inputs],
        [i.output for i in resolved_reference_inputs],
        posix_from_slot,
    )
    datum = None
    script_contexts = []
    for i, spending_input in enumerate(resolved_inputs):
        if not isinstance(spending_input.output.address.payment_part, ScriptHash):
            continue
        try:
            # Redeemers is Union[RedeemerMap, List[Redeemer]]
            spending_redeemer = as_redeemer(
                next(
                    r
                    for r in tx.transaction_witness_set.redeemer
                    if r.index == i and r.tag == RedeemerTag.SPEND
                ),
                tx.transaction_witness_set.redeemer,
            )
        except (StopIteration, TypeError):
            raise ValueError(
                f"Missing redeemer for script input {i} (index or tag set incorrectly or missing redeemer)"
            )
        potential_scripts = tx.transaction_witness_set.plutus_v2_script or []
        for input in resolved_reference_inputs + resolved_inputs:
            if input.output.script is not None:
                potential_scripts.append(input.output.script)
        try:
            spending_script = next(
                s
                for s in tx.transaction_witness_set.plutus_v2_script
                if plutus_script_hash(PlutusV2Script(s))
                == spending_input.output.address.payment_part
            )
        except (StopIteration, TypeError):
            raise NotImplementedError(
                "Can not validate spending of non plutus v2 script (or plutus v2 script is not in context)"
            )
        if spending_input.output.datum is not None:
            datum = spending_input.output.datum
        elif spending_input.output.datum_hash is not None:
            datum_h = spending_input.output.datum_hash
            try:
                datum = next(
                    d
                    for d in tx.transaction_witness_set.plutus_data or []
                    if datum_hash(d) == datum_h
                )
            except StopIteration:
                raise ValueError(
                    f"No datum with hash '{datum_h.payload.hex()}' provided for transaction"
                )
        else:
            raise ValueError(
                "Spending input is missing an attached datum and can not be spent"
            )
        script_contexts.append(
            ScriptInvocation(
                spending_script,
                datum,
                spending_redeemer,
                ScriptContext(tx_info, Spending(to_tx_out_ref(spending_input.input))),
            )
        )
    for i, minting_script_hash in enumerate(tx.transaction_body.mint or []):
        try:
            minting_redeemer = as_redeemer(
                next(
                    r
                    for r in tx.transaction_witness_set.redeemer
                    if r.index == i and r.tag == RedeemerTag.MINT
                ),
                tx.transaction_witness_set.redeemer,
            )
        except StopIteration:
            raise ValueError(
                f"Missing redeemer for mint {i} (index or tag set incorrectly or missing redeemer)"
            )
        try:
            minting_script = next(
                s
                for s in tx.transaction_witness_set.plutus_v2_script
                if plutus_script_hash(PlutusV2Script(s)) == minting_script_hash
            )
        except StopIteration:
            raise NotImplementedError(
                "Can not validate spending of non plutus v2 script (or plutus v2 script is not in context)"
            )

        script_contexts.append(
            ScriptInvocation(
                minting_script,
                datum,
                minting_redeemer,
                ScriptContext(
                    tx_info, Minting(pycardano.script_hash(minting_script).payload)
                ),
            )
        )
    for i, certificate in enumerate(tx.transaction_body.certificates or []):
        try:
            certificate_redeemer = as_redeemer(
                next(
                    r
                    for r in tx.transaction_witness_set.redeemer or []
                    if r.index == i and r.tag == RedeemerTag.CERTIFICATE
                ),
                tx.transaction_witness_set.redeemer,
            )
        except StopIteration:
            if isinstance(certificate, pycardano.StakeRegistration):
                #  TODO: Check can this always be skipped?
                continue
            raise ValueError(
                f"Missing redeemer for certificate {i} (index or tag set incorrectly or missing redeemer)"
            )
        try:
            certificate_script = next(
                s
                for s in tx.transaction_witness_set.plutus_v2_script
                if plutus_script_hash(PlutusV2Script(s))
                == certificate.stake_credential.credential
            )
        except StopIteration:
            raise NotImplementedError(
                "Can not validate spending of non plutus v2 script (or plutus v2 script is not in context)"
            )

        script_contexts.append(
            ScriptInvocation(
                certificate_script,
                datum,
                certificate_redeemer,
                ScriptContext(tx_info, Certifying(to_dcert(certificate))),
            )
        )
    for i, address in enumerate(sorted(tx.transaction_body.withdraws or {})):
        try:
            withdrawal_redeemer = as_redeemer(
                next(
                    r
                    for r in tx.transaction_witness_set.redeemer
                    if r.index == i and r.tag == RedeemerTag.WITHDRAWAL
                ),
                tx.transaction_witness_set.redeemer,
            )
        except StopIteration:
            raise ValueError(
                f"Missing redeemer for withdrawal {i} (index or tag set incorrectly or missing redeemer)"
            )
        script_hash = pycardano.Address.from_primitive(address).staking_part
        try:
            withdrawal_script = next(
                s
                for s in tx.transaction_witness_set.plutus_v2_script
                if plutus_script_hash(PlutusV2Script(s)) == script_hash
            )
        except StopIteration:
            raise NotImplementedError(
                "Can not validate spending of non plutus v2 script (or plutus v2 script is not in context)"
            )

        script_contexts.append(
            ScriptInvocation(
                withdrawal_script,
                datum,
                withdrawal_redeemer,
                ScriptContext(tx_info, Rewarding(to_staking_hash(script_hash))),
            )
        )

    return script_contexts


@cache
def uplc_unflat(script: bytes):
    return uplc.unflatten(script)


def uplc_plutus_data(a: pycardano.Datum) -> PlutusData:
    return uplc.ast.data_from_cbor(cbor2.dumps(a, default=pycardano.default_encoder))


def evaluate_script(script_invocation: ScriptInvocation):
    uplc_program = uplc_unflat(script_invocation.script)
    args = [script_invocation.redeemer.data, script_invocation.script_context]
    if script_invocation.datum is not None:
        args.insert(0, script_invocation.datum)
    args = [uplc_plutus_data(a) for a in args]
    allowed_cpu_steps = script_invocation.redeemer.ex_units.steps
    allowed_mem_steps = script_invocation.redeemer.ex_units.mem
    res = uplc.eval(
        uplc.tools.apply(uplc_program, *args),
        budget=uplc.cost_model.Budget(allowed_cpu_steps, allowed_mem_steps),
    )
    logs = res.logs
    return (
        (res.result),
        (
            res.cost.cpu,
            res.cost.memory,
        ),
        logs,
    )
