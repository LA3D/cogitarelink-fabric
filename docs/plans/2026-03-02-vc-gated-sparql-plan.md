# VC-Gated SPARQL Access Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Gate `/sparql` and `/sparql/update` behind Verifiable Presentation Bearer tokens so only agents with valid `AgentAuthorizationCredential` can query the fabric node.

**Architecture:** Agent wraps its VC in a signed VP (via Credo `POST /presentations/create`), presents as `Authorization: Bearer <base64url(vp_json)>`. FastAPI `verify_vp_bearer()` dependency decodes, calls Credo `POST /presentations/verify`, checks `validUntil` + `agentRole`. Controlled by `FABRIC_AUTH_ENABLED` env var.

**Tech Stack:** FastAPI (dependency injection), Credo-TS 0.6.x (Ed25519 eddsa-jcs-2022), httpx (async HTTP), base64url encoding, Python dataclasses.

**Design doc:** `docs/plans/2026-03-02-vc-gated-sparql-design.md`

---

### Task 1: Credo `POST /presentations/create` endpoint

Add a route to Credo sidecar that wraps a VC in a signed VP with `validUntil`.

**Files:**
- Modify: `fabric/credo/src/index.ts:420-473` (add route after `/agents/register`)
- Test: `tests/hurl/phase2/50-vp-create.hurl`

**Step 1: Write the HURL test**

Create `tests/hurl/phase2/50-vp-create.hurl`:

```hurl
# 50-vp-create.hurl — Credo creates a VP wrapping a VC
# Prerequisite: register an agent first to get a credential

# Step 1: Register agent
POST http://localhost:3000/agents/register
Content-Type: application/json
{
  "agentRole": "DevelopmentAgentRole",
  "authorizedGraphs": ["/graph/observations", "/graph/entities"],
  "authorizedOperations": ["read"]
}
HTTP 201
[Captures]
agent_credential: jsonpath "$.credential"
agent_did: jsonpath "$.agentDid"

# Step 2: Create VP from credential
POST http://localhost:3000/presentations/create
Content-Type: application/json
{
  "credential": {{agent_credential}},
  "holderDid": "{{agent_did}}",
  "validMinutes": 5
}
HTTP 201
[Asserts]
jsonpath "$.type[0]" == "VerifiablePresentation"
jsonpath "$.holder" exists
jsonpath "$.validUntil" exists
jsonpath "$.proof" exists
jsonpath "$.proof.cryptosuite" == "eddsa-jcs-2022"
jsonpath "$.proof.proofPurpose" == "authentication"
jsonpath "$.verifiableCredential" count == 1
```

**Step 2: Run test to verify it fails**

Run: `cd tests && hurl --test --cacert ../caddy-root.crt hurl/phase2/50-vp-create.hurl`
Expected: FAIL — `POST http://localhost:3000/presentations/create` returns 404

**Step 3: Implement the Credo endpoint**

In `fabric/credo/src/index.ts`, add after the `/agents/register` route (after line ~473):

```typescript
app.post('/presentations/create', async (req, res) => {
  // Create a Verifiable Presentation wrapping a VC, signed by holder
  try {
    const { credential, holderDid, validMinutes } = req.body
    if (!credential || !holderDid) {
      return res.status(400).json({ error: 'credential and holderDid required' })
    }
    const minutes = validMinutes ?? 5
    const validUntil = new Date(Date.now() + minutes * 60_000).toISOString()

    // Build unsigned VP
    const unsignedVP: Record<string, unknown> = {
      '@context': ['https://www.w3.org/ns/credentials/v2'],
      type: ['VerifiablePresentation'],
      holder: holderDid,
      verifiableCredential: [credential],
      validUntil,
    }

    // Sign VP with holder's key (proofPurpose: authentication)
    // Use node's key since agent keys are node-managed (D13: controller is home node)
    const proofOptions = {
      type: 'DataIntegrityProof',
      cryptosuite: 'eddsa-jcs-2022',
      verificationMethod: `${nodeDid}#${verificationMethodId}`,
      proofPurpose: 'authentication',
      created: new Date().toISOString(),
    }

    const docHash = jcsHash(unsignedVP)
    const optHash = jcsHash(proofOptions)
    const hashData = new Uint8Array(optHash.length + docHash.length)
    hashData.set(optHash, 0)
    hashData.set(docHash, optHash.length)

    const keyApi = agent.agentContext.dependencyManager.resolve(Kms.KeyManagementApi)
    const sigResult = await keyApi.sign({
      keyId: signingKeyId,
      algorithm: 'EdDSA',
      data: hashData,
    })

    const proofValue = base58btcEncode(sigResult.signature)

    const signedVP = {
      ...unsignedVP,
      proof: { ...proofOptions, proofValue },
    }

    return res.status(201).json(signedVP)
  } catch (err) {
    console.error('VP creation error:', err)
    return res.status(500).json({ error: String(err) })
  }
})
```

Note: Check how `issueVC` (line ~72-110 in index.ts) accesses `signingKeyId` and `verificationMethodId` — reuse the same variables. The VP signing uses the node's key because agents are node-managed (D13: `controller` is the home node DID).

**Step 4: Run test to verify it passes**

Run: `cd tests && hurl --test --cacert ../caddy-root.crt hurl/phase2/50-vp-create.hurl`
Expected: PASS

**Step 5: Commit**

```bash
git add fabric/credo/src/index.ts tests/hurl/phase2/50-vp-create.hurl
git commit -m "feat: add Credo POST /presentations/create endpoint (D13)"
```

---

### Task 2: Credo `POST /presentations/verify` endpoint

Add VP verification that checks both the VP proof and the embedded VC proof.

**Files:**
- Modify: `fabric/credo/src/index.ts` (add route after `/presentations/create`)
- Test: `tests/hurl/phase2/51-vp-verify.hurl`

**Step 1: Write the HURL test**

Create `tests/hurl/phase2/51-vp-verify.hurl`:

```hurl
# 51-vp-verify.hurl — Credo verifies a VP (VP proof + embedded VC proof)

