---
paths: ["**/docker-compose*.yml", "**/Dockerfile*"]
---

# Docker Patterns

## Per-node structure (D8)
Three containers per fabric node:
```yaml
services:
  fabric-node:          # FastAPI gateway (Python)
    build: ./fabric/node
    ports: ["8080:8080"]
    depends_on: [oxigraph, credo-sidecar]
    volumes:
      - did-data:/app/did  # shared DID document

  oxigraph:             # Oxigraph SPARQL 1.2 HTTP server
    image: ghcr.io/oxigraph/oxigraph:latest
    ports: ["7878:7878"]
    volumes:
      - oxigraph-data:/data
    command: serve --location /data --bind 0.0.0.0:7878

  credo-sidecar:        # Credo-TS + Express (Node.js)
    build: ./fabric/credo
    platform: linux/amd64  # Apple Silicon compatibility (D8)
    ports: ["3000:3000"]
    volumes:
      - did-data:/app/did  # shared DID document

volumes:
  did-data:
  oxigraph-data:
```

## Apple Silicon (D8)
Always include `platform: linux/amd64` on the credo-sidecar service.
Credo-TS native modules (Askar) are not available for ARM.
Rosetta 2 emulation works; do not attempt ARM builds.

## Phoenix observability (D16)
```yaml
  phoenix:
    image: arizephoenix/phoenix:latest
    ports:
      - "6006:6006"   # Phoenix UI
      - "4317:4317"   # OTLP gRPC
```

## Bootstrap service (D12)
Include a one-shot `bootstrap` service that:
1. Creates did:webvh for the node
2. Issues FabricConformanceCredential
3. Writes to /graph/registry
4. Exits (restart: "no")

## Named volumes
Use named volumes for Oxigraph data persistence — not bind mounts.
Bind mounts cause permission issues on macOS with Docker Desktop.

## Health checks
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/.well-known/void"]
  interval: 10s
  timeout: 5s
  retries: 3
```

## Port conventions
- 8080: FastAPI gateway (fabric node HTTP API)
- 7878: Oxigraph direct (internal only in production; exposed for dev)
- 3000: Credo sidecar
- 6006: Phoenix UI
- 4317: OTLP gRPC (Phoenix)
