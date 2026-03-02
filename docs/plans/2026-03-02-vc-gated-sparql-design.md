# VC-Gated SPARQL Access — Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:writing-plans after this design is approved.

**Goal:** Gate `/sparql` and `/sparql/update` behind Verifiable Presentation Bearer tokens, enforcing agent identity (D13) and role membership (D14) at query time.

**Decisions:** D13 (agent identity), D14 (role taxonomy), D19 (HitL enforcement)

**Standards:** W3C VC Data Model 2.0, Verifiable Presentations, VCALM v0.9 (CG-Draft), RFC 6750 (Bearer Token Usage)

---

## Architecture

VP-as-Bearer flow with FastAPI dependency injection:

```
Agent                     Fabric Node (FastAPI)          Credo Sidecar
  |                              |                              |
  |-- POST /agents/register -->  |-- POST /agents/register --> |
  |<-- { agentDid, vc } ------  |<-- AgentAuthCredential ---- |
  |                              |                              |
  |-- POST /presentations/create (on Credo) ----------------> |
  |<-- { vp_json } ------------------------------------------ |
  |                              |                              |
  |-- POST /sparql              |                              |
  |   Authorization: Bearer     |                              |
  |   <b64url(vp_json)> ----->  |                              |
  |                              |-- POST /presentations/verify|
  |                              |   { vp_json } -----------> |
  |                              |<-- { verified: true } ----- |
  |                              |                              |
  |                              | check validUntil, agentRole  |
  |                              |                              |
  |<-- SPARQL results ---------- |                              |
```

Agent registers once, creates short-lived VPs (5-minute `validUntil`), presents as Bearer token. No server-side nonce state. Temporal window provides replay protection.

## Verifiable Presentation Format

```json
{
  "@context": ["https://www.w3.org/ns/credentials/v2"],
  "type": ["VerifiablePresentation"],
  "holder": "did:webvh:...:agents:{uuid}",
  "verifiableCredential": [{ ...AgentAuthorizationCredential... }],
  "validUntil": "2026-03-02T15:05:00Z",
  "proof": {
    "type": "DataIntegrityProof",
    "cryptosuite": "eddsa-jcs-2022",
    "verificationMethod": "did:webvh:...:agents:{uuid}#key-1",
    "proofPurpose": "authentication",
    "proofValue": "z..."
  }
}
```

Presented as `Authorization: Bearer <base64url(vp_json)>`.

## FastAPI Dependency: `verify_vp_bearer()`

Async dependency on both `/sparql` and `/sparql/update`:

1. Extract `Authorization: Bearer <token>` header
2. base64url-decode → parse JSON → validate VP structure
3. Check `validUntil` not expired
4. Call Credo `POST /presentations/verify` → `verified: true`
5. Extract `credentialSubject.agentRole` from embedded VC
6. Verify role in `VALID_AGENT_ROLES`
7. Return `AgentContext(agent_did, agent_role, authorized_graphs, authorized_operations)` to route handler

Controlled by `FABRIC_AUTH_ENABLED` env var (default `true` in Docker, `false` for bare unit tests).

### Error Responses (RFC 6750)

| Condition | Status | Response |
|-----------|--------|----------|
| Missing Authorization header | 401 | `WWW-Authenticate: Bearer realm="cogitarelink-fabric"` |
| Malformed token (bad base64, invalid JSON) | 401 | `error="invalid_token"` |
| Expired `validUntil` | 401 | `error="invalid_token", error_description="VP expired"` |
| VP proof verification failed | 403 | `error="insufficient_scope"` |
| Invalid agent role | 403 | `error="insufficient_scope", error_description="Unknown agentRole"` |

## Credo Sidecar Endpoints

Two new routes in `fabric/credo/src/index.ts`:

**`POST /presentations/create`** — Creates and signs a VP wrapping a VC.

Request:
```json
{
  "credential": { ...AgentAuthorizationCredential... },
  "holderDid": "did:webvh:...:agents:{uuid}",
  "validMinutes": 5
}
```

Response: Signed VP JSON.

**`POST /presentations/verify`** — Verifies a VP and its embedded credentials.

Request: VP JSON.
Response: `{ "verified": boolean, "error?": string }`.