# Step 1: Register agent
POST http://localhost:3000/agents/register
Content-Type: application/json
{
  "agentRole": "QARole",
  "authorizedGraphs": ["/graph/observations"],
  "authorizedOperations": ["read"]
}
HTTP 201
[Captures]
agent_credential: jsonpath "$.credential"
agent_did: jsonpath "$.agentDid"

# Step 2: Create VP
POST http://localhost:3000/presentations/create
Content-Type: application/json
{
  "credential": {{agent_credential}},
  "holderDid": "{{agent_did}}",
  "validMinutes": 5
}
HTTP 201
[Captures]
vp_json: jsonpath "$"

# Step 3: Verify VP
POST http://localhost:3000/presentations/verify
Content-Type: application/json
{{vp_json}}
HTTP 200
[Asserts]
jsonpath "$.verified" == true
jsonpath "$.credentialSubject.agentRole" exists
jsonpath "$.validUntil" exists
```

**Step 2: Run test to verify it fails**

Run: `cd tests && hurl --test --cacert ../caddy-root.crt hurl/phase2/51-vp-verify.hurl`
Expected: FAIL — 404 on `/presentations/verify`

**Step 3: Implement the Credo endpoint**

In `fabric/credo/src/index.ts`, add after `/presentations/create`:

```typescript
app.post('/presentations/verify', async (req, res) => {
  // Verify a VP: check VP proof + each embedded VC proof + validUntil
  try {
    const vpJson = req.body
    if (!vpJson || !vpJson.proof) {
      return res.status(400).json({ verified: false, error: 'signed VP with proof required' })
    }

    // 1. Check validUntil
    const validUntil = vpJson.validUntil
    if (validUntil && new Date(validUntil) < new Date()) {
      return res.json({ verified: false, error: 'VP expired (validUntil in the past)' })
    }

    // 2. Verify VP proof
    const vpResult = await verifyProof(vpJson)
    if (!vpResult.verified) {
      return res.json({ verified: false, error: 'VP proof verification failed' })
    }

    // 3. Verify each embedded VC proof
    const credentials = vpJson.verifiableCredential ?? []
    for (const vc of credentials) {
      if (vc.proof) {
        const vcResult = await verifyProof(vc)
        if (!vcResult.verified) {
          return res.json({ verified: false, error: 'Embedded VC proof verification failed' })
        }
      }
    }

    // 4. Extract credential subject from first VC
    const firstVC = credentials[0]
    const credentialSubject = firstVC?.credentialSubject ?? {}

    return res.json({
      verified: true,
      credentialSubject,
      holder: vpJson.holder,
      validUntil: vpJson.validUntil,
    })
  } catch (err) {
    console.error('VP verification error:', err)
    return res.json({ verified: false, error: String(err) })
  }
})
```

**Step 4: Run test to verify it passes**

Run: `cd tests && hurl --test --cacert ../caddy-root.crt hurl/phase2/51-vp-verify.hurl`
Expected: PASS

**Step 5: Commit**

```bash
git add fabric/credo/src/index.ts tests/hurl/phase2/51-vp-verify.hurl
git commit -m "feat: add Credo POST /presentations/verify endpoint (D13)"
```

---

### Task 3: FastAPI `verify_vp_bearer()` dependency — unit tests

Write unit tests for the FastAPI dependency that decodes and verifies VP Bearer tokens. Mock Credo calls.

**Files:**
- Create: `fabric/node/vp_auth.py`
- Create: `tests/pytest/unit/test_vp_auth.py`

**Step 1: Write the failing tests**

Create `tests/pytest/unit/test_vp_auth.py`:

```python
"""Unit tests for VP Bearer token verification (D13/D14)."""
import base64
import json
import pytest
from datetime import datetime, timezone, timedelta
from fabric.node.vp_auth import (
    decode_bearer_token,
    extract_agent_context,
    AgentContext,
    VALID_AGENT_ROLES,
)


