# D30 Caddy HTTPS Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Caddy as a TLS-terminating reverse proxy, migrate NODE_BASE to `https://bootstrap.cogitarelink.ai`, and update all tests — establishing the HTTPS trust chain required by did:webvh and as prerequisite for D13/D14 VC-gated SPARQL access.

**Architecture:** Caddy sits in front of fabric-node in Docker Compose, terminating TLS with `tls internal`. All inter-service communication within Docker stays HTTP. NODE_BASE and NODE_DOMAIN env vars move to the new domain. Tests are updated to use the new base URL and CA cert.

**Tech Stack:** Caddy 2, Docker Compose, HURL, pytest/httpx, macOS Keychain

**Prerequisites:**
- `/etc/hosts` already contains `127.0.0.1 bootstrap.cogitarelink.ai` ✅
- Docker stack currently running on `http://localhost:8080`

---

### Task 1: Create the Caddyfile

**Files:**
- Create: `fabric/caddy/Caddyfile`

**Step 1: Create the directory and Caddyfile**

```bash
mkdir -p fabric/caddy
```

```
# fabric/caddy/Caddyfile
bootstrap.cogitarelink.ai {
    tls internal
    reverse_proxy fabric-node:8080
}
```

**Step 2: Verify file exists**

```bash
cat fabric/caddy/Caddyfile
```
Expected: prints the Caddyfile content.

**Step 3: Commit**

```bash
git add fabric/caddy/Caddyfile
git commit -m "feat: add Caddyfile for D30 HTTPS migration (tls internal)"
```

---

### Task 2: Add Caddy to docker-compose.yml and update environment

**Files:**
- Modify: `docker-compose.yml`

**Step 1: Edit docker-compose.yml**

Replace the entire `docker-compose.yml` with this (only changes are: new `caddy` service, updated env vars on fabric-node and credo-sidecar, new volumes):

```yaml
services:
  oxigraph:
    image: ghcr.io/oxigraph/oxigraph:latest
    ports:
      - "7878:7878"
    volumes:
      - oxigraph-data:/data
    command: serve --location /data --bind 0.0.0.0:7878
    healthcheck:
      test: ["CMD", "/usr/local/bin/oxigraph", "query", "--location", "/data",
             "--query", "SELECT * WHERE {} LIMIT 1", "--results-format", "tsv"]
      interval: 5s
      timeout: 3s
      retries: 5
      start_period: 10s

  fabric-node:
    build: ./fabric/node
    ports:
      - "8080:8080"
    environment:
      OXIGRAPH_URL: http://oxigraph:7878
      NODE_BASE: https://bootstrap.cogitarelink.ai
      CREDO_URL: http://credo-sidecar:3000
      SHARED_DIR: /shared
    volumes:
      - ./shapes:/app/shapes:ro
      - ./ontology:/app/ontology:ro
      - ./sparql:/app/sparql:ro
      - did-data:/shared:ro
    depends_on:
      oxigraph:
        condition: service_healthy

  credo-sidecar:
    build: ./fabric/credo
    platform: linux/amd64
    ports:
      - "3000:3000"
    environment:
      PORT: "3000"
      WALLET_KEY: "fabric-dev-key-change-in-production"
      NODE_DOMAIN: "bootstrap.cogitarelink.ai"
      NODE_BASE: "https://bootstrap.cogitarelink.ai"
      GATEWAY_INTERNAL: "http://fabric-node:8080"
      SHARED_DIR: /shared
    volumes:
      - did-data:/shared
    depends_on:
      oxigraph:
        condition: service_healthy
      fabric-node:
        condition: service_started

  caddy:
    image: caddy:2
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./fabric/caddy/Caddyfile:/etc/caddy/Caddyfile
      - caddy-data:/data
      - caddy-config:/config
    depends_on:
      - fabric-node

volumes:
  oxigraph-data:
  did-data:
  caddy-data:
  caddy-config:
```

**Step 2: Verify the diff looks right**

```bash
git diff docker-compose.yml
```
Expected: NODE_BASE and NODE_DOMAIN changed from `localhost:8080` to `bootstrap.cogitarelink.ai`, caddy service added, two new volumes added.

**Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: add Caddy service and update NODE_BASE to https://bootstrap.cogitarelink.ai"
```

---

### Task 3: Reset volumes and rebuild the stack

The DID was minted with `localhost:8080` — the `did-data` volume must be wiped so it remints with the new domain.

**Step 1: Tear down and destroy all volumes**

```bash
docker compose down -v
```
Expected: all containers stopped, all volumes removed including `did-data`.

**Step 2: Rebuild and start**

```bash
docker compose up -d --build
```
Expected: builds fabric-node and credo-sidecar images, starts all 4 services.

**Step 3: Wait for bootstrap to complete**

```bash
docker compose logs -f fabric-node 2>&1 | grep -m1 "Bootstrap complete"
```
Expected: `Bootstrap complete.` appears within ~30 seconds. Ctrl-C after it appears.

**Step 4: Verify the new DID domain**

```bash
docker compose logs credo-sidecar | grep "Node DID"
```
Expected: `Node DID created: did:webvh:...:bootstrap.cogitarelink.ai` — NOT `localhost`.

**Step 5: Verify HTTPS endpoint responds (will fail cert check until Task 4)**

```bash
curl -k https://bootstrap.cogitarelink.ai/.well-known/void | head -5
```
Expected: returns Turtle content (with `-k` to skip cert check for now).

---

### Task 4: Extract and trust Caddy's CA on macOS

**Step 1: Extract the Caddy root CA certificate**

```bash
docker cp \
  $(docker compose ps -q caddy):/data/caddy/pki/authorities/local/root.crt \
  ./caddy-root.crt
