#!/usr/bin/env -S opshin eval spending
from opshin.prelude import *


def validator(pubkeyhash: bytes, redeemer: None, context: ScriptContext) -> None:
    sig_present = pubkeyhash in context.tx_info.signatories
    assert (
        sig_present
    ), f"Required signature missing, expected {pubkeyhash.hex()} but got {[s.hex() for s in context.tx_info.signatories]}"
