import { Address, deserializeUplc, Datum, Tx, TxId, TxOutput, UTxO, Value, ConstrData, WalletEmulator, NetworkEmulator, NetworkParams } from "@hyperionbt/helios";
import { readFileSync } from "fs";

import readline from "readline";

const rl = readline.createInterface({input: process.stdin, output: process.stdout});
let plutusScriptRaw = ""
rl.on("line", (line) => {
    plutusScriptRaw += line;
})
rl.on("close", () => {
    // Read contract
    const plutusScript = deserializeUplc(plutusScriptRaw);
    const scriptAddress = Address.fromHashes(plutusScript.validatorHash, null, false);
    const unitDatum = new ConstrData(0n, []);
    const wallet = new WalletEmulator(new NetworkEmulator(0));
    const ownerDatum = wallet.pubKeyHash;

    // Build (successful) tx
    let tx = new Tx();
    // Script input
    tx.addInput(
        new UTxO(TxId.fromHex("0000000000000000000000000000000000000000000000000000000000000000"), 0n, new TxOutput(scriptAddress, new Value(10000000n), Datum.inline(ownerDatum))),
        unitDatum,
    );
    tx.attachScript(plutusScript);
    tx.addSigner(wallet.pubKeyHash);
    // aux inputs
    tx.addCollateral(new UTxO(TxId.fromHex("0000000000000000000000000000000000000000000000000000000000000001"), 0n, new TxOutput(wallet.address, new Value(10000000n))));
    const params = readFileSync("src/mainnet.json", "utf8");
    tx.finalize(
        new NetworkParams(JSON.parse(params)),
        wallet.address,
        [new UTxO(TxId.fromHex("0000000000000000000000000000000000000000000000000000000000000002"), 0n, new TxOutput(wallet.address, new Value(10000000n)))],
    ).then((tx) => console.log(tx.toCbor()));
})