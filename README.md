<div align="center">
<img alt="A person with the Cardano logo as face, lifting heavy weights" src="plutus-bench.png" width="240" />
<h1>Plutus-Bench</h1>
</div>

Test and benchmark Plutus Smart Contracts.
This project enables you to construct entire smart contract transactions against a mock environment, and measure the correctness (i.e. unit test) and performance of your smart contracts.

Plutus Bench creates a mock ledger with an arbitrary UTxO set specified by the user.
It then hosts a mock blockfrost API to interact with the ledger, supporting popular off-chain tooling
like [translucent](https://github.com/antibody-cardano/translucent) and [pycardano](https://pycardano.readthedocs.io/en/latest/).

> Note: Plutus Bench is currently a Work In Progress, and is not yet ready for production use.

### Why Plutus Bench?

- **Compatability**: Plutus Bench is written in Python, and is compatible with popular off-chain tooling relying on BlockFrost APIs. Ogmios mocking is also planned.
- **Holistic Testing**: Plutus Bench allows you to test the entire lifecycle of a smart contract, from minting to consuming, in a single test.
- **Simple**: Plutus Bench is designed to be simple to use, and easy to integrate with your existing infrastructure.

### Similar Projects

- [lucid transaction emulator](https://lucid.spacebudz.io/) - Allows emulation of transactions on the Cardano blockchain. Only supports JavaScript and TypeScript.
- [helios transaction emulator](https://github.com/hyperion-bt/helios) - Allows emulation of transactions on the Cardano blockchain. Only supports JavaScript and TypeScript.
- [plutus simple model](https://github.com/mlabs-haskell/plutus-simple-model) - Allows evaluating Plutus smart contracts. Only supports Haskell.

### What about the language comparison?

The language comparison has been moved to [contest](./contest).
It is planned to expand to cover different implementations of the same contract in different languages and the same language, tailored for performance optimizations.