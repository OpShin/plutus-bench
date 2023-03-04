<div align="center">
<img alt="A person with the Cardano logo as face, lifting heavy weights" src="plutus-bench.png" width="240" />
<h1>Plutus-Bench</h1>
</div>

A repository that lets Smart Contract languages compete via unified benchmarks.


## Structure

```
contracts/
├── <contract name 1>/
│   ├── impl/
│   │   ├── <language name 1>
│   │   │   └── make*
│   │   ├── <language name 2>
│   │   ...
│   ├── bench*
│   └── bench_all*
├── <contract name 2>/
...
├── bench*
└── bench_all*
```

The `contracts` folder contains subdirectories, each representing a smart contract use case.
Each use-case describes as precisely as possible what the corresponding contract is supposed to do.

It is accompanied usually by a reference implementation (preferably in [PlutusTx](https://plutus.readthedocs.io/en/latest/))
and a number of test cases in the folder `src`, usually written with [naumachia](https://github.com/MitchTurner/naumachia).
The contract also contains a `bench` and `bench_all` executable that run the tests
for the contract and output the results in machine-readable format.

```bash
$ cd contracts/always-succeeds
$ ./bench eopsin
pass,160,2045491,7702
$ ./bench_all
aiken,pass,15,517656,2001
eopsin,pass,160,2045491,7702
hebi,pass,28,713100,3200
```

Each subdirectoy contains one folder `impl` with subdirectories for each Smart Contract language that implemented the
given specification, along with a an executable called `make` that prints to stdout
the content of a JSON description of the Smart Contract (compatible with the  `cardano-cli`, often denoted `x.plutus`).

```bash
$ cd contracts/always-succeeds/impl/eopsin
$ ./make
{"type": "PlutusScriptV2", "description": "Eopsin 0.9.1 Smart Contract", "cborHex": "589e589c01000022232498c8c8cccc0049262498926002533001488101000013263357389201144e616d654572726f723a2076616c696461746f7200498c8c8c8894ccd5cd19b8f002488101000011003133004002001222232498c8004ccc888894ccd5cd19b8f00248810103001100315333573466e3c00922010102001100415333573466e3c0092201010100110051330060020010040030020012200101"}
```

## Running

To run all tests for all contracts, execute `bench_all`.
To benchmark a specific contract, execute `bench contract`.

```bash
$ bench always-succeeds
aiken,pass,15,517656,2001
eopsin,pass,160,2045491,7702
hebi,pass,28,713100,3200
$ bench_all
always-succeeds,aiken,pass,15,517656,2001
always-succeeds,eopsin,pass,160,2045491,7702
always-succeeds,hebi,pass,28,713100,3200
```
