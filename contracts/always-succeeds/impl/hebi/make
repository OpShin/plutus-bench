#! /bin/bash

set -e

python3.8 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -q


hebi build always_succeeds.py > /dev/null
cat always_succeeds/script.plutus