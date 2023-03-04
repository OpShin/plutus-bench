import { PPubKeyHash, PScriptContext, Script, ScriptType, bool, compile, data, makeValidator, pfn, pmakeUnit, unit } from "@harmoniclabs/plu-ts"

const alwaysSucceds = pfn([
    PPubKeyHash.type,
    data,
    PScriptContext.type
],  bool)
(( giftTo, _rdmr, ctx ) =>
    ctx.extract("txInfo").in( ({ txInfo }) => 
    txInfo.extract("signatories").in( ({ signatories }) =>
    
        signatories.some( giftTo.eqTerm )
    ))
)

const compiled = compile(
    makeValidator(
        alwaysSucceds
    )    
);

const script = new Script(
    ScriptType.PlutusV2,
    compiled
);

console.log(
    JSON.stringify( script.toJson() )
);