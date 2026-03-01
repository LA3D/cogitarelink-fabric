HURL     := hurl
PYTHON   := ~/uvws/.venv/bin/python
GATEWAY  := https://bootstrap.cogitarelink.ai
OXIGRAPH := http://localhost:7878
CA_CERT  := ../caddy-root.crt

.PHONY: test-hurl-p1 test-hurl-p2 test-unit test test-all

test-hurl-p1:
	$(HURL) --test \
	  --variable gateway=$(GATEWAY) \
	  --variable oxigraph=$(OXIGRAPH) \
	  --cacert $(CA_CERT) \
	  hurl/phase1/*.hurl

test-hurl-p2:
	$(HURL) --test \
	  --variable gateway=$(GATEWAY) \
	  --cacert $(CA_CERT) \
	  hurl/phase2/*.hurl

test-unit:
	$(PYTHON) -m pytest pytest/ -v

test: test-hurl-p1 test-unit

test-all: test-hurl-p1 test-hurl-p2 test-unit
