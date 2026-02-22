import os
import pathlib
import httpx
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse

app = FastAPI(title="cogitarelink-fabric node")

OXIGRAPH_URL = os.environ.get("OXIGRAPH_URL", "http://localhost:7878")
NODE_BASE = os.environ.get("NODE_BASE", "http://localhost:8080")
SHAPES_DIR = pathlib.Path(os.environ.get("SHAPES_DIR", "/app/shapes"))

_VOID_TURTLE = """\
@prefix void: <http://rdfs.org/ns/void#> .
@prefix dct:  <http://purl.org/dc/terms/> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

<{base}/.well-known/void>
    a void:Dataset ;
    dct:title "cogitarelink-fabric node"^^xsd:string ;
    void:sparqlEndpoint <{base}/sparql> .
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
  "void:sparqlEndpoint": {{ "@id": "{base}/sparql" }}
}}
"""


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
    """FAIR A1: dereference entity URI via SPARQL DESCRIBE."""
    entity_uri = f"{NODE_BASE}/entity/{entity_id}"
    accept = request.headers.get("accept", "text/turtle")

    # Map Accept to a format Oxigraph supports for DESCRIBE
    if "application/ld+json" in accept:
        fmt = "application/ld+json"
    elif "application/n-triples" in accept:
        fmt = "application/n-triples"
    else:
        fmt = "text/turtle"

    # CONSTRUCT across all named graphs (DESCRIBE only hits default graph)
    query = f"CONSTRUCT {{ <{entity_uri}> ?p ?o }} WHERE {{ GRAPH ?g {{ <{entity_uri}> ?p ?o }} }}"
    params = {"query": query}
    headers = {"Accept": fmt}

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{OXIGRAPH_URL}/query",
            params=params,
            headers=headers,
        )

    if resp.status_code == 200 and entity_id.encode() not in resp.content:
        # Empty CONSTRUCT — entity not found in any named graph
        raise HTTPException(status_code=404, detail=f"Entity not found: {entity_uri}")

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=fmt,
    )


@app.get("/.well-known/shacl")
async def well_known_shacl():
    shapes_file = SHAPES_DIR / "endpoint-sosa.ttl"
    if not shapes_file.exists():
        raise HTTPException(status_code=404, detail="SHACL shapes not found")
    return PlainTextResponse(
        content=shapes_file.read_text(),
        media_type="text/turtle",
    )


async def _proxy(request: Request, upstream_path: str) -> Response:
    body = await request.body()
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length")
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{OXIGRAPH_URL}/{upstream_path}",
            content=body,
            headers=headers,
        )
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=dict(resp.headers),
    )


@app.post("/sparql")
async def sparql_query_proxy(request: Request):
    return await _proxy(request, "query")


@app.post("/sparql/update")
async def sparql_update_proxy(request: Request):
    return await _proxy(request, "update")
