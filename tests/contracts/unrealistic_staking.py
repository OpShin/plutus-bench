from opshin.prelude import *


def validator(address: Address, redeemer: BuiltinData, context: ScriptContext) -> None:
    purpose = context.purpose
    if isinstance(purpose, Certifying):
        return None  # Do whatever you like with certifiying
    elif isinstance(purpose, Rewarding):
        withdrawal_amount = context.tx_info.wdrl[purpose.staking_credential]
        paid_to_address = all_tokens_locked_at_address(
            context.tx_info.outputs, address, Token(b"", b"")
        )
        assert (
            paid_to_address >= 2 * withdrawal_amount
        ), "Insufficient rewards to address"
    else:
        assert False, "not a valid purpose"
