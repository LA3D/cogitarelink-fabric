# Caddy HTTPS Migration Design

**Date**: 2026-02-26
**Decision**: D30
**Status**: Approved — pre-stage before VC-gated SPARQL access (D13/D14 enforcement)

---

## Context

The did:webvh spec requires HTTPS (`HTTPS GET` for DID resolution is normative, not advisory). The current `NODE_BASE=http://localhost:8080` setup violates this requirement and breaks the trust chain at step 2:

```
DNS resolution
  → TLS certificate validates domain       ← broken: no TLS, no real domain
    → HTTPS /.well-known/did.json → DID document
      → VC signed by DID key
        → AgentAuthorizationCredential
```

Agents must be able to verify that the service they are talking to IS the entity described by the DID and VCs — DNS + TLS is the root of that chain. This is the same principle as Hyperledger Fabric's MSP enrollment certificates providing both transport identity (mTLS) and application identity (transaction signing) from the same key material.

Additionally, all fabric entity URIs (D6, D11) and service endpoints embedded in VCs currently reference `http://localhost:8080`, which is not a resolvable identifier outside the developer's machine.

---

## Decision

Add Caddy as a TLS-terminating reverse proxy to Docker Compose. Use `bootstrap.cogitarelink.ai` as the canonical node identity. Set `NODE_BASE=https://bootstrap.cogitarelink.ai`. The DID, all VoID service descriptions, VC credential subjects, and entity URIs resolve to this domain.

**Naming convention**:
- Bootstrap/gateway node: `bootstrap.cogitarelink.ai`
- Future org nodes: `{unit}.{org}.cogitarelink.ai` (e.g., `crc.nd.cogitarelink.ai` for CRC at Notre Dame)

The domain hierarchy encodes organizational affiliation directly in the DID, which is appropriate for a federated fabric where nodes belong to institutions.

---

## Architecture

### Local development topology

```
Mac /etc/hosts:  127.0.0.1  bootstrap.cogitarelink.ai
                     ↓
Caddy :443 (tls internal)
  └── reverse_proxy → fabric-node :8080 (internal Docker network, HTTP)

Internal Docker network (HTTP only):
  fabric-node :8080  →  oxigraph :7878
  fabric-node :8080  →  credo-sidecar :3000
```

Caddy handles TLS termination. All inter-service communication within Docker stays on HTTP. Only the external boundary uses HTTPS.

### Production topology (CRC VM)

Identical Docker Compose, two changes:
1. Remove `tls internal` from Caddyfile — Caddy auto-negotiates Let's Encrypt
2. Add A record in Namecheap: `bootstrap.cogitarelink.ai → CRC VM IP`

No code changes. The same Docker Compose image works for both.

---

## Caddyfile

```
bootstrap.cogitarelink.ai {
    tls internal
    reverse_proxy fabric-node:8080
}
```

Production (remove `tls internal` block entirely):
```
bootstrap.cogitarelink.ai {
    reverse_proxy fabric-node:8080
}
```

---

## Docker Compose changes

New `caddy` service:
```yaml
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
```

New volumes:
```yaml
volumes:
  caddy-data:
  caddy-config:
```

Environment change on `fabric-node` and `credo-sidecar`:
```yaml
NODE_BASE: https://bootstrap.cogitarelink.ai
```

---

## macOS one-time setup

```bash
# 1. Add hosts entry
echo "127.0.0.1  bootstrap.cogitarelink.ai" | sudo tee -a /etc/hosts

# 2. Start the stack
docker compose up -d --build

# 3. Trust Caddy's CA in macOS System Keychain
docker cp $(docker compose ps -q caddy):/data/caddy/pki/authorities/local/root.crt ./caddy-root.crt
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain caddy-root.crt
```

After step 3, `https://bootstrap.cogitarelink.ai` is trusted system-wide — browsers, curl, Python httpx, HURL all accept it without flags.

---

## Volume reset required

The DID is minted at first boot from `NODE_BASE`. The existing `did-data` volume contains a DID with domain `localhost%253A8080` and must be wiped:

```bash
docker compose down -v   # destroys did-data volume
docker compose up -d --build
```

All SPARQL data in Oxigraph is also wiped. Bootstrap reruns cleanly.

---

## Test changes

- HURL tests: base URL changes to `https://bootstrap.cogitarelink.ai`; CA cert passed via `--cacert ./caddy-root.crt` or mounted into test runner
- pytest integration tests: `BASE_URL` env var, httpx client `verify="./caddy-root.crt"` (or env var `SSL_CERT_FILE`)
- pytest conftest: add fixture that reads `FABRIC_CA_CERT` env var (default `./caddy-root.crt`)

---

## What this enables

Once in place:
- VC-gated SPARQL access (D13/D14 enforcement) has a proper trust chain to verify
- `discover_endpoint()` can perform full DID resolution with HTTPS verification
- Entity URIs (`https://bootstrap.cogitarelink.ai/entity/{uuid7}`) are resolvable identifiers
- The node is deployable to CRC VM with a one-line Caddyfile change

---

## Alternatives considered

**tls internal only, keep localhost** — Technically works for local testing but violates did:webvh spec HTTPS requirement and produces non-resolvable entity URIs. The trust chain cannot be validated by external agents. Rejected.

**DNS-01 challenge via Namecheap API** — Would get a real Let's Encrypt cert locally. Rejected for Phase 2 due to: Namecheap IP whitelist requirement (breaks on VPN/travel), Namecheap API rewrites entire DNS zone on each update (data loss risk), Let's Encrypt rate limits during development. Viable for production if Caddy automatic HTTPS doesn't fit.

**mkcert** — Developer tool, requires per-machine installation, not integrated into Docker Compose. Does not model production topology. Rejected.

**Custom CA in Docker** — Generate CA, distribute to containers. More complex than Caddy `tls internal` which handles this automatically. Rejected.

---

**See**: Decision D30 in KF-Prototype-Decisions.md