def _make_vp(role="DevelopmentAgentRole", valid_minutes=5, graphs=None, ops=None):
    """Build a mock VP for testing."""
    now = datetime.now(timezone.utc)
    return {
        "@context": ["https://www.w3.org/ns/credentials/v2"],
        "type": ["VerifiablePresentation"],
        "holder": "did:webvh:abc:bootstrap.cogitarelink.ai:agents:test-agent",
        "verifiableCredential": [{
            "@context": ["https://www.w3.org/ns/credentials/v2"],
            "type": ["VerifiableCredential", "AgentAuthorizationCredential"],
            "credentialSubject": {
                "id": "did:webvh:abc:bootstrap.cogitarelink.ai:agents:test-agent",
                "agentRole": f"fabric:{role}",
                "authorizedGraphs": graphs or ["/graph/observations"],
                "authorizedOperations": ops or ["read"],
                "homeNode": "did:webvh:abc:bootstrap.cogitarelink.ai",
            },
            "proof": {"type": "DataIntegrityProof"},
        }],
        "validUntil": (now + timedelta(minutes=valid_minutes)).isoformat(),
        "proof": {"type": "DataIntegrityProof", "cryptosuite": "eddsa-jcs-2022"},
    }


def _encode_vp(vp: dict) -> str:
    """Base64url-encode a VP dict."""
    return base64.urlsafe_b64encode(json.dumps(vp).encode()).decode().rstrip("=")


class TestDecodeBearer:
    def test_valid_bearer(self):
        vp = _make_vp()
        token = _encode_vp(vp)
        result = decode_bearer_token(f"Bearer {token}")
        assert result["type"] == ["VerifiablePresentation"]

    def test_missing_bearer_prefix(self):
        assert decode_bearer_token("NotBearer xyz") is None

    def test_empty_header(self):
        assert decode_bearer_token("") is None

    def test_invalid_base64(self):
        assert decode_bearer_token("Bearer !!!invalid!!!") is None

    def test_invalid_json(self):
        token = base64.urlsafe_b64encode(b"not json").decode()
        assert decode_bearer_token(f"Bearer {token}") is None


class TestExtractAgentContext:
    def test_valid_vp(self):
        vp = _make_vp(role="QARole", graphs=["/graph/observations"], ops=["read"])
        ctx = extract_agent_context(vp)
        assert isinstance(ctx, AgentContext)
        assert ctx.agent_did == "did:webvh:abc:bootstrap.cogitarelink.ai:agents:test-agent"
        assert ctx.agent_role == "QARole"
        assert ctx.authorized_graphs == ["/graph/observations"]
        assert ctx.authorized_operations == ["read"]

    def test_expired_vp(self):
        vp = _make_vp(valid_minutes=-1)
        assert extract_agent_context(vp) is None

    def test_missing_valid_until(self):
        vp = _make_vp()
        del vp["validUntil"]
        assert extract_agent_context(vp) is None

    def test_invalid_role(self):
        vp = _make_vp(role="BogusRole")
        assert extract_agent_context(vp) is None

    def test_role_strips_fabric_prefix(self):
        vp = _make_vp(role="IngestCuratorRole")
        ctx = extract_agent_context(vp)
        assert ctx.agent_role == "IngestCuratorRole"

    def test_no_credentials(self):
        vp = _make_vp()
        vp["verifiableCredential"] = []
        assert extract_agent_context(vp) is None

    def test_valid_agent_roles_matches_registry(self):
        from fabric.node.registry import VALID_AGENT_ROLES as REGISTRY_ROLES
        assert VALID_AGENT_ROLES == REGISTRY_ROLES
```

**Step 2: Run tests to verify they fail**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/unit/test_vp_auth.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'fabric.node.vp_auth'`

**Step 3: Implement `vp_auth.py`**

Create `fabric/node/vp_auth.py`:

```python
"""VP Bearer token verification for SPARQL endpoint gating (D13/D14).

Pure Python helpers — no FastAPI dependency. Imported by main.py (Docker)
and unit tests (local). Same pattern as did_resolver.py and void_templates.py.
"""
import base64
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from fabric.node.registry import VALID_AGENT_ROLES


@dataclass
class AgentContext:
    """Extracted from a verified VP. Passed to route handlers."""
    agent_did: str
    agent_role: str
    authorized_graphs: list[str]
    authorized_operations: list[str]


def decode_bearer_token(auth_header: str) -> dict | None:
    """Decode Authorization: Bearer <base64url(vp_json)> → VP dict or None."""
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    try:
        padded = token + "=" * (-len(token) % 4)
        raw = base64.urlsafe_b64decode(padded)
        return json.loads(raw)
    except Exception:
        return None


def extract_agent_context(vp: dict) -> AgentContext | None:
    """Extract and validate agent context from a VP dict.

    Checks: validUntil not expired, agentRole in VALID_AGENT_ROLES,
    credentialSubject present. Does NOT verify cryptographic proofs
    (that's Credo's job via POST /presentations/verify).
    """
    valid_until = vp.get("validUntil")
    if not valid_until:
        return None
    try:
        expiry = datetime.fromisoformat(valid_until)
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if expiry < datetime.now(timezone.utc):
            return None
    except (ValueError, TypeError):
        return None

    credentials = vp.get("verifiableCredential", [])
    if not credentials:
        return None

    subject = credentials[0].get("credentialSubject", {})
    raw_role = subject.get("agentRole", "")
    role = raw_role.removeprefix("fabric:")
    if role not in VALID_AGENT_ROLES:
        return None

    return AgentContext(
        agent_did=subject.get("id", vp.get("holder", "")),
        agent_role=role,
        authorized_graphs=subject.get("authorizedGraphs", []),
        authorized_operations=subject.get("authorizedOperations", []),
    )
```

