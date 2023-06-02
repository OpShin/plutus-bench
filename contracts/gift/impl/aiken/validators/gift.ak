use aiken/hash.{Blake2b_224, Hash}
use aiken/list
use aiken/transaction.{ScriptContext, Transaction}
use aiken/transaction/credential.{VerificationKey}

validator {
  fn gift(
    datum: Hash<Blake2b_224, VerificationKey>,
    _redeemer: Void,
    ctx: ScriptContext,
  ) -> Bool {
    let ScriptContext { transaction: Transaction { extra_signatories, .. }, .. } =
      ctx

    list.has(extra_signatories, datum)
  }
}