```
Expected: `caddy-root.crt` file created in repo root.

**Step 2: Add to macOS System Keychain (prompts for password)**

```bash
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain \
  caddy-root.crt
```
Expected: prompts for macOS password, then exits silently on success.

**Step 3: Verify curl accepts the cert without -k**

```bash
curl https://bootstrap.cogitarelink.ai/.well-known/void | head -5
```
Expected: returns Turtle content WITHOUT `-k`. If still failing, restart the terminal (macOS keychain changes sometimes need a new process).

**Step 4: Add caddy-root.crt to .gitignore**

```bash
echo "caddy-root.crt" >> .gitignore
git add .gitignore
git commit -m "chore: gitignore caddy-root.crt (machine-specific CA cert)"
```

---

### Task 5: Update the HURL test Makefile

**Files:**
- Modify: `tests/Makefile`

**Step 1: Update Makefile**

```makefile
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
```

**Step 2: Run phase 1 HURL tests to check for failures**

```bash
cd tests && make test-hurl-p1 2>&1 | tail -20
```
Expected: some tests may fail due to hardcoded URLs inside SPARQL query bodies — those get fixed in Task 6.

**Step 3: Commit**

```bash
git add tests/Makefile
git commit -m "feat: update HURL Makefile for HTTPS gateway and CA cert"
```

---

### Task 6: Fix hardcoded localhost URLs in HURL tests

These 7 HURL test files embed `http://localhost:8080` inside SPARQL query bodies (not the request URL — those already use `{{gateway}}`). They need to use `{{gateway}}` as a variable inside SPARQL strings too.

**Files:**
- Modify: `tests/hurl/phase1/05-sosa-data.hurl`
- Modify: `tests/hurl/phase1/07-entity-deref.hurl`
- Modify: `tests/hurl/phase1/14-entity-content-negotiation.hurl`
- Modify: `tests/hurl/phase2/24-credo-vc-verify.hurl`

Credo tests (`02b-credo-health.hurl`, `20-credo-did-create.hurl`, `20b-credo-did-log.hurl`, `22-credo-vc-issue.hurl`, `25-credo-vc-verify-negative.hurl`, `26-credo-vc-issue-400.hurl`) hit `localhost:3000` directly — Credo is not behind Caddy, so these stay as-is.

**Step 1: Fix phase1/05-sosa-data.hurl — replace hardcoded URLs**

Open `tests/hurl/phase1/05-sosa-data.hurl` and replace every occurrence of `http://localhost:8080` with `{{gateway}}`.

```bash
sed -i '' 's|http://localhost:8080|{{gateway}}|g' tests/hurl/phase1/05-sosa-data.hurl
```

**Step 2: Fix phase1/07-entity-deref.hurl**

```bash
sed -i '' 's|http://localhost:8080|{{gateway}}|g' tests/hurl/phase1/07-entity-deref.hurl
```

**Step 3: Fix phase1/14-entity-content-negotiation.hurl**

```bash
sed -i '' 's|http://localhost:8080|{{gateway}}|g' tests/hurl/phase1/14-entity-content-negotiation.hurl
```

**Step 4: Fix phase2/24-credo-vc-verify.hurl**

This test fetches the conformance VC from `http://localhost:8080` then sends it to Credo. Fix the gateway URL only (leave `localhost:3000` alone):

```bash
sed -i '' 's|http://localhost:8080|{{gateway}}|g' tests/hurl/phase2/24-credo-vc-verify.hurl
```

**Step 5: Verify no more hardcoded gateway URLs remain**

```bash
grep -rn "http://localhost:8080" tests/hurl/
```
Expected: no output (zero matches).

**Step 6: Run phase 1 and phase 2 HURL tests**

```bash
cd tests && make test-hurl-p1 && make test-hurl-p2
```
Expected: all tests pass.

**Step 7: Commit**

```bash
git add tests/hurl/
git commit -m "fix: replace hardcoded localhost:8080 with {{gateway}} variable in HURL tests"
```

---

### Task 7: Update pytest integration tests

The 4 integration test files have `GATEWAY = "http://localhost:8080"` hardcoded as a module-level constant. We update these to read from an environment variable (defaulting to the new HTTPS URL), and ensure httpx uses the Caddy CA cert.