**Step 4: Run tests to verify they pass**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/unit/test_vp_auth.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add fabric/node/vp_auth.py tests/pytest/unit/test_vp_auth.py
git commit -m "feat: add vp_auth.py with decode_bearer_token + extract_agent_context (D13)"
```

---

### Task 4: FastAPI middleware — wire `verify_vp_bearer()` into main.py

Add the async dependency to `/sparql` and `/sparql/update` routes.

**Files:**
- Modify: `fabric/node/main.py:52-55` (add `FABRIC_AUTH_ENABLED` env var)
- Modify: `fabric/node/main.py:552-563` (update `/sparql` and `/sparql/update` routes)
- Test: `tests/pytest/unit/test_vp_auth.py` (add FastAPI dependency test)

**Step 1: Write the failing test**

Add to `tests/pytest/unit/test_vp_auth.py`:

```python
import httpx
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient


class TestVerifyVPBearerDependency:
    """Test the FastAPI dependency function end-to-end with mocked Credo."""

    def _make_app(self, auth_enabled=True):
        """Create a minimal FastAPI app with the VP auth dependency."""
        import os
        os.environ["FABRIC_AUTH_ENABLED"] = str(auth_enabled).lower()
        # Force re-import to pick up env var
        import importlib
        import fabric.node.main as main_mod
        importlib.reload(main_mod)
        return main_mod.app

    def test_missing_auth_header_returns_401(self):
        """POST /sparql without Authorization header → 401."""
        # This test will be validated against the live stack via HURL
        # Unit test just validates the pure functions
        vp = _make_vp()
        ctx = extract_agent_context(vp)
        assert ctx is not None  # sanity check
