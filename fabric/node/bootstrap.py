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
try:
    from fabric.node.catalog import extract_dcat_from_void, build_catalog_insert
except ModuleNotFoundError:
    from catalog import extract_dcat_from_void, build_catalog_insert
try:
    from fabric.node.void_templates import VOID_TURTLE
except ModuleNotFoundError:
    from void_templates import VOID_TURTLE

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


def populate_catalog(node_did: str) -> None:
    """Extract DCAT from VoID template and insert into /graph/catalog (D23)."""
    print("Populating /graph/catalog from VoID...", flush=True)
    void_turtle = VOID_TURTLE.format(base=NODE_BASE)
    datasets = extract_dcat_from_void(void_turtle, NODE_BASE)
    if not datasets:
        print("  WARNING: no datasets extracted from VoID", flush=True)
        return
    sparql = build_catalog_insert(NODE_BASE, node_did, datasets)
    status = sparql_update(sparql)
    print(f"  Catalog ({len(datasets)} datasets): HTTP {status}", flush=True)


def main() -> None:
    print(f"Bootstrap: OXIGRAPH={OXIGRAPH_URL}, NODE_BASE={NODE_BASE}", flush=True)

    # 1. Load TBox ontologies
    load_tbox_ontologies()

    # 2. Wait for Credo conformance VC, register self, populate catalog
    vc = wait_for_conformance_vc()
    if vc:
        node_did = vc.get("issuer", "")
        if node_did:
            register_self(node_did)
            populate_catalog(node_did)
        else:
            print("WARNING: conformance VC has no issuer — skipping registry/catalog", flush=True)
    else:
        print("WARNING: conformance VC not available — skipping registry/catalog", flush=True)

    print("Bootstrap complete.", flush=True)


if __name__ == "__main__":
    main()
