# Plutus-bench

A repository that lets Smart Contract languages compete with unified benchmarks.


### Structure

The `contracts` folder contains subdirectories, each representing a smart contract use case.
Each use-case describes as precisely as possible what the corresponding contract is supposed to do.

It is accompanied usually by a reference implementation (preferably in [PlutusTx](https://plutus.readthedocs.io/en/latest/))
and a number of test cases in the folder `src`, usually written with [naumachia](https://github.com/MitchTurner/naumachia).

Each subdirectoy contains one folder `impl` with subdirectories for each Smart Contract language that implemented the
given specification, along with a bash script called `build.sh` that prints to stdout
the content of a `script.cbor` file that contains the Smart Contract.
The script may write to `.tmp` within each directory.