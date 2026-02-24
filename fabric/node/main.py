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
ONTOLOGY_DIR = pathlib.Path(os.environ.get("ONTOLOGY_DIR", "/app/ontology"))
SHARED_DIR = pathlib.Path(os.environ.get("SHARED_DIR", "/shared"))
# Phase 1: unauthenticated — gated by VC-based access control in Phase 2 (D13, D19)
SPARQL_UPDATE_ENABLED = os.environ.get("SPARQL_UPDATE_ENABLED", "true").lower() == "true"

_VOID_TURTLE = """\
@prefix void: <http://rdfs.org/ns/void#> .
@prefix sd:   <http://www.w3.org/ns/sparql-service-description#> .
@prefix dct:  <http://purl.org/dc/terms/> .
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

# --- Service Description (D6) ---
<{base}/sparql> a sd:Service, dcat:DataService ;
    sd:supportedLanguage sd:SPARQL12Query, sd:SPARQL12Update ;
    dcat:servesDataset <{base}/dataset/observations> ;
    sd:defaultDataset [
        a sd:Dataset ;
        sd:namedGraph [
            sd:name <{base}/graph/observations> ;
            dct:conformsTo <https://w3id.org/cogitarelink/fabric#ObservationShape> ;
        ] ;
        sd:namedGraph [
            sd:name <{base}/graph/entities> ;
            dct:description "Sensor, platform, and observable-property descriptions (sosa:Sensor, sosa:Platform, sosa:ObservableProperty)." ;
        ] ;
        sd:namedGraph [
            sd:name <{base}/graph/metadata> ;
        ] ;
    ] .

# --- VoID Dataset (D6/D9) ---
<{base}/.well-known/void>
    a void:Dataset ;
    dct:title "cogitarelink-fabric node"^^xsd:string ;
    void:sparqlEndpoint <{base}/sparql> ;
    void:uriSpace "{base}/entity/" ;
    void:vocabulary <http://www.w3.org/ns/sosa/> ;
    void:vocabulary <http://www.w3.org/2006/time#> ;
    void:vocabulary <http://www.w3.org/ns/prov#> ;
    void:vocabulary <http://semanticscience.org/resource/> ;
    dct:conformsTo <https://w3id.org/cogitarelink/fabric#CoreProfile> ;
    void:subset [
        a void:Dataset ;
        dct:title "Observations" ;
        void:sparqlGraphEndpoint <{base}/graph/observations> ;
        dct:conformsTo <https://w3id.org/cogitarelink/fabric#ObservationShape> ;
    ] ;
    void:subset [
        a void:Dataset ;
        dct:title "Entities" ;
        dct:description "Sensor, platform, and observable-property descriptions." ;
        void:sparqlGraphEndpoint <{base}/graph/entities> ;
    ] .

# --- DCAT Dataset Description (D23) ---
# Topic-level metadata for fabric catalog harvesting and agent query routing.
<{base}/dataset/observations> a dcat:Dataset ;
    dct:title "SDL Electrochemical Observations"^^xsd:string ;
    dct:description "SOSA/SSN sensor observations with SIO measurement attributes from automated potentiostat station"^^xsd:string ;
    dcat:theme <http://dbpedia.org/resource/Electrochemistry> ,
               <http://dbpedia.org/resource/Cyclic_voltammetry> ;
    dcat:keyword "electrochemistry", "potentiostat", "cyclic voltammetry", "SDL", "SOSA", "SIO" ;
    void:vocabulary <http://www.w3.org/ns/sosa/> ,
                    <http://www.w3.org/2006/time#> ,
                    <http://www.w3.org/ns/prov#> ,
                    <http://semanticscience.org/resource/> ;
    dct:conformsTo <https://w3id.org/cogitarelink/fabric#CoreProfile> ;
    dcat:distribution [
        a dcat:Distribution ;
        dcat:accessService <{base}/sparql> ;
        dcat:accessURL <{base}/sparql> ;
        dct:format "application/sparql-results+json"
    ] .
"""

