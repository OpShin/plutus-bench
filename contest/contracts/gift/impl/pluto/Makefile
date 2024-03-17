SHELL := /bin/bash

all: script.plutus

venv: requirements.txt
	python3 -m venv venv
	source venv/bin/activate && pip install -r requirements.txt -q

pluto-bin:
	git clone https://github.com/Plutonomicon/pluto || true
	cd pluto
	# nix-build  # slower
	stack build pluto # less stable
	cp result/bin/pluto ../pluto-bin

script.cbor: validator.pluto pluto-bin
	./pluto-bin assemble validator.pluto | hexdump -e '/1 "%02x"' -v > script.cbor

script.plutus: venv script.cbor
	source venv/bin/activate && uplc build script.cbor --from-cbor > /dev/null
	cp script/script.plutus .

clean:
	rm -rf venv build script.plutus

.PHONY: clean