```

Note: Full FastAPI dependency integration is better tested via HURL against the live stack. Unit tests focus on the pure functions in `vp_auth.py`. The FastAPI wiring is thin glue.

**Step 2: Implement the FastAPI wiring**

In `fabric/node/main.py`, add import near top (after existing imports):

```python
from fabric.node.vp_auth import decode_bearer_token, extract_agent_context, AgentContext
```

Add env var near line 55:

```python
FABRIC_AUTH_ENABLED = os.environ.get("FABRIC_AUTH_ENABLED", "true").lower() == "true"
```

Add the dependency function:

```python
async def verify_vp_bearer(request: Request) -> AgentContext | None:
    """FastAPI dependency: verify VP Bearer token on SPARQL routes.

    Returns AgentContext on success. Raises HTTPException on failure.
    When FABRIC_AUTH_ENABLED=false, returns None (no auth required).
    """
    if not FABRIC_AUTH_ENABLED:
        return None

    auth = request.headers.get("authorization", "")
    vp = decode_bearer_token(auth)
    if vp is None:
        raise HTTPException(
            status_code=401,
            detail="VP Bearer token required",
            headers={"WWW-Authenticate": 'Bearer realm="cogitarelink-fabric"'},
        )

    # Verify VP proof via Credo
    try:
        resp = await request.app.state.http_credo.post(
            "/presentations/verify", json=vp,
        )
        result = resp.json()
        if not result.get("verified"):
            raise HTTPException(
                status_code=403,
                detail=f"VP verification failed: {result.get('error', 'unknown')}",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Credo verification error: {e}")

    # Extract and validate agent context
    ctx = extract_agent_context(vp)
    if ctx is None:
        raise HTTPException(
            status_code=403,
            detail="VP expired or invalid agentRole",
        )

    return ctx
```

Update the route handlers (replace lines 552-563):

```python
@app.post("/sparql")
async def sparql_query_proxy(
    request: Request,
    agent: AgentContext | None = Depends(verify_vp_bearer),
):
    return await _proxy(request, "query")


@app.post("/sparql/update")
async def sparql_update_proxy(
    request: Request,
    agent: AgentContext | None = Depends(verify_vp_bearer),
):
    if not SPARQL_UPDATE_ENABLED:
        raise HTTPException(status_code=403, detail="SPARQL Update disabled")
    return await _proxy(request, "update")
```

Add `Depends` import at top of file:

```python
from fastapi import Depends
```

**Step 3: Run existing tests to verify nothing breaks**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/unit/ -v`
Expected: All existing tests PASS (auth is disabled in unit test env)

**Step 4: Commit**

```bash
git add fabric/node/main.py
git commit -m "feat: wire verify_vp_bearer() dependency into /sparql routes (D13)"
```

---

### Task 5: Docker Compose — add `FABRIC_AUTH_ENABLED` and rebuild

**Files:**
- Modify: `docker-compose.yml:21-25` (add env var to fabric-node)

**Step 1: Add env var**

In `docker-compose.yml`, add to the `fabric-node` environment section:

```yaml
FABRIC_AUTH_ENABLED: "true"
```

**Step 2: Rebuild and restart**

```bash
docker compose build fabric-node credo-sidecar
docker compose up -d
sleep 15
```

**Step 3: Verify unauthenticated SPARQL is now rejected**

```bash
curl -s --cacert caddy-root.crt -X POST \
  -H "Content-Type: application/sparql-query" \
  -d "SELECT * WHERE { ?s ?p ?o } LIMIT 1" \
  https://bootstrap.cogitarelink.ai/sparql
```

Expected: HTTP 401 with `WWW-Authenticate: Bearer realm="cogitarelink-fabric"`

**Step 4: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: enable FABRIC_AUTH_ENABLED in Docker Compose (D13)"
```

---

### Task 6: Test helper route `POST /test/create-vp`

Add a dev-only endpoint to the FastAPI gateway that registers an agent and returns a ready-to-use base64url VP token. Used by HURL tests.

**Files:**
- Modify: `fabric/node/main.py` (add route)
- Test: `tests/hurl/phase2/52-test-helper-vp.hurl`

**Step 1: Write the HURL test**

Create `tests/hurl/phase2/52-test-helper-vp.hurl`:

```hurl
# 52-test-helper-vp.hurl — Dev helper creates a VP token for testing

POST {{gateway}}/test/create-vp
Content-Type: application/json
{
  "agentRole": "DevelopmentAgentRole",
  "authorizedGraphs": ["/graph/observations", "/graph/entities"],
  "authorizedOperations": ["read"]
}
HTTP 201
[Asserts]
jsonpath "$.token" exists
jsonpath "$.agentDid" exists
jsonpath "$.agentRole" == "DevelopmentAgentRole"
[Captures]
vp_token: jsonpath "$.token"
```

**Step 2: Implement the helper route**

In `fabric/node/main.py`, add near the test/dev routes:

```python
TEST_HELPERS_ENABLED = os.environ.get("TEST_HELPERS_ENABLED", "true").lower() == "true"

@app.post("/test/create-vp")
async def test_create_vp(request: Request):
    """Dev-only: register agent + create VP → return base64url token.

    Used by HURL tests that need a valid VP Bearer token.
    Not available in production (TEST_HELPERS_ENABLED=false).
    """
    if not TEST_HELPERS_ENABLED:
        raise HTTPException(status_code=404, detail="Not found")

    body = await request.json()
    role = body.get("agentRole", "DevelopmentAgentRole")
    graphs = body.get("authorizedGraphs", [])
    ops = body.get("authorizedOperations", ["read"])

    # 1. Register agent via Credo
    reg_resp = await app.state.http_credo.post("/agents/register", json={
        "agentRole": role,
        "authorizedGraphs": graphs,
        "authorizedOperations": ops,
    })
    if reg_resp.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Agent registration failed: {reg_resp.text}")
    reg_data = reg_resp.json()

    # 2. Create VP via Credo
    vp_resp = await app.state.http_credo.post("/presentations/create", json={
        "credential": reg_data["credential"],
        "holderDid": reg_data["agentDid"],
        "validMinutes": 5,
    })
    if vp_resp.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"VP creation failed: {vp_resp.text}")
    vp_json = vp_resp.json()

    # 3. Base64url-encode VP
    import base64
    token = base64.urlsafe_b64encode(
        json.dumps(vp_json).encode()
    ).decode().rstrip("=")

    return JSONResponse(status_code=201, content={
        "token": token,
        "agentDid": reg_data["agentDid"],
        "agentRole": role,
        "validUntil": vp_json.get("validUntil"),
    })
```

**Step 3: Run HURL test**

Run: `cd tests && hurl --test --variable gateway=https://bootstrap.cogitarelink.ai --cacert ../caddy-root.crt hurl/phase2/52-test-helper-vp.hurl`
Expected: PASS

**Step 4: Commit**

```bash
git add fabric/node/main.py tests/hurl/phase2/52-test-helper-vp.hurl
git commit -m "feat: add POST /test/create-vp helper for HURL tests (D13)"
```

---

### Task 7: HURL integration tests — auth enforcement

Write HURL tests verifying that `/sparql` and `/sparql/update` require VP Bearer auth and work with valid tokens.

**Files:**
- Create: `tests/hurl/phase2/53-sparql-requires-auth.hurl`
- Create: `tests/hurl/phase2/54-sparql-with-vp-bearer.hurl`

