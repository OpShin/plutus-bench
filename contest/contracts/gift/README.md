# Gift contract

A spending contract that requires a single datum to be locked with funds.
The datum is just the pubkeyhash (bytes) that is allowed to spend the funds.

The contract should fail if the given pubkeyhash is not among the signatories of the contract.

> TODO This contract needs test cases!