"""VoID→DCAT catalog helpers — rdflib-based VoID parsing (D23).

Same pattern as registry.py and did_resolver.py:
imported by main.py (Docker), bootstrap.py, and unit tests (local).
"""
from datetime import datetime, timezone

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF, DCTERMS

try:
    from fabric.node.did_resolver import sparql_escape
except ModuleNotFoundError:
    from did_resolver import sparql_escape

FABRIC_NS = "https://w3id.org/cogitarelink/fabric#"
# Open Namespace — rdflib's VOID ClosedNamespace lacks sparqlGraphEndpoint
VOID = Namespace("http://rdfs.org/ns/void#")


def extract_dcat_from_void(void_turtle: str, node_base: str) -> list[dict]:
    """Parse VoID Turtle, extract void:subset blocks as dataset dicts."""
    if not void_turtle.strip():
        return []

    g = Graph()
    g.parse(data=void_turtle, format="turtle")

    # Find the root VoID dataset (has void:subset children)
    root = None
    for s in g.subjects(RDF.type, VOID.Dataset):
        if (s, VOID.subset, None) in g:
            root = s
            break
    if root is None:
        return []

    # Collect top-level vocabularies (inherited by all subsets)
    top_vocabs = [str(o) for o in g.objects(root, VOID.vocabulary)]

    datasets = []
    for subset in g.objects(root, VOID.subset):
        title = g.value(subset, DCTERMS.title)
        graph_ep = g.value(subset, VOID.sparqlGraphEndpoint)
        if title and graph_ep:
            local_vocabs = [str(o) for o in g.objects(subset, VOID.vocabulary)]
            all_vocabs = list(dict.fromkeys(top_vocabs + local_vocabs))
            datasets.append({
                "title": str(title),
                "graph_endpoint": str(graph_ep),
                "vocabularies": all_vocabs,
            })
    return datasets


def build_catalog_insert(
    node_base: str, node_did: str, datasets: list[dict],
) -> str:
    """SPARQL INSERT DATA for /graph/catalog with dcat:Dataset entries."""
    now = datetime.now(timezone.utc).isoformat()
    triples = []
    for ds in datasets:
        safe_title = sparql_escape(ds["title"])
        graph_ep = ds["graph_endpoint"]
        vocab_lines = "\n".join(
            f'        void:vocabulary <{v}> ;'
            for v in ds.get("vocabularies", [])
        )
        triples.append(f"""\
    <{graph_ep}> a dcat:Dataset ;
        dct:title "{safe_title}" ;
        dcat:accessService <{node_base}/sparql> ;
        dct:publisher <{node_did}> ;
        dct:issued "{now}"^^xsd:dateTime ;
{vocab_lines}
        dcat:keyword "{safe_title.lower()}" .""")

    body = "\n".join(triples)
    return f"""\
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct:  <http://purl.org/dc/terms/>
PREFIX void: <http://rdfs.org/ns/void#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
INSERT DATA {{
  GRAPH <{node_base}/graph/catalog> {{
{body}
  }}
}}"""


def build_catalog_construct(node_base: str) -> str:
    """SPARQL CONSTRUCT returning all entries in /graph/catalog (Dataset + DataService)."""
    return f"""\
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct:  <http://purl.org/dc/terms/>
PREFIX void: <http://rdfs.org/ns/void#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
CONSTRUCT {{ ?s ?p ?o }}
WHERE {{
  GRAPH <{node_base}/graph/catalog> {{
    ?s ?p ?o .
  }}
}}"""
