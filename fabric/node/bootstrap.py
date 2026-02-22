#!/usr/bin/env python3
"""Startup bootstrap: load SOSA TBox stub into Oxigraph via Graph Store HTTP Protocol."""
import os
import pathlib
import urllib.request
import urllib.parse

OXIGRAPH_URL = os.environ.get("OXIGRAPH_URL", "http://localhost:7878")
NODE_BASE = os.environ.get("NODE_BASE", "http://localhost:8080")
TBOX_GRAPH = f"{NODE_BASE}/graph/tbox/sosa"
ONTOLOGY_DIR = pathlib.Path(os.environ.get("ONTOLOGY_DIR", "/app/ontology"))


def put_graph(graph_uri: str, ttl: str) -> None:
    encoded = urllib.parse.quote(graph_uri, safe="")
    url = f"{OXIGRAPH_URL}/store?graph={encoded}"
    req = urllib.request.Request(
        url, data=ttl.encode(), method="PUT",
        headers={"Content-Type": "text/turtle"},
    )
    with urllib.request.urlopen(req) as r:
        print(f"  PUT <{graph_uri}>: HTTP {r.status}", flush=True)


def main() -> None:
    stub = ONTOLOGY_DIR / "sosa-tbox-stub.ttl"
    if stub.exists():
        print(f"Loading SOSA TBox stub into <{TBOX_GRAPH}>...", flush=True)
        put_graph(TBOX_GRAPH, stub.read_text())
    else:
        print(f"WARNING: {stub} not found — skipping TBox load", flush=True)
    print("Bootstrap complete.", flush=True)


if __name__ == "__main__":
    main()