Verifies: VP proof signature, each embedded VC proof signature, `validUntil` not expired.

## Tool-Level Error Handling

When `sparql_query` tool receives 401/403, it returns a structured message the LLM can reason about:

```
Access denied: Your AgentAuthorizationCredential (role: QARole) does not
authorize this operation. HTTP 403: insufficient_scope.
Report this to the human operator — do not retry.
```

Agent instruction hint injected into endpoint SD:
```
You are authenticated as {agentRole} with access to {authorizedGraphs}.
If you receive an access denied error, report it to the human — do not retry.
```

## Experiment Harness Updates

- `FabricEndpoint` gains `vp_token: str | None` and `refresh_vp()` method
- `run_experiment.py` registers a `DevelopmentAgentRole` agent at startup, creates VP, injects into endpoint
- `sparql_query` tool passes `Authorization: Bearer` header when `ep.vp_token` is set
- On 401 response: refresh VP once, retry; if still 401, return error to agent

## Testing

**Unit tests** (`test_verify_vp_bearer.py`):
- Valid VP passes → returns AgentContext
- Expired VP → 401
- Invalid proof → 403
- Missing header → 401
- Bad base64 → 401
- Invalid role → 403
- Mock Credo HTTP calls (no Docker needed)

**HURL integration tests**:
- `50-sparql-requires-auth.hurl` — POST /sparql without auth → 401
- `51-sparql-with-vp-bearer.hurl` — register agent, create VP, query with Bearer → 200
- `52-sparql-update-requires-auth.hurl` — POST /sparql/update without auth → 401

**Test helper route**: `POST /test/create-vp` (dev-only, controlled by env var) — registers an agent and returns a ready-to-use base64url VP token for HURL tests.

## Backward Compatibility

`FABRIC_AUTH_ENABLED=false` disables the middleware entirely. Unit tests that mock Oxigraph responses work without credentials. The env var defaults to `true` in `docker-compose.yml` and `false` elsewhere.

---

## Future Extensions (tracked, not implemented)

### Option C: Tiered Role/Graph Enforcement

Extend `verify_vp_bearer()` to inspect `authorizedGraphs` and `authorizedOperations` from the VP against the actual SPARQL query. Requires SPARQL parsing to extract target graph from `GRAPH <uri>` clauses or `FROM` / `FROM NAMED`. Natural follow-on once Option B (role-only checks) is validated.

### Credential-Scoped Service Descriptions

`discover_endpoint` filters graph inventory, SPARQL examples, and catalog entries based on `authorizedGraphs` from the agent's VP. Agent only sees resources it can access. Prevents the agent from constructing queries it can't execute. Complements Option C — enforcement tells the agent "no", filtered SD prevents it from asking.

### Server-Side Challenge/Nonce (VCALM)

Full VCALM `POST /challenges` exchange for cryptographic replay protection. Server issues challenge → agent creates VP signed over challenge → server verifies challenge binding. Replaces `validUntil` temporal window with cryptographic binding to a specific verification session. Reference: W3C CCG VCALM v0.9 (https://w3c-ccg.github.io/vcalm/).

### OAuth/Okta Integration

Notre Dame uses Okta for institutional SSO. For human-in-the-loop flows (D19), agent VPs could be bridged to OAuth tokens via an authorization server that accepts VP presentation and issues scoped OAuth access tokens. This connects VC-based agent identity with organizational identity management. Relevant when fabric nodes are deployed at institutional endpoints (e.g., `crc.nd.cogitarelink.ai`).

### Alternatives Considered

| Approach | Chosen? | Why |
|----------|---------|-----|
| VP-as-Bearer with `validUntil` | Yes (Phase 2) | Standards-aligned, no server state, sufficient for experimental use |
| Full VCALM challenge/nonce | Deferred | More replay protection but requires server-side state management |
| Bare VC as Bearer (no VP) | Rejected | No holder binding — replayable by anyone who intercepts the VC |
| OAuth token exchange | Deferred | Requires OAuth AS infrastructure; relevant for Okta integration |
| Starlette middleware | Rejected | Less explicit than DI; harder to extend per-route for Option C |
| Token introspection endpoint | Rejected | Premature complexity; no JWTs in current stack |
