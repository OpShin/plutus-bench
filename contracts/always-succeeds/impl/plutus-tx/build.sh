#! /bin/bash

set -e

cabal build contract.cabal > /dev/null
cabal run > /dev/null

cat script.plutus