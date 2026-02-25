import json
import os
import pathlib
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import httpx
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
try:
    from fabric.node.void_templates import VOID_TURTLE as _VOID_TURTLE, VOID_JSONLD as _VOID_JSONLD
except ModuleNotFoundError:
    from void_templates import VOID_TURTLE as _VOID_TURTLE, VOID_JSONLD as _VOID_JSONLD
try:
    from fabric.node.did_resolver import (
        classify_identifier, parse_did_log, build_resolution_result,
        build_error_result, build_deref_result, decode_webvh_domain,
        sparql_escape, is_valid_uuid, uuid7,
    )
except ModuleNotFoundError:
    from did_resolver import (
        classify_identifier, parse_did_log, build_resolution_result,
        build_error_result, build_deref_result, decode_webvh_domain,
        sparql_escape, is_valid_uuid, uuid7,
    )
try:
    from fabric.node.registry import (
        build_registry_construct, build_registry_insert,
        build_agents_list_construct, build_agent_construct, build_agent_insert,
        check_void_conformance, VALID_AGENT_ROLES, FABRIC_NS,
    )
except ModuleNotFoundError:
    from registry import (
        build_registry_construct, build_registry_insert,
        build_agents_list_construct, build_agent_construct, build_agent_insert,
        check_void_conformance, VALID_AGENT_ROLES, FABRIC_NS,
    )
try:
    from fabric.node.integrity import verify_related_resources
except ModuleNotFoundError:
    from integrity import verify_related_resources

OXIGRAPH_URL = os.environ.get("OXIGRAPH_URL", "http://localhost:7878")
NODE_BASE = os.environ.get("NODE_BASE", "http://localhost:8080")
CREDO_URL = os.environ.get("CREDO_URL", "http://localhost:3000")
SHAPES_DIR = pathlib.Path(os.environ.get("SHAPES_DIR", "/app/shapes"))
SPARQL_DIR = pathlib.Path(os.environ.get("SPARQL_DIR", "/app/sparql"))
ONTOLOGY_DIR = pathlib.Path(os.environ.get("ONTOLOGY_DIR", "/app/ontology"))
SHARED_DIR = pathlib.Path(os.environ.get("SHARED_DIR", "/shared"))
# Phase 1: unauthenticated — gated by VC-based access control in Phase 2 (D13, D19)
SPARQL_UPDATE_ENABLED = os.environ.get("SPARQL_UPDATE_ENABLED", "true").lower() == "true"

# LDN inbox Link header (D25)
_LDN_LINK = f'<{NODE_BASE}/inbox>; rel="http://www.w3.org/ns/ldp#inbox"'

# Proxy header allowlists — forward only what Oxigraph needs
_PROXY_REQUEST_HEADERS = {"accept", "content-type", "accept-encoding"}
_HOP_BY_HOP = {"transfer-encoding", "connection", "keep-alive"}


@asynccontextmanager
async def lifespan(app):
    app.state.http = httpx.AsyncClient(base_url=OXIGRAPH_URL)
    app.state.http_credo = httpx.AsyncClient(base_url=CREDO_URL)
    app.state.http_external = httpx.AsyncClient()
    yield
    await app.state.http_external.aclose()
    await app.state.http_credo.aclose()
    await app.state.http.aclose()


app = FastAPI(title="cogitarelink-fabric node", lifespan=lifespan)


@app.get("/healthz")
async def healthz():
    return JSONResponse({"status": "ok"})


@app.get("/.well-known/void")
async def well_known_void(request: Request):
    accept = request.headers.get("accept", "text/turtle")
    if "application/ld+json" in accept:
        return Response(
            content=_VOID_JSONLD.format(base=NODE_BASE),
            media_type="application/ld+json",
        )
    return PlainTextResponse(
        content=_VOID_TURTLE.format(base=NODE_BASE),
        media_type="text/turtle",
    )


@app.get("/.well-known/profile")
async def well_known_profile():
    profile_file = ONTOLOGY_DIR / "fabric-core-profile.ttl"
    if not profile_file.exists():
        raise HTTPException(status_code=404, detail="Core profile not found")
    return PlainTextResponse(content=profile_file.read_text(), media_type="text/turtle")


