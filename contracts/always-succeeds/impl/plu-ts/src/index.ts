import { Script, ScriptType, compile, data, pfn, pmakeUnit, unit } from "@harmoniclabs/plu-ts"

const alwaysSucceds = pfn([
    data,
    data,
    data
],  unit)
(( _dat, _rdmr, _ctx ) => pmakeUnit() )

const compiled = compile( alwaysSucceds );

const script = new Script(
    ScriptType.PlutusV2,
    compiled
);

console.log(
    JSON.stringify( script.toJson() )
);