import random
import uuid
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Union

from pycardano import (
    Address,
    ChainContext,
    ExecutionUnits,
    GenesisParameters,
    Network,
    PaymentSigningKey,
    PaymentVerificationKey,
    ProtocolParameters,
    ScriptType,
    Transaction,
    TransactionId,
    TransactionInput,
    TransactionOutput,
    UTxO,
    Value,
    RedeemerTag,
)

from .protocol_params import (
    DEFAULT_GENESIS_PARAMETERS,
    DEFAULT_PROTOCOL_PARAMETERS,
)
from .tx_tools import (
    evaluate_script,
    generate_script_contexts_resolved,
    ScriptInvocation,
)


ValidatorType = Callable[[Any, Any, Any], Any]
MintingPolicyType = Callable[[Any, Any], Any]
OpshinValidator = Union[ValidatorType, MintingPolicyType]


def evaluate_opshin_validator(validator: OpshinValidator, invocation: ScriptInvocation):
    if invocation.redeemer.tag == RedeemerTag.SPEND:
        validator(invocation.datum, invocation.redeemer.data, invocation.script_context)
    elif invocation.redeemer.tag == RedeemerTag.MINT:
        validator(invocation.redeemer.data, invocation.script_context)
    else:
        raise NotImplementedError("Only spending and minting validators supported.")