@app.get("/entity/{entity_id}")
async def entity_deref(entity_id: str, request: Request):
    """FAIR A1: dereference entity URI via SPARQL CONSTRUCT across named graphs."""
    entity_uri = f"{NODE_BASE}/entity/{entity_id}"
    accept = request.headers.get("accept", "text/turtle")

    if "application/ld+json" in accept:
        fmt = "application/ld+json"
    elif "application/n-triples" in accept:
        fmt = "application/n-triples"
    else:
        fmt = "text/turtle"

    query = f"CONSTRUCT {{ <{entity_uri}> ?p ?o }} WHERE {{ GRAPH ?g {{ <{entity_uri}> ?p ?o }} }}"
    resp = await app.state.http.get(
        "/query", params={"query": query}, headers={"Accept": fmt},
    )

    # Oxigraph returns 200 with only prefix declarations for empty CONSTRUCT.
    # N-Triples has no prefixes, so empty = zero bytes. Turtle prefixes are short.
    body = resp.content.strip()
    if resp.status_code == 200 and (len(body) == 0 or entity_uri.encode() not in body):
        raise HTTPException(status_code=404, detail=f"Entity not found: {entity_uri}")

    return Response(content=resp.content, status_code=resp.status_code, media_type=fmt)


@app.get("/.well-known/shacl")
async def well_known_shacl():
    shapes_file = SHAPES_DIR / "endpoint-sosa.ttl"
    if not shapes_file.exists():
        raise HTTPException(status_code=404, detail="SHACL shapes not found")
    # Apply {base} substitution (same pattern as VoID and SPARQL examples)
    # so sh:pattern, sh:agentInstruction, and metadata IRI reflect actual node URL.
    content = shapes_file.read_text().replace("{base}", NODE_BASE)
    return PlainTextResponse(content=content, media_type="text/turtle")


@app.get("/.well-known/sparql-examples")
async def well_known_sparql_examples():
    examples_file = SPARQL_DIR / "sosa-examples.ttl"
    if not examples_file.exists():
        raise HTTPException(status_code=404, detail="SPARQL examples not found")
    content = examples_file.read_text().replace("{base}", NODE_BASE)
    return PlainTextResponse(content=content, media_type="text/turtle")


# --- Phase 2: W3C DID Resolution HTTP API (D3, D5, D25) ---

@app.get("/1.0/identifiers/{identifier:path}")
async def resolve_identifier(identifier: str, request: Request):
    kind = classify_identifier(identifier, NODE_BASE)
    accept = request.headers.get("accept", "application/did-resolution")

    if kind == "local-did":
        did_log = SHARED_DIR / "did.jsonl"
        if not did_log.exists():
            err = build_error_result("notFound", "DID log not yet available")
            return JSONResponse(content=err, status_code=404)
        result = parse_did_log(did_log.read_text(), target_did=identifier)
        if result is None:
            err = build_error_result("notFound", f"DID not found: {identifier}")
            return JSONResponse(content=err, status_code=404)
        did_doc, metadata = result
        if "application/did+ld+json" in accept or "application/did+json" in accept:
            return JSONResponse(content=did_doc, media_type="application/did+ld+json",
                headers={"Link": _LDN_LINK})
        return JSONResponse(content=build_resolution_result(did_doc, metadata),
            headers={"Link": _LDN_LINK})

    if kind == "local-entity":
        entity_id = identifier.rsplit("/entity/", 1)[-1]
        entity_uri = f"{NODE_BASE}/entity/{entity_id}"
        query = f"CONSTRUCT {{ <{entity_uri}> ?p ?o }} WHERE {{ GRAPH ?g {{ <{entity_uri}> ?p ?o }} }}"
        resp = await app.state.http.get(
            "/query", params={"query": query},
            headers={"Accept": "application/ld+json"},
        )
        body = resp.content.strip()
        if resp.status_code == 200 and (len(body) == 0 or entity_uri.encode() not in body):
            err = build_error_result("notFound", f"Entity not found: {entity_uri}")
            return JSONResponse(content=err, status_code=404)
        try:
            content = json.loads(resp.content)
        except json.JSONDecodeError:
            content = {"@value": resp.content.decode(errors="replace")}
        return JSONResponse(content=build_deref_result(content, "application/ld+json"))

    if kind == "remote-did":
        domain = decode_webvh_domain(identifier)
        if not domain:
            err = build_error_result("invalidDid", f"Cannot decode domain: {identifier}")
            return JSONResponse(content=err, status_code=400)
        err = build_error_result("methodNotSupported",
            f"Remote DID resolution not yet implemented (domain: {domain})")
        return JSONResponse(content=err, status_code=501)

    if kind == "did-key":
        err = build_error_result("methodNotSupported", "did:key resolution not yet implemented")
        return JSONResponse(content=err, status_code=501)

    if kind == "external-http":
        err = build_error_result("methodNotSupported", "External HTTP dereference not yet implemented")
        return JSONResponse(content=err, status_code=501)

    err = build_error_result("invalidDid", f"Unrecognized identifier: {identifier}")
    return JSONResponse(content=err, status_code=400)


