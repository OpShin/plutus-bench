import uuid
from dataclasses import dataclass
import requests
from pycardano import (
    TransactionOutput,
    UTxO,
    TransactionInput,
    BlockFrostChainContext,
    Network,
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
            f"/{self.session_id}/ledger/txout", json={"tx_cbor": txout.to_cbor().hex()}
        )

    def del_txout(self, txout: TransactionInput) -> bool:
        return self.client._del(
            f"/{self.session_id}/ledger/txout",
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
            base_url=self.client.base_url + self.session_id + "/api",
            api_version="v1",
        )

    def chain_context(self, network=Network.TESTNET):
        return BlockFrostChainContext(
            project_id="",
            network=network,
            base_url=self.client.base_url + self.session_id + "/api",
        )


@dataclass
class MockFrostClient:
    base_url: str = "https://mockfrost.dev/"

    def __post_init__(self):
        self.base_url = self.base_url.rstrip("/") + "/"

    def _get(self, path: str, **kwargs):
        return requests.get(self.base_url + path, **kwargs).json()

    def _post(self, path: str, **kwargs):
        return requests.post(self.base_url + path, **kwargs).json()

    def _put(self, path: str, **kwargs):
        return requests.put(self.base_url + path, **kwargs).json()

    def _del(self, path: str, **kwargs):
        return requests.delete(self.base_url + path, **kwargs).json()

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
