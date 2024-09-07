#!/usr/bin/env bash

# This script is used to build the contracts in the contracts directory.

# Get the path of own directory
DIR=$(dirname "${BASH_SOURCE[0]}")
cd $DIR

opshin build spending contracts/gift.py