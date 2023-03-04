module Onchain (validateSerialized) where

import Cardano.Api
import Cardano.Api.Shelley (PlutusScript (..))
import Codec.Serialise (serialise)
import qualified Data.ByteString.Base16 as B16
import qualified Data.ByteString.Char8 as C
import qualified Data.ByteString.Lazy as LBS
import qualified Data.ByteString.Short as SBS
import qualified Plutus.Script.Utils.V2.Scripts as Scripts
import qualified Plutus.Script.Utils.V2.Typed.Scripts.Validators as Scripts
import qualified Plutus.V2.Ledger.Api as Api
import Plutus.V2.Ledger.Contexts as Api
import qualified PlutusTx
import PlutusTx.Prelude
import Prelude (String)

-- | Validators ------------------------------------------------------------------

{-# INLINEABLE validate #-}
validate :: Api.PubKeyHash -> () -> Api.ScriptContext -> Bool
validate pk' _ p = Api.txSignedBy (Api.scriptContextTxInfo p) pk'


-- | Instantiate validators ------------------------------------------------------------------

validateCompiled :: Scripts.Validator
validateCompiled = Api.Validator $ Api.fromCompiledCode ($$(PlutusTx.compile [|| val ||]))
  where
    val = Scripts.mkUntypedValidator validate 


-- | Serialization ------------------------------------------------------------------

validateSerialized :: String
validateSerialized = C.unpack $ B16.encode $ serialiseToCBOR 
                        ((PlutusScriptSerialised $ SBS.toShort . LBS.toStrict $ serialise $ Api.unValidatorScript validateCompiled) :: PlutusScript PlutusScriptV2)

