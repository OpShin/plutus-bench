import { PPubKeyHash, PScriptContext, Script, ScriptType, bool, compile, data, makeValidator, pfn } from "@harmoniclabs/plu-ts"

const giftContract = pfn([
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
        giftContract
    )    
);

const script = new Script(
    ScriptType.PlutusV2,
    compiled
);

console.log(
    JSON.stringify( script.toJson() )
);