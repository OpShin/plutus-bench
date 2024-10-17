import random
import traceback
import uuid
import warnings
from collections import defaultdict
from dataclasses import asdict
from typing import Any, Callable, Dict, List, Optional, Union

import cbor2
import pycardano
from blockfrost import Namespace
from blockfrost.utils import convert_json_to_object, convert_json_to_pandas
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
    script_hash,
    NativeScript,
    PlutusV1Script,
    PlutusV2Script,
    ScriptHash,
    BlockFrostChainContext,
    RawCBOR,
    RawPlutusData,
    datum_hash,
    default_encoder,
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


def request_wrapper(func):
    def error_wrapper(*args, **kwargs):
        request_response = func(*args, **kwargs)
        if "return_type" in kwargs:
            if kwargs["return_type"] == "object":
                return convert_json_to_object(request_response)
            elif kwargs["return_type"] == "pandas":
                return convert_json_to_pandas(request_response)
            elif kwargs["return_type"] == "json":
                return request_response
        else:
            return convert_json_to_object(request_response)

    return error_wrapper


def script_type(script: bytes) -> str:
    if isinstance(script, NativeScript):
        return "timelock"
    elif isinstance(script, PlutusV1Script):
        return "plutusV1"
    elif isinstance(script, PlutusV2Script) or type(script) is bytes:
        return "plutusV2"
    else:
        return "unknown"


def datum_to_cbor(d: pycardano.Datum) -> bytes:
    return cbor2.dumps(d, default=default_encoder)


def evaluate_opshin_validator(validator: OpshinValidator, invocation: ScriptInvocation):
    if invocation.redeemer.tag == RedeemerTag.SPEND:
        validator(invocation.datum, invocation.redeemer.data, invocation.script_context)
    elif invocation.redeemer.tag == RedeemerTag.MINT:
        validator(invocation.redeemer.data, invocation.script_context)
    else:
        raise NotImplementedError("Only spending and minting validators supported.")


