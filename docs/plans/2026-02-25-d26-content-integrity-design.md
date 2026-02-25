# D26 Content Integrity — Tier 2 (Self-Attested) Design

> **For Claude:** Use EnterPlanMode to create the implementation plan from this design.

**Goal**: Add `relatedResource` + `digestMultibase` content hashes to the FabricConformanceCredential so agents can verify that self-description artifacts (VoID, SHACL, SPARQL examples) haven't changed since the VC was issued.

**Scope**: Tier 2 only (self-attested — node hashes its own artifacts). Tier 1 (bootstrap-attested) deferred to Week 5-6 admission flow.

**Decision**: D26 in KF-Prototype-Decisions.md

---

## Architecture

### Current Flow

```
Credo bootstrap()
  → create did:webvh
  → writeDIDLog() → /shared/did.jsonl
  → issueVC(credentialSubject) → sign with eddsa-jcs-2022
  → write /shared/conformance-vc.json
  → done
```

FastAPI serves artifacts independently — no binding between VC and artifact content.

### New Flow

```
Credo bootstrap()
  → create did:webvh
  → writeDIDLog() → /shared/did.jsonl
  → waitForGateway()                          ← NEW: wait for FastAPI to be ready
  → fetchAndHashArtifacts()                   ← NEW: fetch VoID/SHACL/examples, SHA-256
  → issueVC(credentialSubject + relatedResource) → sign with eddsa-jcs-2022
  → write /shared/conformance-vc.json
  → done
```

### Sequencing Constraint

The Credo sidecar must fetch artifacts from the FastAPI gateway to hash them. This means FastAPI must be up and serving content before the VC is issued. Docker Compose starts both containers simultaneously, so Credo needs a wait-for-gateway loop.

**Wait strategy**: Poll `GET {NODE_BASE}/.well-known/void` with exponential backoff (500ms, 1s, 2s, 4s). Timeout after 30s. FastAPI startup is fast (< 2s typically), so this shouldn't delay bootstrap noticeably.

---

## Credo Sidecar Changes (`fabric/credo/src/index.ts`)

### New Helper: `waitForGateway()`

```typescript
async function waitForGateway(maxWaitMs = 30000): Promise<void> {
  const start = Date.now()
  let delay = 500
  while (Date.now() - start < maxWaitMs) {
    try {
      const resp = await fetch(`${NODE_BASE}/.well-known/void`)
      if (resp.ok) return
    } catch { /* gateway not up yet */ }
    await new Promise(r => setTimeout(r, delay))
    delay = Math.min(delay * 2, 4000)
  }
  throw new Error(`Gateway not ready after ${maxWaitMs}ms`)
}
```

### New Helper: `computeDigestMultibase(url)`

```typescript
async function computeDigestMultibase(url: string): Promise<{
  digestMultibase: string
  digestSRI: string
  mediaType: string
}> {
  const resp = await fetch(url)
  if (!resp.ok) throw new Error(`Failed to fetch ${url}: ${resp.status}`)
  const body = new Uint8Array(await resp.arrayBuffer())
  const mediaType = resp.headers.get('content-type')?.split(';')[0]?.trim() ?? 'application/octet-stream'

  // SHA-256 hash
  const hash = await Hasher.hash(body, 'sha-256')  // @credo-ts/core Hasher

  // Multibase base58btc encoding (reuse existing base58btcEncode)
  const digestMultibase = base58btcEncode(hash)

  // SRI format: sha256-{base64}
  const digestSRI = 'sha256-' + Buffer.from(hash).toString('base64')

  return { digestMultibase, digestSRI, mediaType }
}
```

**Note**: `Hasher` from `@credo-ts/core` is already available (used in `jcsHash`). `base58btcEncode` is already implemented in `index.ts`.

### Modified `bootstrap()` Function

After `writeDIDLog()`, before `issueVC()`:

```typescript
// Wait for gateway to be ready
await waitForGateway()

// Fetch and hash self-description artifacts
const artifacts = [
  `${NODE_BASE}/.well-known/void`,
  `${NODE_BASE}/.well-known/shacl`,
  `${NODE_BASE}/.well-known/sparql-examples`,
]
const relatedResource = await Promise.all(
  artifacts.map(async (url) => {
    const { digestMultibase, digestSRI, mediaType } = await computeDigestMultibase(url)
    return { id: url, digestMultibase, digestSRI, mediaType }
  })
)
```

Then pass `relatedResource` into the VC:

```typescript
const vc = await issueVC(
  ['FabricConformanceCredential'],
  {
    id: nodeDid,
    conformsTo: 'https://w3id.org/cogitarelink/fabric#CoreProfile',
    // ... existing service directory fields ...
    attestedAt: new Date().toISOString(),
  },
  relatedResource,  // NEW parameter
)
```

