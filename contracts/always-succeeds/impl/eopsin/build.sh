#! /bin/bash

set -e

mkdir -p .tmp
python3.8 -m venv .tmp/venv
source .tmp/venv/bin/activate
pip install -r requirements.txt


eopsin build always_succeeds.py -o .tmp > /dev/null
cat .tmp/script.plutus