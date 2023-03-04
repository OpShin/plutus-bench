{-# LANGUAGE TemplateHaskell #-}
{-# LANGUAGE DeriveGeneric #-}
module Main where

import Onchain (validateSerialized)
import Data.Aeson.TH (deriveJSON, defaultOptions, fieldLabelModifier)
import Data.Aeson.Text (encodeToLazyText)
import qualified Data.Text.Lazy.IO as I
import GHC.Generics (Generic)
import Prelude

data Script = Script {type' :: String, description :: String, cborHex :: String} deriving (Show, Generic)


$(deriveJSON defaultOptions {fieldLabelModifier = \x -> if x == "type'" then "type" else x} ''Script)

scripts :: Script
scripts = Script {type' = "PlutusScriptV2", description = "", cborHex = validateSerialized}

main :: IO ()
main = do
  I.writeFile "script.plutus" (encodeToLazyText scripts)
  putStrLn "Scripts compiled"