### Modified `issueVC()` Signature

Add optional `relatedResource` parameter:

```typescript
async function issueVC(
  type: string[],
  subject: Record<string, unknown>,
  relatedResource?: Array<{ id: string; digestMultibase: string; digestSRI: string; mediaType: string }>,
): Promise<Record<string, unknown>> {
  // ... existing code ...
  const credential: Record<string, unknown> = {
    '@context': ['https://www.w3.org/ns/credentials/v2'],
    type: ['VerifiableCredential', ...type],
    issuer: nodeDid,
    validFrom: new Date().toISOString(),
    credentialSubject: { ...subject },
  }
  if (relatedResource?.length) {
    credential.relatedResource = relatedResource
  }
  // ... sign and return ...
}
```

---

## Python Verification Utility (`fabric/node/`)

### New Module: `integrity.py`

Pure Python (no FastAPI dependency — same pattern as `did_resolver.py` and `void_templates.py`).

```python
import hashlib, json
from typing import Any

# Multibase base58btc alphabet (same as Bitcoin)
_B58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

def b58_encode(data: bytes) -> str:
    """Base58btc encode (Bitcoin alphabet)."""
    n = int.from_bytes(data, 'big')
    result = []
    while n > 0:
        n, r = divmod(n, 58)
        result.append(_B58_ALPHABET[r])
    # Preserve leading zero bytes
    for b in data:
        if b == 0:
            result.append(_B58_ALPHABET[0])
        else:
            break
    return ''.join(reversed(result))

def b58_decode(s: str) -> bytes:
    """Base58btc decode."""
    n = 0
    for c in s:
        n = n * 58 + _B58_ALPHABET.index(c)
    # Count leading '1's (zero bytes)
    pad = 0
    for c in s:
        if c == _B58_ALPHABET[0]:
            pad += 1
        else:
            break
    result = n.to_bytes((n.bit_length() + 7) // 8, 'big') if n else b''
    return b'\x00' * pad + result

def compute_digest_multibase(content: bytes) -> str:
    """SHA-256 hash, return as multibase base58btc ('z' prefix)."""
    h = hashlib.sha256(content).digest()
    return 'z' + b58_encode(h)

def compute_digest_sri(content: bytes) -> str:
    """SHA-256 hash, return as SRI format (sha256-{base64})."""
    import base64
    h = hashlib.sha256(content).digest()
    return 'sha256-' + base64.b64encode(h).decode('ascii')

def verify_digest_multibase(content: bytes, expected: str) -> bool:
    """Verify content matches expected digestMultibase."""
    return compute_digest_multibase(content) == expected

def verify_related_resources(vc: dict, fetcher=None) -> list[dict]:
    """Verify all relatedResource entries in a VC.

    Args:
        vc: Parsed VC JSON (must have 'relatedResource' array)
        fetcher: callable(url) -> bytes; if None, uses httpx synchronous GET

    Returns:
        List of {url, expected, actual, match, mediaType} dicts
    """
    resources = vc.get('relatedResource', [])
    if not resources:
        return []

    if fetcher is None:
        import httpx
        def fetcher(url):
            r = httpx.get(url)
            r.raise_for_status()
            return r.content

    results = []
    for res in resources:
        url = res.get('id', '')
        expected = res.get('digestMultibase', '')
        try:
            content = fetcher(url)
            actual = compute_digest_multibase(content)
            results.append({
                'url': url,
                'expected': expected,
                'actual': actual,
                'match': actual == expected,
                'mediaType': res.get('mediaType', ''),
            })
        except Exception as e:
            results.append({
                'url': url,
                'expected': expected,
                'actual': None,
                'match': False,
                'error': str(e),
            })
    return results
```

### Dockerfile Update

```dockerfile
COPY main.py bootstrap.py start.sh void_templates.py did_resolver.py integrity.py ./
```

---

## HURL Integration Tests

### `tests/hurl/phase2/38-conformance-vc-related-resources.hurl`

```hurl
# Phase 2 — D26: relatedResource in conformance VC
# Verify VC contains relatedResource entries with digest hashes

GET {{gateway}}/.well-known/conformance-vc.json
HTTP 200
[Asserts]
jsonpath "$.relatedResource" count == 3
jsonpath "$.relatedResource[0].id" contains "/.well-known/void"
jsonpath "$.relatedResource[0].digestMultibase" startsWith "z"
jsonpath "$.relatedResource[0].mediaType" exists
jsonpath "$.relatedResource[1].id" contains "/.well-known/shacl"
jsonpath "$.relatedResource[1].digestMultibase" startsWith "z"
jsonpath "$.relatedResource[2].id" contains "/.well-known/sparql-examples"
jsonpath "$.relatedResource[2].digestMultibase" startsWith "z"
```