# --- Phase 2: DID + VC routes from shared Credo volume (D5, D8, D12) ---

@app.get("/.well-known/did.jsonl")
async def well_known_did_jsonl():
    """Serve did:webvh DID log from Credo sidecar shared volume."""
    did_log = SHARED_DIR / "did.jsonl"
    if not did_log.exists():
        raise HTTPException(status_code=404, detail="DID log not yet available")
    return PlainTextResponse(content=did_log.read_text(), media_type="application/jsonl")


@app.get("/.well-known/did.json")
async def well_known_did_json():
    """Serve current DID document (last entry in did.jsonl log)."""
    did_log = SHARED_DIR / "did.jsonl"
    if not did_log.exists():
        raise HTTPException(status_code=404, detail="DID log not yet available")
    lines = [l.strip() for l in did_log.read_text().strip().split("\n") if l.strip()]
    if not lines:
        raise HTTPException(status_code=404, detail="DID log empty")
    last_entry = json.loads(lines[-1])
    # did:webvh log entries have the DID document in the "state" field
    did_doc = last_entry.get("state", last_entry)
    return JSONResponse(content=did_doc, media_type="application/ld+json",
        headers={"Link": _LDN_LINK})


@app.get("/.well-known/conformance-vc.json")
async def well_known_conformance_vc():
    """Serve FabricConformanceCredential VC from Credo sidecar shared volume."""
    vc_file = SHARED_DIR / "conformance-vc.json"
    if not vc_file.exists():
        raise HTTPException(status_code=404, detail="Conformance VC not yet available")
    vc = json.loads(vc_file.read_text())
    return JSONResponse(content=vc, media_type="application/ld+json")


# --- Phase 2: W3C Linked Data Notifications inbox (D25) ---

_LDN_MAX_PAYLOAD = 65536  # 64KB cap


@app.post("/inbox")
async def ldn_inbox_receive(request: Request):
    content_type = request.headers.get("content-type", "")
    if "application/ld+json" not in content_type and "application/json" not in content_type:
        return JSONResponse(status_code=415,
            content={"error": "Content-Type must be application/ld+json"})

    body = await request.body()
    if len(body) > _LDN_MAX_PAYLOAD:
        return JSONResponse(status_code=413,
            content={"error": "Payload too large (64KB max)"})

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    if "@context" not in payload:
        return JSONResponse(status_code=400,
            content={"error": "Missing @context — must be JSON-LD"})

    notif_id = uuid7()
    notif_iri = f"{NODE_BASE}/inbox/{notif_id}"
    now = datetime.now(timezone.utc).isoformat()
    safe_actor = sparql_escape(str(payload.get("actor", "anonymous")))
    escaped = sparql_escape(json.dumps(payload))
    sparql = f"""INSERT DATA {{
      GRAPH <{NODE_BASE}/graph/inbox> {{
        <{notif_iri}> a <http://www.w3.org/ns/ldp#Resource> ;
          <http://purl.org/dc/terms/created> "{now}"^^<http://www.w3.org/2001/XMLSchema#dateTime> ;
          <https://w3id.org/cogitarelink/fabric#actor> "{safe_actor}" ;
          <https://w3id.org/cogitarelink/fabric#notificationContent> "{escaped}" .
      }}
    }}"""
    resp = await app.state.http.post("/update", content=sparql,
        headers={"Content-Type": "application/sparql-update"})

    if resp.status_code >= 400:
        return JSONResponse(status_code=500, content={"error": "Storage failed"})

    return JSONResponse(status_code=201, content={"id": notif_iri},
        headers={"Location": notif_iri})


