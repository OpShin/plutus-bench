import uuid
from dataclasses import dataclass
from typing import Union

import requests
from pycardano import (
    TransactionOutput,
    UTxO,
    TransactionInput,
    BlockFrostChainContext,
    Network,
    PaymentSigningKey,
    PaymentVerificationKey,
    Address,
    Value,
)
from blockfrost import BlockFrostApi


@dataclass
class MockFrostSession:
    client: "MockFrostClient"
    session_id: str

    def info(self):
        return self.client._get(f"/session/{self.session_id}")

    def delete(self):
        return self.client._del(f"/session/{self.session_id}")

    def add_txout(self, txout: TransactionOutput) -> dict:
        return self.client._post(
            f"/{self.session_id}/ledger/txo", json={"tx_cbor": txout.to_cbor().hex()}
        )

    def del_txout(self, txout: TransactionInput) -> bool:
        return self.client._del(
            f"/{self.session_id}/ledger/txo",
            json={
                "tx_id": txout.transaction_id.payload.hex(),
                "output_index": txout.index,
            },
        )

    def add_utxo(self, utxo: UTxO) -> dict:
        return self.client._put(
            f"/{self.session_id}/ledger/utxo", json={"utxo": utxo.to_cbor().hex()}
        )

    def set_slot(self, slot: int) -> int:
        return self.client._put(f"/{self.session_id}/slot", json={"slot": slot})

    def blockfrost_api(self) -> BlockFrostApi:
        return BlockFrostApi(
            project_id="",
            base_url=self.client.base_url + "/" + self.session_id + "/api",
            api_version="v1",
        )

    def chain_context(self, network=Network.TESTNET):
        return BlockFrostChainContext(
            project_id="",
            network=network,
            base_url=self.client.base_url + "/" + self.session_id + "/api",
        )


@dataclass
class MockFrostClient:
    base_url: str = "https://mockfrost.dev"
    session: requests.Session = requests.Session()

    def __post_init__(self):
        self.base_url = self.base_url.rstrip("/")

    def _get(self, path: str, **kwargs):
        return self.session.get(self.base_url + path, **kwargs).json()

    def _post(self, path: str, **kwargs):
        return self.session.post(self.base_url + path, **kwargs).json()

    def _put(self, path: str, **kwargs):
        return self.session.put(self.base_url + path, **kwargs).json()

    def _del(self, path: str, **kwargs):
        return self.session.delete(self.base_url + path, **kwargs).json()

    def create_session(
        self, protocol_parameters=None, genesis_parameters=None
    ) -> MockFrostSession:
        session_id = self._post(
            "/session",
            json={
                "protocol_parameters": protocol_parameters,
                "genesis_parameters": genesis_parameters,
            },
        )
        return MockFrostSession(client=self, session_id=session_id)


class MockFrostUser:
    def __init__(self, api: MockFrostSession, network=Network.TESTNET):
        self.network = network
        self.api = api
        self.context = api.chain_context()
        self.signing_key = PaymentSigningKey.generate()
        self.verification_key = PaymentVerificationKey.from_signing_key(
            self.signing_key
        )
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
