from opshin.prelude import *


def validator(datum: PubKeyHash, redeem: None, ctx: ScriptContext) -> None:
    assert datum in ctx.tx_info.signatories
