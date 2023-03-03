use naumachia::scripts::raw_script::{BlueprintFile, PlutusScriptFile};
use std::{
    io::{self, Read},
    marker::PhantomData,
    str,
};
use uplc::{
    ast::{DeBruijn, Name, NamedDeBruijn, Program, Term},
    machine::cost_model::ExBudget,
    parser,
};

use naumachia::scripts::raw_validator_script::RawPlutusValidator;
use naumachia::scripts::{ScriptError, ScriptResult};
use naumachia::transaction::TransactionVersion;

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

fn main() {
    let script = get_script();

    let owner = Address::from_bech32("addr_test1qpmtp5t0t5y6cqkaz7rfsyrx7mld77kpvksgkwm0p7en7qum7a589n30e80tclzrrnj8qr4qvzj6al0vpgtnmrkkksnqd8upj0").unwrap();

    let owner_pkh = pub_key_hash_from_address_if_available(&owner).unwrap();
    let ctx = ContextBuilder::new(owner_pkh).build_spend(&vec![], 0);
    script.execute((), (), ctx).unwrap();
}
