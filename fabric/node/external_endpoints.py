"""External endpoint attestation helpers — D29.

Loads external-endpoints.ttl.template, substitutes {base}/{node_did}.
Bootstrap appends the resulting Turtle to /graph/catalog via Oxigraph's
Graph Store Protocol (POST /store?graph=<uri>) — no SPARQL INSERT needed.
Same pattern as catalog.py / registry.py.
"""
import pathlib

_TEMPLATE_PATH = pathlib.Path(__file__).parent / "external-endpoints.ttl.template"


def load_external_endpoints_ttl(node_base: str, node_did: str) -> str:
    """Substitute {base}/{node_did} in the template; return Turtle string."""
    tmpl = _TEMPLATE_PATH.read_text()
    return tmpl.replace("{base}", node_base).replace("{node_did}", node_did)