@app.get("/inbox")
async def ldn_inbox_list():
    query = f"""SELECT ?notif WHERE {{
      GRAPH <{NODE_BASE}/graph/inbox> {{
        ?notif a <http://www.w3.org/ns/ldp#Resource> ;
          <http://purl.org/dc/terms/created> ?created .
      }}
    }} ORDER BY DESC(?created)"""
    resp = await app.state.http.post("/query", content=query,
        headers={"Content-Type": "application/sparql-query",
                 "Accept": "application/sparql-results+json"})
    if resp.status_code >= 400:
        return JSONResponse(status_code=502, content={"error": "SPARQL query failed"})
    results = json.loads(resp.content)
    notifs = [b["notif"]["value"]
              for b in results.get("results", {}).get("bindings", [])]
    return JSONResponse(content={
        "@context": "http://www.w3.org/ns/ldp",
        "@id": f"{NODE_BASE}/inbox",
        "contains": notifs,
    }, media_type="application/ld+json")


@app.get("/inbox/{notification_id}")
async def ldn_inbox_get(notification_id: str):
    if not is_valid_uuid(notification_id):
        raise HTTPException(status_code=400, detail="Invalid notification ID")
    notif_iri = f"{NODE_BASE}/inbox/{notification_id}"
    query = f"""SELECT ?content WHERE {{
      GRAPH <{NODE_BASE}/graph/inbox> {{
        <{notif_iri}> <https://w3id.org/cogitarelink/fabric#notificationContent> ?content .
      }}
    }}"""
    resp = await app.state.http.post("/query", content=query,
        headers={"Content-Type": "application/sparql-query",
                 "Accept": "application/sparql-results+json"})
    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail="SPARQL query failed")
    results = json.loads(resp.content)
    bindings = results.get("results", {}).get("bindings", [])
    if not bindings:
        raise HTTPException(status_code=404, detail="Notification not found")
    content_str = bindings[0]["content"]["value"]
    return JSONResponse(content=json.loads(content_str), media_type="application/ld+json")


# --- Phase 2: Registry + Admission + Agents (D12, D13, D14) ---

async def _sparql_construct(query: str, accept: str) -> Response:
    """Run a CONSTRUCT query and return content-negotiated response."""
    if "application/ld+json" in accept:
        fmt = "application/ld+json"
    else:
        fmt = "text/turtle"
    resp = await app.state.http.get(
        "/query", params={"query": query}, headers={"Accept": fmt},
    )
    return Response(content=resp.content, status_code=resp.status_code, media_type=fmt)


@app.get("/fabric/registry")
async def fabric_registry(request: Request):
    """D12: List all registered fabric nodes."""
    accept = request.headers.get("accept", "text/turtle")
    query = build_registry_construct(NODE_BASE)
    return await _sparql_construct(query, accept)


@app.post("/fabric/admission")
async def fabric_admission(request: Request):
    """D12: Admit a node to the fabric with witness co-signing."""
    body = await request.json()
    remote_base = body.get("nodeBase", "").rstrip("/")
    if not remote_base:
        raise HTTPException(status_code=400, detail="nodeBase required")

    # 1. Fetch remote conformance VC
    try:
        vc_resp = await app.state.http_external.get(
            f"{remote_base}/.well-known/conformance-vc.json")
        vc_resp.raise_for_status()
        remote_vc = vc_resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Cannot fetch conformance VC: {e}")

    # 2. Fetch remote VoID and check conformance
    try:
        void_resp = await app.state.http_external.get(
            f"{remote_base}/.well-known/void",
            headers={"Accept": "text/turtle"})
        void_resp.raise_for_status()
        void_turtle = void_resp.text
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Cannot fetch VoID: {e}")

    if not check_void_conformance(void_turtle):
        raise HTTPException(status_code=422,
            detail="VoID missing dct:conformsTo fabric:CoreProfile")

    # 3. Verify VC proof via Credo
    verify_resp = await app.state.http_credo.post(
        "/credentials/verify", json=remote_vc)
    verify_result = verify_resp.json()
    if not verify_result.get("verified"):
        raise HTTPException(status_code=403,
            detail=f"VC proof verification failed: {verify_result.get('error', 'unknown')}")

    # 4. Verify D26 relatedResource hashes
    def fetcher(url):
        import httpx as _httpx
        r = _httpx.get(url)
        r.raise_for_status()
        return r.content
    hash_results = verify_related_resources(remote_vc, fetcher=fetcher)
    mismatches = [r for r in hash_results if not r.get("match")]
    if mismatches:
        raise HTTPException(status_code=409,
            detail=f"D26 hash mismatch: {[m['url'] for m in mismatches]}")

    # 5. Co-sign VC via Credo
    cosign_resp = await app.state.http_credo.post(
        "/credentials/cosign", json=remote_vc)
    if cosign_resp.status_code >= 400:
        raise HTTPException(status_code=502,
            detail=f"Co-signing failed: {cosign_resp.text}")
    cosigned_vc = cosign_resp.json()

    # 6. Insert remote node into /graph/registry
    remote_did = remote_vc.get("issuer", "")
    local_vc = SHARED_DIR / "conformance-vc.json"
    local_did = ""
    if local_vc.exists():
        try:
            local_did = json.loads(local_vc.read_text()).get("issuer", "")
        except Exception:
            pass
    sparql = build_registry_insert(remote_base, remote_did, registered_by=local_did or None)
    resp = await app.state.http.post(
        "/update", content=sparql.encode(),
        headers={"Content-Type": "application/sparql-update"})

    return JSONResponse(status_code=201, content=cosigned_vc)


