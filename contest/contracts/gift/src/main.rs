use naumachia::{
    scripts::{
        raw_script::PlutusScriptFile, raw_validator_script::plutus_data::PlutusData, ExecutionCost,
    },
    trireme_ledger_client::cml_client::plutus_data_interop::PlutusDataInterop,
};
use std::{
    io::{self, Read},
    str,
};

use naumachia::scripts::raw_validator_script::RawPlutusValidator;

use naumachia::scripts::context::{pub_key_hash_from_address_if_available, ContextBuilder};
use naumachia::scripts::ValidatorCode;
use naumachia::Address;

pub fn get_script() -> RawPlutusValidator<PlutusData, PlutusData> {
    let mut plutus_file = Vec::new();
    let mut stdin = io::stdin();
    stdin.read_to_end(&mut plutus_file).unwrap();
    let plutus_script: PlutusScriptFile =
        serde_json::from_str(str::from_utf8(&plutus_file).unwrap()).unwrap();

    return RawPlutusValidator::new_v2(plutus_script).unwrap();
}

pub fn test_spend(script: RawPlutusValidator<PlutusData, PlutusData>) -> Option<ExecutionCost> {
    let owner = Address::from_bech32("addr_test1qpmtp5t0t5y6cqkaz7rfsyrx7mld77kpvksgkwm0p7en7qum7a589n30e80tclzrrnj8qr4qvzj6al0vpgtnmrkkksnqd8upj0").unwrap();

    let script_addr = script.address(0).unwrap();

    let owner_pkh = pub_key_hash_from_address_if_available(&owner).unwrap();
    let ctx = ContextBuilder::new(owner_pkh.clone())
        .with_input(&vec![1], 0, &script_addr)
        .with_datum_hash_from_datum::<PlutusData>(owner_pkh.clone().into())
        .finish_input()
        .build_spend(&vec![1], 0);
    let cost = script
        .execute(owner_pkh.clone().into(), ().into(), ctx)
        .unwrap();
    return Some(cost);
}

pub fn test_fail(script: RawPlutusValidator<PlutusData, PlutusData>) -> Option<ExecutionCost> {
    let owner = Address::from_bech32("addr_test1qpmtp5t0t5y6cqkaz7rfsyrx7mld77kpvksgkwm0p7en7qum7a589n30e80tclzrrnj8qr4qvzj6al0vpgtnmrkkksnqd8upj0").unwrap();
    let other = Address::from_bech32("addr_test1qpy5a8ea64dz7p28hxzdwq7fltrghgant84j6gw3asam5hvx23v86j6cdz5fps95xxxhdtdprd45sfx0ta6sa4ykmsvsucxzk6").unwrap();

    let script_addr = script.address(0).unwrap();

    let owner_pkh = pub_key_hash_from_address_if_available(&owner).unwrap();
    let other_pkh = pub_key_hash_from_address_if_available(&other).unwrap();
    let ctx = ContextBuilder::new(owner_pkh.clone())
        .with_input(&vec![1], 0, &script_addr)
        .with_datum_hash_from_datum::<PlutusData>(other_pkh.clone().into())
        .finish_input()
        .build_spend(&vec![1], 0);
    let cost = script
        .execute(other_pkh.clone().into(), ().into(), ctx)
        .unwrap();
    return Some(cost);
}

fn main() {
    let script = get_script();

    let script_size = script.script_hex().unwrap().len() / 2;
    let cost = test_spend(script).unwrap();
    let cpu_steps = cost.cpu();
    let mem_steps = cost.mem();
    println!("spend,pass,{script_size},{cpu_steps},{mem_steps}");
}
