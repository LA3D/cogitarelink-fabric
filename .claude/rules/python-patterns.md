---
paths: ["**/*.py"]
---

# Python Patterns

## Environments

Two environments — know which one applies:

| Context | Python | Key packages |
|---|---|---|
| **Claude Code tool use** | `~/uvws/.venv/bin/python` (3.12.12) | rdflib 7.6.0, pyshacl 0.31.0, owlrl 7.1.4, dspy 3.1.3†, sparqlx 0.10.0, httpx 0.28.1 |
| **Fabric project code** | Project venv / Docker | Oxigraph HTTP server (no pyoxigraph in global venv); FastAPI, uvicorn |

† **dspy is pinned to a fork**: `git+https://github.com/rawwerks/dspy.git@feat/rlm-media-types-protocol`
(PR [stanfordnlp/dspy#9295](https://github.com/stanfordnlp/dspy/pull/9295) — adds multimodal media types, budget controls, multi-model routing, LocalInterpreter, depth>1 to RLM; not yet merged to main).
Install: `uv pip install "git+https://github.com/rawwerks/dspy.git@feat/rlm-media-types-protocol"`
When PR merges and a release ships, revert to: `uv pip install "dspy>=<merged-version>"`

For ad-hoc RDF/SPARQL/validation work from Claude Code, use `~/uvws/.venv/bin/python`.

## Style (fastai philosophy)
- Brevity facilitates reasoning — one concept per screen
- Abbreviations: `g` for graph, `ep` for endpoint, `obs` for observation, `shp` for shape
- No comments unless explaining WHY
- No docstrings on internal functions; type hints on public functions only
- No auto-linter formatting; maintain intentional style

## RDF — rdflib 7.6 (Claude Code tool use)

```python
from rdflib import Graph, Dataset, ConjunctiveGraph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL, SKOS, PROV, DCAT, SDO

# In-process graph (named graphs via Dataset)
g = Dataset()
g.parse("path/to/file.ttl", format="turtle")
g.parse("https://example.org/vocab", format="turtle")

# Named graph access
ng = g.graph(URIRef("https://node.example.org/graph/observations"))

# SPARQL over in-process graph
results = g.query("""
    SELECT ?s ?o WHERE {
        GRAPH <https://node.example.org/graph/observations> {
            ?s a sosa:Observation ; sosa:hasResult ?o .
        }
    }
""")

# JSON-LD built-in (rdflib 7, no rdflib_jsonld needed)
g.parse("data.jsonld", format="json-ld")
g.serialize("out.jsonld", format="json-ld")
```

## SPARQL over HTTP — sparqlx (async, SPARQL 1.2)

```python
from sparqlx import SPARQLWrapper

# Async usage (preferred)
async with SPARQLWrapper(sparql_endpoint="http://localhost:8080/sparql") as sw:
    results = await sw.query("SELECT ?s WHERE { ?s a sosa:Observation } LIMIT 10")
    for row in results:
        print(row)

# Also accepts rdflib.Graph directly (no HTTP needed)
from rdflib import Dataset
g = Dataset()
g.parse("file.ttl")
async with SPARQLWrapper(sparql_endpoint=g) as sw:
    results = await sw.query("SELECT ?s WHERE { ?s a sosa:Observation }")
```

Use `sparqlx` instead of `rdflib.plugins.stores.sparqlstore.SPARQLStore` for HTTP — it's httpx-based (async-native, SPARQL 1.2 compliant).

## OWL-RL Reasoning — owlrl 7.1

```python
import owlrl
from rdflib import Graph

g = Graph()
g.parse("fabric-vocab.ttl", format="turtle")
g.parse("data.ttl", format="turtle")

# Apply OWL-RL closure
owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(g)
# Now subclass/subproperty inferences are materialized
```

## SHACL Validation — pyshacl 0.31

```python
from pyshacl import validate

conforms, report_g, report_text = validate(
    data_graph=data_g,
    shacl_graph=shapes_g,
    inference="rdfs",           # or "owlrl" for OWL-RL pre-inference
    advanced=True,              # SPARQL-based rules + sh:agentInstruction
)
if not conforms:
    # parse sh:agentInstruction from violations
    SHACL = Namespace("http://www.w3.org/ns/shacl#")
    for result in report_g.subjects(RDF.type, SHACL.ValidationResult):
        msg = report_g.value(result, SHACL.resultMessage)
        hint = report_g.value(
            report_g.value(result, SHACL.sourceShape), SHACL.agentInstruction
        )
```

## dspy.RLM — REPL-based agents (dspy 3.1)

`dspy.RLM` is in `dspy.predict`. The LLM writes Python code in a REPL loop to iteratively explore context and build answers. Built-in sandbox tools: `llm_query(prompt)`, `llm_query_batched(prompts)`, `SUBMIT(result)`, `budget()`.

```python
import dspy

dspy.configure(lm=dspy.LM("anthropic/claude-sonnet-4-6"))

# Basic: string signature
rlm = dspy.RLM(
    "endpoint_sd, query -> answer",
    max_iterations=20,
    max_llm_calls=50,
    verbose=True,
)
result = rlm(endpoint_sd=void_ttl, query="find CV observations for KCl")
print(result.answer)

# With fabric tools exposed to REPL
def sparql_query(endpoint: str, query: str) -> str:
    """Execute SPARQL SELECT against endpoint, return JSON results."""
    import httpx
    r = httpx.post(endpoint, data={"query": query},
                   headers={"Accept": "application/sparql-results+json"})
    return r.text

def fetch_void(endpoint_base: str) -> str:
    """Fetch .well-known/void as Turtle."""
    import httpx
    r = httpx.get(f"{endpoint_base}/.well-known/void",
                  headers={"Accept": "text/turtle"})
    return r.text

rlm = dspy.RLM(
    "endpoint_base, query -> answer",
    tools=[sparql_query, fetch_void],
    max_iterations=30,
)

# Async
result = await rlm.aforward(endpoint_base="http://localhost:8080", query="...")
```

**Key RLM parameters:**
- `signature` — `"input_fields -> output_fields"` or `dspy.Signature` subclass
- `tools` — list of functions or `dspy.Tool` objects callable from REPL code
- `max_iterations` — REPL turns (default 20)
- `max_llm_calls` — sub-LLM calls via `llm_query` (default 50)
- `max_depth` — recursion depth for nested RLMs (default 1 = no recursion)
- `interpreter` — `PythonInterpreter` (default, WASM sandbox) or custom

**Typed Signature:**
```python
class FabricQuery(dspy.Signature):
    """Navigate a fabric endpoint to answer a natural language query."""
    endpoint_base: str = dspy.InputField(desc="Base URL of fabric node")
    query: str = dspy.InputField(desc="Natural language query")
    answer: str = dspy.OutputField(desc="Answer with supporting evidence")
    sources: list[str] = dspy.OutputField(desc="Named graphs consulted")

rlm = dspy.RLM(FabricQuery, tools=[sparql_query, fetch_void])
```

## HTTP — httpx (async)

```python
import httpx

async with httpx.AsyncClient() as client:
    r = await client.get(
        ep + "/.well-known/void",
        headers={"Accept": "text/turtle"}
    )
    r.raise_for_status()
    ttl = r.text
```

## Async-first

All IO: async/await. Use `asyncio.gather` for parallel endpoint queries (scatter).
No blocking calls in async context.

## Error handling

Raise specific exceptions at system boundaries. Don't catch-all internally — let errors surface to the RLM agent for adaptive retry.
