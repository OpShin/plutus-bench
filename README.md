<div align="center">
<img alt="A person with the Cardano logo as face, lifting heavy weights" src="plutus-bench.png" width="240" />
<h1>Plutus-Bench</h1>
</div>

Comparable, unified benchmark for Cardano Smart Contract languages.

## Running

To run all tests for all contracts, execute `bench_all`.
To benchmark a specific contract, execute `bench <contract>`.

```bash
$ bench always-succeeds
aiken,spend,pass,15,517656,2001
hebi,spend,pass,28,713100,3200
helios,spend,pass,8,230100,1100
opshin,spend,pass,160,2045491,7702
plu-ts,spend,pass,8,230100,1100
plutus-tx,spend,pass,1896,98491633,321400
pluto,spend,pass,8,230100,1100

$ bench_all
always-succeeds,aiken,spend,pass,15,517656,2001
...
always-succeeds,uplc,spend,pass,8,230100,1100
gift,plutus-tx,spend,pass,1896,98491633,321400
gift,opshin,spend,pass,488,25670834,69870
gift,hebi,spend,pass,287,21317688,59373
...
```

## Structure

```
contracts/
├── <contract name 1>/
│   ├── impl/
│   │   ├── <language name 1>
│   │   │   └── make*
│   │   ├── <language name 2>
│   │   ...
│   ├── README.md
│   ├── bench*
│   └── bench_all*
├── <contract name 2>/
...
├── bench*
└── bench_all*
```

The `contracts` folder contains subdirectories, each representing a smart contract use case.
Each use-case describes as precisely as possible what the corresponding contract is supposed to do.
The description _must_ be contained in `README.md`.

The contract _must_ also contain executables `bench` and `bench_all`.
They run tests and benchmarks for the contract and output the results in machine-readable format.

The contract _may_ be accompanied by a reference implementation (preferably in [PlutusTx](https://plutus.readthedocs.io/en/latest/)).
The recommended way for writing tests and benchmarks is currently using [naumachia](https://github.com/MitchTurner/naumachia).

The output of the tests is in CSV with the following columns.

1. name of the test
1. `pass` or `fail`
1. script size in bytes
1. cpu steps consumed
1. memory consumed

Example output can be found below

```bash
$ cd contracts/always-succeeds
$ ./bench opshin
spend,pass,160,2045491,7702
$ ./bench_all
aiken,spend,pass,15,517656,2001
hebi,spend,pass,28,713100,3200
helios,spend,pass,8,230100,1100
opshin,spend,pass,160,2045491,7702
pluto,spend,pass,8,230100,1100
plutus-tx,spend,pass,1896,98491633,321400
```

Each subdirectoy contains one folder `impl` with subdirectories for each Smart Contract language that implemented the
given specification.
Each subfolder _must_ contain an executable `make` that prints to stdout
the content of a JSON description of the Smart Contract (compatible with the  `cardano-cli`, often denoted `script.plutus`).

Example output:

```bash
$ cd contracts/always-succeeds/impl/opshin
$ ./make
{"type": "PlutusScriptV2", "description": "opshin 0.9.14 Smart Contract", "cborHex": "589e589c01000022232498c8c8cccc0049262498926002533001488101000013263357389201144e616d654572726f723a2076616c696461746f7200498c8c8c8894ccd5cd19b8f002488101000011003133004002001222232498c8004ccc888894ccd5cd19b8f00248810103001100315333573466e3c00922010102001100415333573466e3c0092201010100110051330060020010040030020012200101"}
```
