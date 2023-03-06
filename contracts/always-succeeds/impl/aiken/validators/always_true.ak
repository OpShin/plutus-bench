use aiken/transaction.{ScriptContext}

validator voting {
  fn(_voting_datum: Void, _redeemer: Void, _sc: ScriptContext) -> Bool {
    True
  }
}
