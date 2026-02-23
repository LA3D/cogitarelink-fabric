#!/usr/bin/env python3
"""Startup bootstrap: load TBox ontologies into Oxigraph via Graph Store HTTP Protocol."""
import os
import pathlib
import time
import urllib.request
import urllib.parse

OXIGRAPH_URL = os.environ.get("OXIGRAPH_URL", "http://localhost:7878")
NODE_BASE = os.environ.get("NODE_BASE", "http://localhost:8080")
ONTOLOGY_DIR = pathlib.Path(os.environ.get("ONTOLOGY_DIR", "/app/ontology"))


def put_graph(graph_uri: str, ttl: str, retries: int = 2) -> None:
    encoded = urllib.parse.quote(graph_uri, safe="")
    url = f"{OXIGRAPH_URL}/store?graph={encoded}"
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                url, data=ttl.encode(), method="PUT",
                headers={"Content-Type": "text/turtle"},
            )
            with urllib.request.urlopen(req) as r:
                print(f"  PUT <{graph_uri}>: HTTP {r.status}", flush=True)
            return
        except urllib.error.URLError as e:
            if attempt < retries:
                print(f"  Retry {attempt + 1}/{retries}: {e}", flush=True)
                time.sleep(1)
            else:
                raise


def main() -> None:
    ttl_files = sorted(ONTOLOGY_DIR.glob("*.ttl"))
    if not ttl_files:
        print(f"WARNING: no .ttl files in {ONTOLOGY_DIR}", flush=True)
    for f in ttl_files:
        if f.name.endswith("-profile.ttl"):
            continue
        graph_uri = f"{NODE_BASE}/ontology/{f.stem}"
        try:
            print(f"Loading {f.name} into <{graph_uri}>...", flush=True)
            put_graph(graph_uri, f.read_text())
        except Exception as e:
            print(f"WARNING: failed to load {f.name}: {e}", flush=True)
    print("Bootstrap complete.", flush=True)


if __name__ == "__main__":
    main()
