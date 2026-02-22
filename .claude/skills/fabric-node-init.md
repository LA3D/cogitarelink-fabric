# /fabric-node-init

Scaffold a new fabric node: Docker Compose service, FastAPI stub, .well-known/ templates, Oxigraph named graph setup.

## Usage
```
/fabric-node-init <node-name> [--port <gateway-port>] [--domain <node-domain>]
```
Example: `/fabric-node-init sdl-instrument --port 8081 --domain sdl.fabric.example.org`

## Steps

1. **Create directory structure**:
   ```
   fabric/{node-name}/
   ├── docker-compose.yml
   ├── gateway/
   │   ├── Dockerfile
   │   ├── main.py          # FastAPI app
   │   ├── well_known.py    # .well-known/ routes
   │   └── requirements.txt
   ├── oxigraph/
   │   └── config.toml
   ├── credo/
   │   ├── Dockerfile
   │   ├── src/agent.ts
   │   └── package.json
   └── well-known/
       ├── void.ttl          # L1: SD + VoID template
       ├── shacl.ttl         # L3: endpoint-specific shapes template
       └── sparql-examples/  # L4: example queries directory
   ```

2. **docker-compose.yml**: Three-container pattern per docker-patterns.md
   - fabric-node (FastAPI :gateway-port), oxigraph (Oxigraph), credo-sidecar (Credo :3000+offset)
   - `platform: linux/amd64` on credo-sidecar
   - Named volumes for oxigraph-data and did-data

3. **well-known/void.ttl**: Template with:
   - `dct:conformsTo <fabric:CoreProfile>`
   - `void:sparqlEndpoint <https://{domain}/sparql>`
   - `void:vocabulary` stubs for SOSA, QUDT, PROV-O
   - Named graph stubs (observations, entities, claims, mappings, crosswalks)

4. **well-known/shacl.ttl**: Minimal endpoint shape template with `sh:agentInstruction` placeholder

5. **FastAPI main.py**: Routes for `.well-known/void`, `.well-known/shacl`, `.well-known/sparql-examples`, `/sparql` (proxy to Oxigraph), `/entity/{uuid}`

6. **Named graph initialization SPARQL**: `fabric/{node-name}/init/setup.rq` — creates empty named graphs + loads TBox from ontology/ directory

7. Report: files created + next steps (load ontology, customize shapes, run docker compose up)
