#! /bin/bash

(cd "impl/$1" && bash build.sh) | cargo run