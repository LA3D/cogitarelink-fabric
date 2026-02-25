HURL     := hurl
PYTHON   := ~/uvws/.venv/bin/python
GATEWAY  := https://bootstrap.cogitarelink.ai
OXIGRAPH := http://localhost:7878
CA_CERT  := ../caddy-root.crt
# Combined CA bundle: Caddy internal CA + system CAs (required for LLM API calls)
CA_BUNDLE := /tmp/cogitarelink-ca-bundle.pem

.PHONY: test-hurl-p1 test-hurl-p2 test-unit test-fast test test-all ca-bundle

ca-bundle:
	cat $(CA_CERT) /etc/ssl/cert.pem > $(CA_BUNDLE)

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

# Fast: unit tests only (no Docker, no slow tests) — ~2s
test-fast:
	$(PYTHON) -m pytest pytest/unit/ -v -m "not slow"

# Unit tests (all, including slow-marked)
test-unit: ca-bundle
	SSL_CERT_FILE=$(CA_BUNDLE) FABRIC_GATEWAY=$(GATEWAY) \
	  $(PYTHON) -m pytest pytest/ -v

# Default: phase1 HURL + unit tests
test: test-hurl-p1 test-unit

# Full: all HURL phases + all pytest
test-all: test-hurl-p1 test-hurl-p2 test-unit
