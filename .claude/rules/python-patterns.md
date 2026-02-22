---
paths: ["**/*.py"]
---

# Python Patterns

## Style (fastai philosophy)
- Brevity facilitates reasoning — one concept per screen
- Abbreviations for common names: `g` for graph, `ep` for endpoint, `obs` for observation, `shp` for shape
- No comments unless explaining WHY (not what)
- No docstrings on internal functions; type hints on public functions only
- No auto-linter formatting; maintain intentional style

## HTTP
Use `httpx` for async HTTP, not `requests`:
```python
async with httpx.AsyncClient() as client:
    r = await client.get(ep + "/.well-known/void", headers={"Accept": "text/turtle"})
    r.raise_for_status()
```

## RDF (pyoxigraph)
```python
import pyoxigraph as ox
g = ox.Store()                          # in-process store
g.load(path, format=ox.RdfFormat.TURTLE)
for triple in g.quads_for_pattern(None, RDF_TYPE, SOSA_OBSERVATION, None):
    ...
```
Note: pyoxigraph 0.5.x uses RDF 1.2 (`rdf-12`) by default; `rdf-star` removed. Use `quads_for_pattern()` (new in 0.5.5).

## SHACL Validation
```python
from pyshacl import validate
conforms, report_g, report_text = validate(
    data_graph=g, shacl_graph=shapes_g, inference="rdfs"
)
if not conforms:
    parse_agent_instructions(report_g)  # extract sh:agentInstruction violations
```

## DSPy (RLM agents)
- `aforward()` for async signatures
- `program.json` for serialized program state
- `GraphRunContext[QueryState]` from pydantic-graph for typed state (experimental)
- Structured output via `dspy.Prediction` with typed fields

## FastAPI (fabric gateway)
```python
from fastapi import FastAPI, Response
app = FastAPI()

@app.get("/.well-known/void")
async def void_sd(accept: str = Header("text/turtle")):
    return Response(content=VOID_TTL, media_type="text/turtle")
```

## Async-first
All IO operations use async/await. No blocking calls in async context.
Use `asyncio.gather` for parallel endpoint queries (scatter in scatter-gather).

## Error handling
Raise specific exceptions at system boundaries (HTTP calls, RDF parse, SHACL validate).
Don't catch-all internally; let errors surface to the RLM agent for adaptive retry.