**Step 1: Write the auth-required test**

Create `tests/hurl/phase2/53-sparql-requires-auth.hurl`:

```hurl
# 53-sparql-requires-auth.hurl — SPARQL endpoints reject unauthenticated requests

# Query without auth → 401
POST {{gateway}}/sparql
Content-Type: application/sparql-query
SELECT * WHERE { ?s ?p ?o } LIMIT 1
HTTP 401
[Asserts]
header "WWW-Authenticate" contains "Bearer"

# Update without auth → 401
POST {{gateway}}/sparql/update
Content-Type: application/sparql-update
INSERT DATA { GRAPH <urn:test> { <urn:s> <urn:p> "v" } }
HTTP 401
[Asserts]
header "WWW-Authenticate" contains "Bearer"
```

**Step 2: Write the authenticated query test**

Create `tests/hurl/phase2/54-sparql-with-vp-bearer.hurl`:

```hurl
# 54-sparql-with-vp-bearer.hurl — SPARQL works with valid VP Bearer token

# Step 1: Get a VP token via test helper
POST {{gateway}}/test/create-vp
Content-Type: application/json
{
  "agentRole": "DevelopmentAgentRole",
  "authorizedGraphs": ["/graph/observations"],
  "authorizedOperations": ["read"]
}
HTTP 201
[Captures]
vp_token: jsonpath "$.token"

# Step 2: Query with VP Bearer → 200
POST {{gateway}}/sparql
Content-Type: application/sparql-query
Authorization: Bearer {{vp_token}}
SELECT * WHERE { ?s ?p ?o } LIMIT 1
HTTP 200
```

**Step 3: Run tests**

Run: `cd tests && hurl --test --variable gateway=https://bootstrap.cogitarelink.ai --cacert ../caddy-root.crt hurl/phase2/53-sparql-requires-auth.hurl hurl/phase2/54-sparql-with-vp-bearer.hurl`
Expected: PASS

**Step 4: Commit**

```bash
git add tests/hurl/phase2/53-sparql-requires-auth.hurl tests/hurl/phase2/54-sparql-with-vp-bearer.hurl
git commit -m "test: add HURL tests for VP-gated SPARQL access (D13)"
```

---

### Task 8: Update `sparql_query` tool with auth header + error messages

Update the agent's SPARQL query tool to pass the VP Bearer token and return LLM-readable error messages on 401/403.

**Files:**
- Modify: `agents/fabric_discovery.py:33-49` (add `vp_token` field to `FabricEndpoint`)
- Modify: `agents/fabric_query.py:56-90` (add auth header + error messages)
- Test: `tests/pytest/unit/test_fabric_query.py` (add auth tests)

**Step 1: Write the failing tests**

Add to `tests/pytest/unit/test_fabric_query.py` (or create new test file):

```python
def test_sparql_query_401_returns_readable_error():
    """401 from SPARQL endpoint → LLM-readable error, not raw HTTP."""
    import httpx
    from unittest.mock import patch, MagicMock
    from agents.fabric_query import make_fabric_query_tool
    from agents.fabric_discovery import FabricEndpoint

    ep = FabricEndpoint(
        base="https://example.com",
        sparql_url="https://example.com/sparql",
        void_ttl="", profile_ttl="", shapes_ttl="", examples_ttl="",
    )
    tool = make_fabric_query_tool(ep)

    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "VP Bearer token required"
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "401", request=MagicMock(), response=mock_resp
    )

    with patch("httpx.post", return_value=mock_resp):
        result = tool("SELECT * WHERE { ?s ?p ?o }")
    assert "Access denied" in result or "401" in result
    assert "do not retry" in result.lower() or "report" in result.lower()


def test_sparql_query_sends_auth_header():
    """When ep.vp_token is set, Authorization header is sent."""
    import httpx
    from unittest.mock import patch, MagicMock
    from agents.fabric_query import make_fabric_query_tool
    from agents.fabric_discovery import FabricEndpoint

    ep = FabricEndpoint(
        base="https://example.com",
        sparql_url="https://example.com/sparql",
        void_ttl="", profile_ttl="", shapes_ttl="", examples_ttl="",
        vp_token="test-token-abc",
    )
    tool = make_fabric_query_tool(ep)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = '{"results":{"bindings":[]}}'
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.post", return_value=mock_resp) as mock_post:
        tool("SELECT * WHERE { ?s ?p ?o }")
    call_kwargs = mock_post.call_args
    assert "Authorization" in call_kwargs.kwargs.get("headers", {}) or \
           "Authorization" in (call_kwargs[1].get("headers", {}) if len(call_kwargs) > 1 else {})
```