_VOID_JSONLD = """\
{{
  "@context": {{
    "void": "http://rdfs.org/ns/void#",
    "sd": "http://www.w3.org/ns/sparql-service-description#",
    "dct": "http://purl.org/dc/terms/",
    "dcat": "http://www.w3.org/ns/dcat#"
  }},
  "@graph": [
    {{
      "@id": "{base}/sparql",
      "@type": ["sd:Service", "dcat:DataService"],
      "dcat:servesDataset": {{ "@id": "{base}/dataset/observations" }}
    }},
    {{
      "@id": "{base}/.well-known/void",
      "@type": "void:Dataset",
      "dct:title": "cogitarelink-fabric node",
      "void:sparqlEndpoint": {{ "@id": "{base}/sparql" }},
      "void:uriSpace": "{base}/entity/",
      "void:vocabulary": [
        {{ "@id": "http://www.w3.org/ns/sosa/" }},
        {{ "@id": "http://www.w3.org/2006/time#" }},
        {{ "@id": "http://www.w3.org/ns/prov#" }},
        {{ "@id": "http://semanticscience.org/resource/" }}
      ],
      "dct:conformsTo": {{ "@id": "https://w3id.org/cogitarelink/fabric#CoreProfile" }},
      "void:subset": [
        {{
          "@type": "void:Dataset",
          "dct:title": "Observations",
          "void:sparqlGraphEndpoint": {{ "@id": "{base}/graph/observations" }},
          "dct:conformsTo": {{ "@id": "https://w3id.org/cogitarelink/fabric#ObservationShape" }}
        }},
        {{
          "@type": "void:Dataset",
          "dct:title": "Entities",
          "dct:description": "Sensor, platform, and observable-property descriptions.",
          "void:sparqlGraphEndpoint": {{ "@id": "{base}/graph/entities" }}
        }}
      ]
    }},
    {{
      "@id": "{base}/dataset/observations",
      "@type": "dcat:Dataset",
      "dct:title": "SDL Electrochemical Observations",
      "dct:description": "SOSA/SSN sensor observations with SIO measurement attributes from automated potentiostat station",
      "dcat:theme": [
        {{ "@id": "http://dbpedia.org/resource/Electrochemistry" }},
        {{ "@id": "http://dbpedia.org/resource/Cyclic_voltammetry" }}
      ],
      "dcat:keyword": ["electrochemistry", "potentiostat", "cyclic voltammetry", "SDL", "SOSA", "SIO"],
      "void:vocabulary": [
        {{ "@id": "http://www.w3.org/ns/sosa/" }},
        {{ "@id": "http://www.w3.org/2006/time#" }},
        {{ "@id": "http://www.w3.org/ns/prov#" }},
        {{ "@id": "http://semanticscience.org/resource/" }}
      ],
      "dct:conformsTo": {{ "@id": "https://w3id.org/cogitarelink/fabric#CoreProfile" }},
      "dcat:distribution": {{
        "@type": "dcat:Distribution",
        "dcat:accessService": {{ "@id": "{base}/sparql" }},
        "dcat:accessURL": {{ "@id": "{base}/sparql" }},
        "dct:format": "application/sparql-results+json"
      }}
    }}
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
    import json
    did_log = SHARED_DIR / "did.jsonl"
    if not did_log.exists():
        raise HTTPException(status_code=404, detail="DID log not yet available")
    lines = [l.strip() for l in did_log.read_text().strip().split("\n") if l.strip()]
    if not lines:
        raise HTTPException(status_code=404, detail="DID log empty")
    last_entry = json.loads(lines[-1])
    # did:webvh log entries have the DID document in the "state" field
    did_doc = last_entry.get("state", last_entry)
    return JSONResponse(content=did_doc, media_type="application/ld+json")


@app.get("/.well-known/conformance-vc.json")
async def well_known_conformance_vc():
    """Serve FabricConformanceCredential VC from Credo sidecar shared volume."""
    import json
    vc_file = SHARED_DIR / "conformance-vc.json"
    if not vc_file.exists():
        raise HTTPException(status_code=404, detail="Conformance VC not yet available")
    vc = json.loads(vc_file.read_text())
    return JSONResponse(content=vc, media_type="application/ld+json")


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
