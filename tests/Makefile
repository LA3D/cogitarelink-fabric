HURL    := hurl
PYTHON  := ~/uvws/.venv/bin/python
GATEWAY := http://localhost:8080
OXIGRAPH := http://localhost:7878

.PHONY: test-hurl-p1 test-hurl-p2 test-unit test test-all

test-hurl-p1:
	$(HURL) --test \
	  --variable gateway=$(GATEWAY) \
	  --variable oxigraph=$(OXIGRAPH) \
	  hurl/phase1/*.hurl

test-hurl-p2:
	$(HURL) --test \
	  --variable gateway=$(GATEWAY) \
	  hurl/phase2/*.hurl

test-unit:
	$(PYTHON) -m pytest pytest/ -v

test: test-hurl-p1 test-unit

test-all: test-hurl-p1 test-hurl-p2 test-unit