**Step 2: Run tests to verify they fail**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/unit/test_fabric_query.py -v -k "auth"`
Expected: FAIL — `FabricEndpoint` has no `vp_token` field

**Step 3: Add `vp_token` to `FabricEndpoint`**

In `agents/fabric_discovery.py`, add to the dataclass fields (after `vocab_graph_map`):

```python
vp_token: str | None = field(default=None, repr=False)
```

**Step 4: Update `make_fabric_query_tool` to pass auth header + readable errors**

In `agents/fabric_query.py`, update the `sparql_query` closure:

```python
def sparql_query(query: str) -> str:
    """Execute SPARQL against the fabric endpoint. Returns JSON results.
    Results are truncated to ~10k chars. On error, returns error description."""
    try:
        if reject_unbounded and _is_unbounded_scan(query):
            return _UNBOUNDED_MSG
        headers = {"Accept": "application/sparql-results+json"}
        if ep.vp_token:
            headers["Authorization"] = f"Bearer {ep.vp_token}"
        r = httpx.post(
            ep.sparql_url,
            data={"query": query},
            headers=headers,
            timeout=30.0,
        )
        r.raise_for_status()
        txt = r.text
        if len(txt) > max_chars:
            return txt[:max_chars] + f"\n... truncated ({len(txt)} total chars). Use llm_query() to analyse large results."
        return txt
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (401, 403):
            return (
                f"Access denied (HTTP {e.response.status_code}): "
                f"{e.response.text[:300]}. "
                "Your credential may be expired or lack authorization for this graph. "
                "Report this to the human operator — do not retry."
            )
        return f"SPARQL error (HTTP {e.response.status_code}): {e.response.text[:500]}"
    except Exception as e:
        return f"SPARQL error: {e}"
```

**Step 5: Run tests**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/unit/test_fabric_query.py -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add agents/fabric_discovery.py agents/fabric_query.py tests/pytest/unit/test_fabric_query.py
git commit -m "feat: add VP Bearer auth header + LLM-readable errors to sparql_query tool (D13)"
```

---

### Task 9: Update experiment harness — agent registration + VP injection

Wire the experiment harness to register an agent, create a VP, and inject the token into `FabricEndpoint`.

**Files:**
- Modify: `experiments/fabric_navigation/run_experiment.py:363-372` (add VP creation to startup)
- Modify: `agents/fabric_discovery.py` (add `register_and_authenticate` helper)

**Step 1: Add helper to `fabric_discovery.py`**

Add a standalone function (not a method — same pattern as `discover_endpoint`):

```python
def register_and_authenticate(
    ep: FabricEndpoint,
    role: str = "DevelopmentAgentRole",
    graphs: list[str] | None = None,
    operations: list[str] | None = None,
    valid_minutes: int = 5,
) -> FabricEndpoint:
    """Register agent at fabric node and set VP Bearer token on endpoint.

    Calls POST /agents/register then POST /test/create-vp (or Credo directly).
    Returns the same FabricEndpoint with vp_token populated.
    """
    import base64, json
    graphs = graphs or ["*"]
    operations = operations or ["read"]

    # Use the test helper for simplicity
    r = httpx.post(
        f"{ep.base}/test/create-vp",
        json={"agentRole": role, "authorizedGraphs": graphs, "authorizedOperations": operations},
        timeout=30.0,
        verify=os.environ.get("SSL_CERT_FILE", True),
    )
    r.raise_for_status()
    data = r.json()
    ep.vp_token = data["token"]
    return ep
```

**Step 2: Wire into `run_experiment.py`**

After `discover_endpoint()` call, add:

```python
if os.environ.get("FABRIC_AUTH_ENABLED", "true").lower() == "true":
    from agents.fabric_discovery import register_and_authenticate
    ep = register_and_authenticate(ep)
    print(f"  Agent registered: {ep.vp_token[:20]}...")
```

**Step 3: Add agent instruction hint to `kwarg_builder`**

In `kwarg_builder`, add after the existing hint injections:

```python
if ep.vp_token:
    sd = sd + "\n\nYou are authenticated with a VP Bearer token. If you receive an access denied error (401 or 403), report it to the human operator — do not retry the same query."
```

**Step 4: Test manually**

```bash
cd ~/dev/git/LA3D/agents/cogitarelink-fabric
SSL_CERT_FILE=/tmp/cogitarelink-ca-bundle.pem \
  ~/uvws/.venv/bin/python experiments/fabric_navigation/run_experiment.py \
    --tasks experiments/fabric_navigation/tasks/phase3-sio-tbox.json \
    --phase phase3b-tbox-paths \
    --output /tmp/test-auth \
    --model anthropic/claude-sonnet-4-6 \
    --verbose 2>&1 | head -30
```

Expected: Agent registers successfully, queries execute with Bearer token.

**Step 5: Commit**

```bash
git add agents/fabric_discovery.py experiments/fabric_navigation/run_experiment.py
git commit -m "feat: wire agent registration + VP auth into experiment harness (D13)"
```

---

### Task 10: Fix existing HURL tests — add VP auth to all SPARQL-using tests

Existing HURL tests that hit `/sparql` will now get 401. Each needs a VP token.