@app.post("/agents/register")
async def agent_register(request: Request):
    """D13/D14: Register an agent and issue AgentAuthorizationCredential."""
    body = await request.json()
    agent_role = body.get("agentRole", "")
    authorized_graphs = body.get("authorizedGraphs", [])
    authorized_operations = body.get("authorizedOperations", [])

    if agent_role not in VALID_AGENT_ROLES:
        raise HTTPException(status_code=400,
            detail=f"Invalid agentRole: {agent_role}. Must be one of {sorted(VALID_AGENT_ROLES)}")

    # Proxy to Credo sidecar
    credo_resp = await app.state.http_credo.post("/agents/register", json=body)
    if credo_resp.status_code >= 400:
        raise HTTPException(status_code=credo_resp.status_code, detail=credo_resp.text)
    result = credo_resp.json()

    # Insert agent into /graph/agents
    agent_did = result.get("agentDid", "")
    if agent_did:
        sparql = build_agent_insert(
            NODE_BASE, agent_did, agent_role,
            authorized_graphs, authorized_operations)
        await app.state.http.post(
            "/update", content=sparql.encode(),
            headers={"Content-Type": "application/sparql-update"})

    return JSONResponse(status_code=201, content=result)


@app.get("/agents")
async def agents_list(request: Request):
    """D13: List all registered agents."""
    accept = request.headers.get("accept", "text/turtle")
    query = build_agents_list_construct(NODE_BASE)
    return await _sparql_construct(query, accept)


@app.get("/agents/{agent_id}")
async def agent_get(agent_id: str, request: Request):
    """D13: Get a single agent by ID."""
    if not is_valid_uuid(agent_id):
        raise HTTPException(status_code=400, detail="Invalid agent ID")
    # Reconstruct agent DID from the ID segment
    local_vc = SHARED_DIR / "conformance-vc.json"
    node_did = ""
    if local_vc.exists():
        try:
            node_did = json.loads(local_vc.read_text()).get("issuer", "")
        except Exception:
            pass
    agent_did = f"{node_did}:agents:{agent_id}" if node_did else f"{NODE_BASE}/agents/{agent_id}"
    accept = request.headers.get("accept", "text/turtle")
    query = build_agent_construct(NODE_BASE, agent_did)
    return await _sparql_construct(query, accept)


async def _proxy(request: Request, upstream_path: str) -> Response:
    body = await request.body()
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() in _PROXY_REQUEST_HEADERS
    }
    resp = await app.state.http.post(
        f"/{upstream_path}", content=body, headers=headers,
    )
    resp_headers = {
        k: v for k, v in resp.headers.items()
        if k.lower() not in _HOP_BY_HOP
    }
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=resp_headers,
    )


@app.post("/sparql")
async def sparql_query_proxy(request: Request):
    return await _proxy(request, "query")


@app.post("/sparql/update")
async def sparql_update_proxy(request: Request):
    # Phase 1: unauthenticated write access for local development.
    # Phase 2 gates this behind AgentAuthorizationCredential (D13, D19).
    if not SPARQL_UPDATE_ENABLED:
        raise HTTPException(status_code=403, detail="SPARQL Update disabled")
    return await _proxy(request, "update")
