use naumachia::{scripts::{raw_script::PlutusScriptFile, ExecutionCost, raw_validator_script::plutus_data::PlutusData}, trireme_ledger_client::cml_client::plutus_data_interop::PlutusDataInterop};
use std::{
    io::{self, Read},
    str,
};

use naumachia::scripts::raw_validator_script::RawPlutusValidator;

use naumachia::scripts::context::{pub_key_hash_from_address_if_available, ContextBuilder};
use naumachia::scripts::ValidatorCode;
use naumachia::Address;


pub fn get_script() -> RawPlutusValidator<(), ()> {
    let mut plutus_file = Vec::new();
    let mut stdin = io::stdin();
    stdin.read_to_end(&mut plutus_file).unwrap();
    let plutus_script: PlutusScriptFile =
        serde_json::from_str(str::from_utf8(&plutus_file).unwrap()).unwrap();

    return RawPlutusValidator::new_v2(plutus_script).unwrap();
}

pub fn test_spend(script: RawPlutusValidator<(), ()>) -> Option<ExecutionCost> {
    let owner = Address::from_bech32("addr_test1qpmtp5t0t5y6cqkaz7rfsyrx7mld77kpvksgkwm0p7en7qum7a589n30e80tclzrrnj8qr4qvzj6al0vpgtnmrkkksnqd8upj0").unwrap();

    let script_addr = script.address(0).unwrap();

    let owner_pkh = pub_key_hash_from_address_if_available(&owner).unwrap();
    let ctx = ContextBuilder::new(owner_pkh)
        .with_input(&vec![0], 0, &script_addr)
        .finish_input()
        .build_spend(&vec![1], 0);
    let ctx_data: PlutusData = ctx.clone().into();
    let ctx_json = serde_json::to_string(&ctx_data.to_plutus_data()).unwrap();
    println!("{}", ctx_json);
    let cost = script.execute((), (), ctx).unwrap();
    return Some(cost)
}

fn main() {
    let script = get_script();

    let script_size = script.script_hex().unwrap().len() / 2;
    let cost = test_spend(script).unwrap();
    let cpu_steps = cost.cpu();
    let mem_steps = cost.mem();
    println!("spend,pass,{script_size},{cpu_steps},{mem_steps}");
}
