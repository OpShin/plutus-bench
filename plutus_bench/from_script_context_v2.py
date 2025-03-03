from typing import Tuple, TypedDict, Optional

import pycardano
from .ledger.api_v2 import *


def from_staking_credential(
    sk: Union[SomeStakingCredential, NoStakingCredential],
) -> Union[
    pycardano.VerificationKeyHash,
    pycardano.ScriptHash,
    pycardano.PointerAddress,
    None,
]:
    if isinstance(sk, NoStakingCredential):
        return None
    else:
        return from_staking_hash(sk.staking_credential)


def from_staking_hash(
    sk: Union[StakingPtr, StakingHash],
) -> Union[
    pycardano.VerificationKeyHash, pycardano.ScriptHash, pycardano.PointerAddress
]:
    if isinstance(sk, StakingPtr):
        return pycardano.PointerAddress(sk.slot_no, sk.tx_index, sk.cert_index)
    if isinstance(sk, StakingHash):
        if isinstance(sk.value, PubKeyCredential):
            return pycardano.VerificationKeyHash(sk.value.credential_hash)
        if isinstance(sk.value, ScriptCredential):
            return pycardano.ScriptHash(sk.value.credential_hash)
    raise NotImplementedError(f"Unknown stake key type {type(sk)}")


def from_pubkeyhash(pkh: PubKeyHash) -> pycardano.VerificationKeyHash:
    return pycardano.VerificationKeyHash.from_primitive(pkh)


def from_payment_credential(
    c: Union[PubKeyCredential, ScriptCredential],
) -> Union[pycardano.VerificationKeyHash, pycardano.ScriptHash]:
    if isinstance(c, PubKeyCredential):
        return pycardano.VerificationKeyHash(c.credential_hash)
    if isinstance(c, ScriptCredential):
        return pycardano.ScriptHash(c.credential_hash)
    raise NotImplementedError(f"Unknown payment key type {type(c)}")


def from_address(a: Address, network: pycardano.Network) -> pycardano.Address:
    return pycardano.Address(
        from_payment_credential(a.payment_credential),
        from_staking_credential(a.staking_credential),
        network=network,
    )


def from_value(a: Value) -> pycardano.Value:
    lovelace = a.get(b"", {}).get(b"", 0)
    multi_asset = pycardano.MultiAsset()
    for policy_id, tokens in a.items():
        if policy_id == b"":
            continue
        for token_name, amount in tokens.items():
            multi_asset += pycardano.MultiAsset(
                {
                    pycardano.ScriptHash(policy_id): {
                        pycardano.AssetName(token_name): amount
                    }
                }
            )
    return pycardano.Value(coin=lovelace, multi_asset=multi_asset)


class DatumDict(TypedDict):
    datum: Optional[pycardano.Datum]
    datum_hash: Optional[pycardano.DatumHash]


def from_output_datum(a: OutputDatum) -> DatumDict:
    if isinstance(a, NoOutputDatum):
        return {"datum": None, "datum_hash": None}
    if isinstance(a, SomeOutputDatum):
        return {"datum": a.datum, "datum_hash": pycardano.datum_hash(a.datum)}
    if isinstance(a, SomeOutputDatumHash):
        return {"datum": None, "datum_hash": pycardano.DatumHash(a.datum_hash)}
    raise NotImplementedError(f"Unknown output datum type {type(a)}")