**Files:**
- Create: `tests/pytest/integration/conftest.py`
- Modify: `tests/pytest/integration/test_fabric_discovery.py`
- Modify: `tests/pytest/integration/test_fabric_query.py`
- Modify: `tests/pytest/integration/test_fabric_validate.py`
- Modify: `tests/pytest/integration/test_fabric_agent.py`

**Step 1: Create conftest.py**

```python
# tests/pytest/integration/conftest.py
import os
import ssl
import pytest

GATEWAY = os.environ.get("FABRIC_GATEWAY", "https://bootstrap.cogitarelink.ai")
CA_CERT = os.environ.get("FABRIC_CA_CERT", "caddy-root.crt")


@pytest.fixture(scope="session")
def ssl_context():
    ctx = ssl.create_default_context()
    ctx.load_verify_locations(CA_CERT)
    return ctx
```

**Step 2: Update test_fabric_discovery.py**

Replace the module-level `GATEWAY` constant:

```python
# old
GATEWAY = "http://localhost:8080"

# new
import os
GATEWAY = os.environ.get("FABRIC_GATEWAY", "https://bootstrap.cogitarelink.ai")
```

Also update the two `FabricEndpoint(base="http://localhost:8080", ...)` constructions — these are unit-style tests constructing a stub endpoint, not hitting the live stack. Replace with:

```python
base=GATEWAY,
sparql_url=f"{GATEWAY}/sparql",
```

And update the assertion:
```python
# old
assert "http://localhost:8080" in plan
# new
assert GATEWAY in plan
```

**Step 3: Update test_fabric_query.py**

```python
# old
GATEWAY = "http://localhost:8080"

# new
import os
GATEWAY = os.environ.get("FABRIC_GATEWAY", "https://bootstrap.cogitarelink.ai")
```

Also update the inline SPARQL IRI that has the hardcoded URL:
```python
# old
"ASK { GRAPH <http://localhost:8080/ontology/sosa> { sosa:Observation a owl:Class } }"
# new
f"ASK {{ GRAPH <{GATEWAY}/ontology/sosa> {{ sosa:Observation a owl:Class }} }}"
```

**Step 4: Update test_fabric_validate.py**

```python
# old
GATEWAY = "http://localhost:8080"

# new
import os
GATEWAY = os.environ.get("FABRIC_GATEWAY", "https://bootstrap.cogitarelink.ai")
```

**Step 5: Update test_fabric_agent.py**

```python
# old
GATEWAY = "http://localhost:8080"

# new
import os
GATEWAY = os.environ.get("FABRIC_GATEWAY", "https://bootstrap.cogitarelink.ai")
```

**Step 6: Set SSL_CERT_FILE and run integration tests**

```bash
SSL_CERT_FILE=./caddy-root.crt pytest tests/pytest/integration/ -v
```
Expected: all integration tests pass.

**Step 7: Commit**

```bash
git add tests/pytest/integration/
git commit -m "fix: update integration tests for HTTPS gateway and CA cert"
```

---

### Task 8: Run the full test suite and verify

**Step 1: Run full pytest suite**

```bash
SSL_CERT_FILE=./caddy-root.crt pytest tests/ -v 2>&1 | tail -10
```
Expected: `205 passed` (same count as before).

**Step 2: Run full HURL suite**

```bash
cd tests && make test-all
```
Expected: all 42 HURL tests pass (15 phase1 + 27 phase2).

**Step 3: Verify the DID document is served correctly over HTTPS**

```bash
curl https://bootstrap.cogitarelink.ai/.well-known/did.json | python3 -m json.tool | grep '"id"'
```
Expected: `"id": "did:webvh:...:bootstrap.cogitarelink.ai"` — the domain in the DID matches the HTTPS domain.

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete D30 Caddy HTTPS migration — bootstrap.cogitarelink.ai"
```

---

### Task 9: Update MEMORY.md

**Files:**
- Modify: `.claude/memory/MEMORY.md`

Update the Project State section to reflect D30 complete, NODE_BASE change, and test count. Add D30 patterns to Key Architecture Patterns.

```
## Project State (as of 2026-02-26)
**Tests**: 205 unit + 42 HURL — all passing
**NODE_BASE**: https://bootstrap.cogitarelink.ai (D30)
**DID domain**: bootstrap.cogitarelink.ai
```

Add to Key Architecture Patterns:
```
- Caddy `tls internal`: reverse proxy at :443 → fabric-node :8080; NODE_BASE=https://bootstrap.cogitarelink.ai; cert at caddy-data:/data/caddy/pki/authorities/local/root.crt; trust once in macOS Keychain; SSL_CERT_FILE=./caddy-root.crt for pytest; --cacert for HURL
- Production switch: remove `tls internal` from Caddyfile, add Namecheap A record → server IP; Caddy auto-gets LE cert
```

**Commit**

```bash
git add .claude/memory/MEMORY.md
git commit -m "docs: update MEMORY.md for D30 HTTPS migration"
```