class MockChainContext(ChainContext):
    def __init__(
        self,
        protocol_param: Optional[ProtocolParameters] = None,
        genesis_param: Optional[GenesisParameters] = None,
        opshin_scripts: Optional[Dict[ScriptType, OpshinValidator]] = None,
        seed: int = 0,
    ):
        """
        A mock PyCardano ChainContext that you can use for testing offchain code and evaluating scripts locally.

        Args:
            protocol_param: Cardano Node protocol parameters. Defaults to preview network parameters.
            genesis_param: Cardano Node genesis parameters. Defaults to preview network parameters.
            opshin_scripts: If set, evaluate the opshin validator when the plutus script matches.
        """
        self.random = random.Random(seed)
        self._protocol_param = (
            protocol_param if protocol_param else DEFAULT_PROTOCOL_PARAMETERS
        )
        self._genesis_param = (
            genesis_param if genesis_param else DEFAULT_GENESIS_PARAMETERS
        )
        if opshin_scripts is None:
            self.opshin_scripts = {}
        else:
            self.opshin_scripts = opshin_scripts
        self._utxo_state: Dict[str, List[UTxO]] = defaultdict(list)
        self._address_lookup: Dict[UTxO, str] = {}
        self._utxo_from_txid: Dict[TransactionId, Dict[int, UTxO]] = defaultdict(dict)
        self._network = Network.TESTNET
        self._epoch = 0
        self._last_block_slot = 0

    @property
    def protocol_param(self) -> ProtocolParameters:
        return self._protocol_param

    @property
    def genesis_param(self) -> GenesisParameters:
        return self._genesis_param

    @property
    def network(self) -> Network:
        return self._network

    @property
    def epoch(self) -> int:
        return self._epoch

    @property
    def last_block_slot(self) -> int:
        return self._last_block_slot

    def _utxos(self, address: str) -> List[UTxO]:
        return self._utxo_state.get(address, [])

    def add_utxo(self, utxo: UTxO):
        address = str(utxo.output.address)
        self._utxo_state[address].append(utxo)
        self._address_lookup[utxo] = address
        self._utxo_from_txid[utxo.input.transaction_id][utxo.input.index] = utxo

    def add_txout(self, txout: TransactionOutput):
        """
        Basically the same as add_utxo, but clarifies that the transaction id does not matter.
        """
        utxo = UTxO(
            TransactionInput(TransactionId(self.random.randbytes(32)), 0), txout
        )
        self.add_utxo(utxo)

    def get_address(self, utxo: UTxO) -> str:
        return self._address_lookup[utxo]

    def remove_utxo(self, utxo: UTxO):
        del self._utxo_from_txid[utxo.input.transaction_id][utxo.input.index]
        address = self._address_lookup[utxo]
        del self._address_lookup[utxo]
        i = self._utxo_state[address].index(utxo)
        self._utxo_state[address].pop(i)

    def get_utxo_from_txid(self, transaction_id: TransactionId, index: int) -> UTxO:
        return self._utxo_from_txid[transaction_id][index]

    def submit_tx(self, tx: Transaction):
        self.evaluate_tx(tx)
        self.submit_tx_mock(tx)

    def submit_tx_mock(self, tx: Transaction):
        for input in tx.transaction_body.inputs:
            utxo = self.get_utxo_from_txid(input.transaction_id, input.index)
            self.remove_utxo(utxo)
        for i, output in enumerate(tx.transaction_body.outputs):
            utxo = UTxO(TransactionInput(tx.id, i), output)
            self.add_utxo(utxo)

    def submit_tx_cbor(self, cbor: Union[bytes, str]):
        return self.submit_tx(Transaction.from_cbor(cbor))

    def evaluate_tx(self, tx: Transaction) -> Dict[str, ExecutionUnits]:
        input_utxos = [
            self.get_utxo_from_txid(input.transaction_id, input.index)
            for input in tx.transaction_body.inputs
        ]
        ref_input_utxos = (
            [
                self.get_utxo_from_txid(input.transaction_id, input.index)
                for input in tx.transaction_body.reference_inputs
            ]
            if tx.transaction_body.reference_inputs is not None
            else []
        )
        script_invocations = generate_script_contexts_resolved(
            tx, input_utxos, ref_input_utxos, lambda s: self.posix_from_slot(s)
        )
        ret = {}
        for invocation in script_invocations:
            # run opshin script if available
            if self.opshin_scripts.get(invocation.script) is not None:
                opshin_validator = self.opshin_scripts[invocation.script]
                evaluate_opshin_validator(opshin_validator, invocation)
            redeemer = invocation.redeemer
            if redeemer.ex_units.steps <= 0 and redeemer.ex_units.mem <= 0:
                redeemer.ex_units = ExecutionUnits(
                    self.protocol_param.max_tx_ex_mem,
                    self.protocol_param.max_tx_ex_steps,
                )

            res, (cpu, mem), logs = evaluate_script(invocation)
            if isinstance(res, Exception):
                raise res
            key = f"{redeemer.tag.name.lower()}:{redeemer.index}"
            ret[key] = ExecutionUnits(mem, cpu)
        return ret

    def evaluate_tx_cbor(self, cbor: Union[bytes, str]) -> Dict[str, ExecutionUnits]:
        return self.evaluate_tx(Transaction.from_cbor(cbor))

    def wait(self, slots):
        self._last_block_slot += slots

    def posix_from_slot(self, slot: int) -> int:
        """Convert a slot to POSIX time (seconds)"""
        return self.genesis_param.system_start + self.genesis_param.slot_length * slot

    def slot_from_posix(self, posix: int) -> int:
        """Convert POSIX time (seconds) to the last slot"""
        return (
            posix - self.genesis_param.system_start
        ) // self.genesis_param.slot_length


class MockUser:
    def __init__(self, context: MockChainContext):
        self.context = context
        self.signing_key = PaymentSigningKey.generate()
        self.verification_key = PaymentVerificationKey.from_signing_key(
            self.signing_key
        )
        self.network = self.context.network
        self.address = Address(
            payment_part=self.verification_key.hash(), network=self.network
        )

    def fund(self, amount: Union[int, Value]):
        self.context.add_txout(
            TransactionOutput(self.address, amount),
        )

    def utxos(self):
        return self.context.utxos(self.address)

    def balance(self) -> Value:
        return sum([utxo.output.amount for utxo in self.utxos()], start=Value())