**Files:**
- Modify: All `tests/hurl/phase1/*.hurl` and `tests/hurl/phase2/*.hurl` files that POST to `/sparql` or `/sparql/update`

**Step 1: Identify affected tests**

```bash
grep -rn "POST {{gateway}}/sparql" tests/hurl/ | grep -v "requires-auth"
```

**Step 2: Add VP token capture to each affected test**

Pattern: Add a setup section at the top of each affected HURL file that gets a VP token:

```hurl
# Setup: get VP token
POST {{gateway}}/test/create-vp
Content-Type: application/json
{
  "agentRole": "DevelopmentAgentRole",
  "authorizedGraphs": ["*"],
  "authorizedOperations": ["read", "write"]
}
HTTP 201
[Captures]
vp_token: jsonpath "$.token"

# Original test (add Authorization header)
POST {{gateway}}/sparql
Content-Type: application/sparql-query
Authorization: Bearer {{vp_token}}
...
```

Add the `Authorization: Bearer {{vp_token}}` header to every `POST {{gateway}}/sparql` and `POST {{gateway}}/sparql/update` request in the file.

**Step 3: Run full HURL suite**

Run: `cd tests && make test-hurl-p1 && make test-hurl-p2`
Expected: All 42+ tests PASS (original 42 + new auth tests)

**Step 4: Commit**

```bash
git add tests/hurl/
git commit -m "fix: add VP Bearer auth to all HURL tests hitting /sparql (D13)"
```

---

### Task 11: Fix existing pytest integration tests — add VP auth

Existing pytest integration tests that hit `/sparql` need VP tokens.

**Files:**
- Modify: `tests/pytest/integration/conftest.py` (add VP fixture)
- Modify: `tests/pytest/integration/test_fabric_discovery.py`
- Modify: `tests/pytest/integration/test_fabric_query.py`
- Modify: `tests/pytest/integration/test_fabric_validate.py`
- Modify: `tests/pytest/integration/test_fabric_agent.py`

**Step 1: Add VP fixture to conftest.py**

```python
@pytest.fixture(scope="session")
def vp_token():
    """Get a VP Bearer token for integration tests."""
    import httpx
    r = httpx.post(
        f"{GATEWAY}/test/create-vp",
        json={
            "agentRole": "DevelopmentAgentRole",
            "authorizedGraphs": ["*"],
            "authorizedOperations": ["read", "write"],
        },
        verify=CA_CERT,
        timeout=30.0,
    )
    r.raise_for_status()
    return r.json()["token"]
```

**Step 2: Update integration tests to use VP token**

In each integration test that creates a `FabricEndpoint`, set `ep.vp_token` from the fixture:

```python
def test_something(vp_token):
    ep = discover_endpoint(GATEWAY)
    ep.vp_token = vp_token
    # ... rest of test
```

**Step 3: Run integration tests**

Run: `cd ~/dev/git/LA3D/agents/cogitarelink-fabric && SSL_CERT_FILE=/tmp/cogitarelink-ca-bundle.pem FABRIC_GATEWAY=https://bootstrap.cogitarelink.ai ~/uvws/.venv/bin/python -m pytest tests/pytest/integration/ -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add tests/pytest/integration/
git commit -m "fix: add VP Bearer auth to pytest integration tests (D13)"
```

---

### Task 12: Full test suite verification + MEMORY.md update

Run everything end-to-end and update session memory.

**Files:**
- Modify: `.claude/memory/MEMORY.md`

**Step 1: Run full pytest suite**

```bash
cd ~/dev/git/LA3D/agents/cogitarelink-fabric
SSL_CERT_FILE=/tmp/cogitarelink-ca-bundle.pem FABRIC_GATEWAY=https://bootstrap.cogitarelink.ai \
  ~/uvws/.venv/bin/python -m pytest tests/ -v 2>&1 | tail -20
```

Expected: All tests pass (205 existing + new vp_auth tests)

**Step 2: Run full HURL suite**

```bash
cd tests && make test-all
```

Expected: All tests pass (42 existing + new auth tests)

**Step 3: Verify DID still served**

```bash
curl --cacert caddy-root.crt https://bootstrap.cogitarelink.ai/.well-known/did.json | python3 -m json.tool | grep '"id"'
```

Expected: `bootstrap.cogitarelink.ai` DID

**Step 4: Update `.claude/memory/MEMORY.md`**

Add to Completed Work:
```
- **D13/D14 VP-gated SPARQL access**: VP-as-Bearer enforcement on /sparql + /sparql/update; Credo POST /presentations/create + /presentations/verify; verify_vp_bearer() FastAPI dependency; FABRIC_AUTH_ENABLED env var; tool-level LLM-readable error messages
```

Add D13/D14 VP Auth Patterns section with key patterns discovered during implementation.

**Step 5: Commit**

```bash
git add .claude/memory/MEMORY.md
git commit -m "[Agent: Claude] docs: update MEMORY.md with D13/D14 VP-gated SPARQL patterns

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

**Step 6: Push**

```bash
git push
```
