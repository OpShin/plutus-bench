SHELL := /bin/bash

all: script.plutus

venv: requirements.txt
	python3 -m venv venv
	source venv/bin/activate && pip install -r requirements.txt -q

script.plutus: venv gift.py
	source venv/bin/activate && opshin build spending gift.py > /dev/null
	cp build/gift/script.plutus .

clean:
	rm -rf venv build script.plutus

.PHONY: clean