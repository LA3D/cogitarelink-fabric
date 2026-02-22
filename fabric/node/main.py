import os
import pathlib
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse

OXIGRAPH_URL = os.environ.get("OXIGRAPH_URL", "http://localhost:7878")
NODE_BASE = os.environ.get("NODE_BASE", "http://localhost:8080")
SHAPES_DIR = pathlib.Path(os.environ.get("SHAPES_DIR", "/app/shapes"))
SPARQL_DIR = pathlib.Path(os.environ.get("SPARQL_DIR", "/app/sparql"))
# Phase 1: unauthenticated — gated by VC-based access control in Phase 2 (D13, D19)
SPARQL_UPDATE_ENABLED = os.environ.get("SPARQL_UPDATE_ENABLED", "true").lower() == "true"

_VOID_TURTLE = """\
@prefix void: <http://rdfs.org/ns/void#> .
@prefix dct:  <http://purl.org/dc/terms/> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

<{base}/.well-known/void>
    a void:Dataset ;
    dct:title "cogitarelink-fabric node"^^xsd:string ;
    void:sparqlEndpoint <{base}/sparql> ;
    void:vocabulary <http://www.w3.org/ns/sosa/> ;
    void:vocabulary <http://www.w3.org/2006/time#> .
"""

_VOID_JSONLD = """\
{{
  "@context": {{
    "void": "http://rdfs.org/ns/void#",
    "dct": "http://purl.org/dc/terms/"
  }},
  "@id": "{base}/.well-known/void",
  "@type": "void:Dataset",
  "dct:title": "cogitarelink-fabric node",
  "void:sparqlEndpoint": {{ "@id": "{base}/sparql" }},
  "void:vocabulary": [
    {{ "@id": "http://www.w3.org/ns/sosa/" }},
    {{ "@id": "http://www.w3.org/2006/time#" }}
  ]
}}
"""

# Proxy header allowlists — forward only what Oxigraph needs
_PROXY_REQUEST_HEADERS = {"accept", "content-type", "accept-encoding"}
_HOP_BY_HOP = {"transfer-encoding", "connection", "keep-alive"}


@asynccontextmanager
async def lifespan(app):
    app.state.http = httpx.AsyncClient(base_url=OXIGRAPH_URL)
    yield
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
    return PlainTextResponse(
        content=shapes_file.read_text(),
        media_type="text/turtle",
    )


@app.get("/.well-known/sparql-examples")
async def well_known_sparql_examples():
    examples_file = SPARQL_DIR / "sosa-examples.ttl"
    if not examples_file.exists():
        raise HTTPException(status_code=404, detail="SPARQL examples not found")
    content = examples_file.read_text().replace("{base}", NODE_BASE)
    return PlainTextResponse(content=content, media_type="text/turtle")


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