### `tests/hurl/phase2/39-content-integrity-verify.hurl`

This test verifies that the hash of a fetched artifact actually matches what's in the VC. HURL can't compute SHA-256 directly, so this test captures the `digestMultibase` from the VC and uses a Python verification endpoint (or we rely on the unit tests for hash verification and just check structural correctness in HURL).

**Decision**: HURL tests verify structure (relatedResource exists, has correct fields). Unit tests verify hash computation and matching. No need for a verification endpoint just for testing.

---

## Unit Tests (`tests/pytest/unit/test_integrity.py`)

```python
from fabric.node.integrity import (
    b58_encode, b58_decode,
    compute_digest_multibase, compute_digest_sri,
    verify_digest_multibase, verify_related_resources,
)

def test_b58_roundtrip():
    data = b'\x00\x01\x02\xff' * 8
    assert b58_decode(b58_encode(data)) == data

def test_compute_digest_multibase_known():
    # SHA-256 of empty string = e3b0c44298fc1c149...
    assert compute_digest_multibase(b'').startswith('z')
    assert len(compute_digest_multibase(b'')) > 10

def test_compute_digest_multibase_deterministic():
    content = b'hello world'
    assert compute_digest_multibase(content) == compute_digest_multibase(content)

def test_compute_digest_sri():
    sri = compute_digest_sri(b'hello world')
    assert sri.startswith('sha256-')

def test_verify_digest_multibase_match():
    content = b'test content'
    digest = compute_digest_multibase(content)
    assert verify_digest_multibase(content, digest)

def test_verify_digest_multibase_mismatch():
    assert not verify_digest_multibase(b'content A', compute_digest_multibase(b'content B'))

def test_verify_related_resources():
    content_a = b'void turtle content'
    content_b = b'shacl turtle content'
    vc = {
        'relatedResource': [
            {'id': 'http://example.org/void', 'digestMultibase': compute_digest_multibase(content_a), 'mediaType': 'text/turtle'},
            {'id': 'http://example.org/shacl', 'digestMultibase': compute_digest_multibase(content_b), 'mediaType': 'text/turtle'},
        ]
    }
    fetcher = lambda url: content_a if 'void' in url else content_b
    results = verify_related_resources(vc, fetcher=fetcher)
    assert len(results) == 2
    assert all(r['match'] for r in results)

def test_verify_related_resources_mismatch():
    vc = {
        'relatedResource': [
            {'id': 'http://example.org/void', 'digestMultibase': 'zBadHash', 'mediaType': 'text/turtle'},
        ]
    }
    results = verify_related_resources(vc, fetcher=lambda url: b'actual content')
    assert len(results) == 1
    assert not results[0]['match']

def test_verify_related_resources_empty():
    assert verify_related_resources({}) == []
    assert verify_related_resources({'relatedResource': []}) == []
```

---

## Risk Assessment

**Low risk**:
- SHA-256 + base58btc are well-understood algorithms
- `relatedResource` is a standard VC Data Model 2.0 field — no custom vocabulary
- The VC structure change is additive (existing fields unchanged)

**Medium risk**:
- **Gateway wait timing**: If FastAPI is slow to start, Credo bootstrap could timeout. Mitigated by 30s timeout + exponential backoff. Docker Compose `depends_on` already ensures Oxigraph is up before FastAPI starts.
- **Content determinism**: If VoID/SHACL content changes between Credo's hash and an agent's verification (e.g., timestamp in template), hashes won't match. Mitigated by: templates are static (only `{base}` substitution, no timestamps).

**Not a risk**:
- Breaking existing tests: `relatedResource` is additive to the VC JSON. Existing HURL test 37 checks `credentialSubject` fields, not top-level structure. The proof will be different (signs different content), but test 37 doesn't verify the proof.

---

## Files Changed

| File | Change |
|---|---|
| `fabric/credo/src/index.ts` | Add `waitForGateway()`, `computeDigestMultibase()`, modify `bootstrap()` and `issueVC()` |
| `fabric/node/integrity.py` | NEW — pure Python hash/multibase/verification utilities |
| `fabric/node/Dockerfile` | Add `integrity.py` to COPY |
| `tests/pytest/unit/test_integrity.py` | NEW — unit tests for integrity module |
| `tests/hurl/phase2/38-conformance-vc-related-resources.hurl` | NEW — verify relatedResource structure in VC |