class MockFrostApi:

    def __init__(
        self,
        protocol_param: Optional[ProtocolParameters] = None,
        genesis_param: Optional[GenesisParameters] = None,
        opshin_scripts: Optional[Dict[ScriptType, OpshinValidator]] = None,
        seed: int = 0,
    ):
        """
        A mock BlockFrost API that you can use for testing offchain code and evaluating scripts locally.

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
        self._scripts: Dict[ScriptHash, ScriptType] = {}
        # map from address to outputs
        self._utxo_state: Dict[str, List[UTxO]] = defaultdict(list)
        # map from utxo to address
        self._address_lookup: Dict[TransactionInput, str] = {}
        self._utxo_from_txid: Dict[TransactionId, Dict[int, UTxO]] = defaultdict(dict)
        self._network = Network.TESTNET
        self._epoch = 0
        self._last_block_slot = 0

    # these functions are convenience functions and for manipulating the state of the mock chain

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

    def set_block_slot(self, slot: int):
        self._last_block_slot = slot
        self._epoch = self._last_block_slot // self._genesis_param.epoch_length

    def _utxos(self, address: str | Address) -> List[UTxO]:
        return self._utxo_state.get(str(address), [])

    def add_utxo(self, utxo: UTxO):
        address = str(utxo.output.address)
        self._utxo_state[address].append(utxo)
        self._address_lookup[utxo.input] = address
        self._utxo_from_txid[utxo.input.transaction_id][utxo.input.index] = utxo
        # TODO properly determine the script type
        if utxo.output.script:
            self._scripts[script_hash(utxo.output.script)] = utxo.output.script

    def add_txout(self, txout: TransactionOutput) -> TransactionInput:
        """
        Basically the same as add_utxo, but clarifies that the transaction id does not matter.

        Returns:
            The input that can be used to spend the output.
        """
        utxo = UTxO(
            TransactionInput(TransactionId(self.random.randbytes(32)), 0), txout
        )
        self.add_utxo(utxo)
        return utxo.input

    def get_address(self, utxo: TransactionInput) -> str:
        return self._address_lookup[utxo]

    def remove_txi(self, txi: TransactionInput):
        del self._utxo_from_txid[txi.transaction_id][txi.index]
        address = self._address_lookup[txi]
        del self._address_lookup[txi]
        i = [
            i for i, utxo in enumerate(self._utxo_state[address]) if utxo.input == txi
        ][0]
        self._utxo_state[address].pop(i)

    def remove_utxo(self, utxo: UTxO):
        self.remove_txi(utxo.input)

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
        if isinstance(cbor, str):
            cbor = bytes.fromhex(cbor)
        return self.evaluate_tx(Transaction.from_cbor(cbor))

    def get_utxo_from_txid(self, transaction_id: TransactionId, index: int) -> UTxO:
        return self._utxo_from_txid[transaction_id][index]

    def wait(self, slots):
        self._last_block_slot += slots
        self._epoch = self._last_block_slot // self._genesis_param.epoch_length

    def posix_from_slot(self, slot: int) -> int:
        """Convert a slot to POSIX time (seconds)"""
        return self.genesis_param.system_start + self.genesis_param.slot_length * slot

    def slot_from_posix(self, posix: int) -> int:
        """Convert POSIX time (seconds) to the last slot"""
        return (
            posix - self.genesis_param.system_start
        ) // self.genesis_param.slot_length

    # These functions are supposed to overwrite the BlockFrost API

    @request_wrapper
    def epoch_latest(self, **kwargs):
        return {
            "epoch": self.epoch,
            # I suspect these values are not actually used by the client
            "start_time": self.posix_from_slot(
                self.epoch * self.genesis_param.epoch_length
            ),
            "end_time": self.posix_from_slot(
                (self.epoch + 1) * self.genesis_param.epoch_length
            ),
            "first_block_time": self.posix_from_slot(
                self.epoch * self.genesis_param.epoch_length
            ),
            "last_block_time": self.posix_from_slot(
                (self.epoch + 1) * self.genesis_param.epoch_length
            ),
            "block_count": 0,
            "tx_count": 0,
            "output": 0,
            "fees": 0,
            "active_stake": 0,
        }

    @request_wrapper
    def block_latest(self, **kwargs):
        return {
            "time": self.posix_from_slot(self.last_block_slot),
            "height": self.last_block_slot,
            "hash": "4ea1ba291e8eef538635a53e59fddba7810d1679631cc3aed7c8e6c4091a516a",
            "slot": self.last_block_slot,
            "epoch": self.epoch,
            "epoch_slot": self.last_block_slot % self.genesis_param.epoch_length,
            "slot_leader": "pool1pu5jlj4q9w9jlxeu370a3c9myx47md5j5m2str0naunn2qnikdy",
            "size": 0,
            "tx_count": 0,
            "output": 0,
            "fees": 0,
            "block_vrf": "vrf_vk1wf2k6lhujezqcfe00l6zetxpnmh9n6mwhpmhm0dvfh3fxgmdnrfqkms8ty",
            "op_cert": "da905277534faf75dae41732650568af545134ee08a3c0392dbefc8096ae177c",
            "op_cert_counter": 0,
            "previous_block": "4ea1ba291e8eef538635a53e59fddba7810d1679631cc3aed7c8e6c4091a516a",
            "next_block": "4ea1ba291e8eef538635a53e59fddba7810d1679631cc3aed7c8e6c4091a516a",
            "confirmations": 0,
        }

    @request_wrapper
    def genesis(self, **kwargs):
        return asdict(self.genesis_param)

    @request_wrapper
    def epoch_latest_parameters(self, **kwargs):
        return {
            "min_fee_b": str(self._protocol_param.min_fee_constant),
            "min_fee_a": str(self._protocol_param.min_fee_coefficient),
            "max_block_size": str(self._protocol_param.max_block_size),
            "max_tx_size": str(self._protocol_param.max_tx_size),
            "max_block_header_size": str(self._protocol_param.max_block_header_size),
            "key_deposit": str(self._protocol_param.key_deposit),
            "pool_deposit": str(self._protocol_param.pool_deposit),
            "a0": str(self._protocol_param.pool_influence),
            "rho": str(self._protocol_param.monetary_expansion),
            "tau": str(self._protocol_param.treasury_expansion),
            "decentralisation_param": str(self._protocol_param.decentralization_param),
            "extra_entropy": self._protocol_param.extra_entropy,
            "protocol_major_ver": str(self._protocol_param.protocol_major_version),
            "protocol_minor_ver": str(self._protocol_param.protocol_minor_version),
            "min_utxo": str(self._protocol_param.min_utxo),
            "min_pool_cost": str(self._protocol_param.min_pool_cost),
            "price_mem": str(self._protocol_param.price_mem),
            "price_step": str(self._protocol_param.price_step),
            "max_tx_ex_mem": str(self._protocol_param.max_tx_ex_mem),
            "max_tx_ex_steps": str(self._protocol_param.max_tx_ex_steps),
            "max_block_ex_mem": str(self._protocol_param.max_block_ex_mem),
            "max_block_ex_steps": str(self._protocol_param.max_block_ex_steps),
            "max_val_size": str(self._protocol_param.max_val_size),
            "collateral_percent": str(self._protocol_param.collateral_percent),
            "max_collateral_inputs": str(self._protocol_param.max_collateral_inputs),
            "coins_per_utxo_word": str(self._protocol_param.coins_per_utxo_word),
            "coins_per_utxo_size": str(self._protocol_param.coins_per_utxo_byte),
            "cost_models": {
                k: self._protocol_param.cost_models[k]
                for k in self._protocol_param.cost_models
            },
            "min_fee_ref_script_cost_per_byte": self._protocol_param.min_fee_reference_scripts["min_fee_ref_script_cost_per_byte"]
        }

    @request_wrapper
    def script(self, script_hash: str, **kwargs):
        script_hash = ScriptHash(bytes.fromhex(script_hash))
        if script_hash not in self._scripts:
            raise ValueError("Script not found")
        script = self._scripts[script_hash]
        return {
            "type": script_type(script),
            "script_hash": script_hash,
            "serialized_size": len(script),
        }

    @request_wrapper
    def script_cbor(self, script_hash: str, **kwargs):
        script_hash = ScriptHash(bytes.fromhex(script_hash))
        if script_hash not in self._scripts:
            raise ValueError("Script not found")
        return {"cbor": self._scripts[script_hash].hex()}

    @request_wrapper
    def script_json(self, script_hash: str, **kwargs):
        script_hash = ScriptHash(bytes.fromhex(script_hash))
        if script_hash not in self._scripts:
            raise ValueError("Script not found")
        return {"json": self._scripts[script_hash].to_dict()}

    @request_wrapper
    def address_utxos(self, address: str, **kwargs):
        l = []
        for utxo in self._utxos(address):
            amount_list = [
                {
                    "unit": "lovelace",
                    "quantity": str(utxo.output.amount.coin),
                }
            ]
            for pid, asset in utxo.output.amount.multi_asset.items():
                for name, amount in asset.items():
                    amount_list.append(
                        {
                            "unit": (pid.payload + name.payload).hex(),
                            "quantity": str(amount),
                        }
                    )
            l.append(
                {
                    "address": address,
                    "tx_hash": utxo.input.transaction_id.payload.hex(),
                    "tx_index": utxo.input.index,  # TODO deprecated
                    "output_index": utxo.input.index,
                    "amount": amount_list,
                    "block": "4ea1ba291e8eef538635a53e59fddba7810d1679631cc3aed7c8e6c4091a516a",
                    "data_hash": (
                        datum_hash(utxo.output.datum).payload.hex()
                        if utxo.output.datum
                        else (
                            utxo.output.datum_hash.payload.hex()
                            if utxo.output.datum_hash
                            else None
                        )
                    ),
                    "inline_datum": (
                        datum_to_cbor(utxo.output.datum).hex()
                        if utxo.output.datum
                        else None
                    ),
                    "reference_script_hash": (
                        utxo.output.script.hash().payload.hex()
                        if utxo.output.script
                        else None
                    ),
                }
            )

        return l

    @request_wrapper
    def transaction_submit_raw(self, tx_cbor: bytes, **kwargs):
        tx = Transaction.from_cbor(tx_cbor)
        self.submit_tx(tx)
        return tx.id.payload.hex()

    def transaction_submit(self, file_path: str, **kwargs):
        with open(file_path, "rb") as file:
            tx_cbor = file.read()
        return self.transaction_submit_raw(tx_cbor)

    @request_wrapper
    def transaction_evaluate_raw(self, tx_cbor: bytes, **kwargs):
        try:
            res = self.evaluate_tx_cbor(tx_cbor)
        except Exception as e:
            return {
                "result": {
                    "EvaluationFailure": str(e),
                    "Trace": traceback.format_exception(e),
                }
            }
        return {
            "result": {
                "EvaluationResult": {
                    k: {
                        "steps": v.steps,
                        "memory": v.mem,
                    }
                    for k, v in res.items()
                }
            }
        }

    def transaction_evaluate(self, file_path: str, **kwargs):
        with open(file_path, "r") as file:
            tx_cbor = file.read()
        return self.transaction_evaluate_raw(tx_cbor)


class MockChainContext(BlockFrostChainContext):
    def __init__(
        self,
        api: Optional[MockFrostApi] = None,
        network: Optional[Network] = None,
    ):
        if network is not None:
            warnings.warn(
                "`network` argument will be deprecated in the future. Directly passing `base_url` is recommended."
            )
            self._network = network
        else:
            self._network = Network.TESTNET

        self._project_id = ""
        self._base_url = ""
        self.api = api or MockFrostApi()
        self._epoch_info = self.api.epoch_latest()
        self._epoch = None
        self._genesis_param = None
        self._protocol_param = None


class MockUser:
    def __init__(self, api: MockFrostApi):
        self.api = api
        self.context = MockChainContext(self.api)
        self.signing_key = PaymentSigningKey.generate()
        self.verification_key = PaymentVerificationKey.from_signing_key(
            self.signing_key
        )
        self.network = self.api.network
        self.address = Address(
            payment_part=self.verification_key.hash(), network=self.network
        )

    def fund(self, amount: Union[int, Value]):
        self.api.add_txout(
            TransactionOutput(self.address, amount),
        )

    def utxos(self):
        return self.context.utxos(self.address)

    def balance(self) -> Value:
        return sum([utxo.output.amount for utxo in self.utxos()], start=Value())
