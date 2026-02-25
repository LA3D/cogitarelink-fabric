#!/usr/bin/env python3
"""Startup bootstrap: load TBox ontologies + registry self-entry into Oxigraph."""
import json
import os
import pathlib
import time
import urllib.request
import urllib.parse

try:
    from fabric.node.registry import build_registry_insert
except ModuleNotFoundError:
    from registry import build_registry_insert

OXIGRAPH_URL = os.environ.get("OXIGRAPH_URL", "http://localhost:7878")
NODE_BASE = os.environ.get("NODE_BASE", "http://localhost:8080")
ONTOLOGY_DIR = pathlib.Path(os.environ.get("ONTOLOGY_DIR", "/app/ontology"))
SHARED_DIR = pathlib.Path(os.environ.get("SHARED_DIR", "/shared"))


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


def sparql_update(update: str) -> int:
    data = update.encode()
    req = urllib.request.Request(
        f"{OXIGRAPH_URL}/update",
        data=data,
        headers={"Content-Type": "application/sparql-update"},
    )
    with urllib.request.urlopen(req) as r:
        return r.status


def wait_for_conformance_vc(max_wait: int = 60) -> dict | None:
    """Poll /shared/conformance-vc.json until available (Credo writes it async)."""
    vc_path = SHARED_DIR / "conformance-vc.json"
    start = time.time()
    delay = 1
    while time.time() - start < max_wait:
        if vc_path.exists():
            try:
                vc = json.loads(vc_path.read_text())
                if vc.get("issuer"):
                    return vc
            except (json.JSONDecodeError, KeyError):
                pass
        print(f"  Waiting for conformance VC ({int(time.time() - start)}s)...", flush=True)
        time.sleep(delay)
        delay = min(delay * 2, 8)
    return None


def load_tbox_ontologies() -> None:
    """Load all .ttl ontology files into named graphs (D9 L2 TBox)."""
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


def register_self(node_did: str) -> None:
    """Insert self-entry into /graph/registry (D12)."""
    print(f"Registering self in /graph/registry (DID: {node_did})...", flush=True)
    sparql = build_registry_insert(NODE_BASE, node_did)
    status = sparql_update(sparql)
    print(f"  Registry self-entry: HTTP {status}", flush=True)


def main() -> None:
    print(f"Bootstrap: OXIGRAPH={OXIGRAPH_URL}, NODE_BASE={NODE_BASE}", flush=True)

    # 1. Load TBox ontologies
    load_tbox_ontologies()

    # 2. Wait for Credo conformance VC and register self
    vc = wait_for_conformance_vc()
    if vc:
        node_did = vc.get("issuer", "")
        if node_did:
            register_self(node_did)
        else:
            print("WARNING: conformance VC has no issuer — skipping registry", flush=True)
    else:
        print("WARNING: conformance VC not available — skipping registry", flush=True)

    print("Bootstrap complete.", flush=True)


if __name__ == "__main__":
    main()
