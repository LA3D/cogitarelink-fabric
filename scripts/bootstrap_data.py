#!/usr/bin/env python3
"""Bootstrap fabric node: load SOSA TBox + mock observation into Oxigraph.

Runs at container startup (optional — data persists across restarts in volume).
Idempotent: INSERT DATA is safe to re-run (adds duplicates only for blank nodes,
but named URIs are deduplicated by the triplestore).

Usage:
    python scripts/bootstrap_data.py [--endpoint http://localhost:7878]
"""
import argparse
import pathlib
import sys
import urllib.request
import urllib.parse

ROOT = pathlib.Path(__file__).parent.parent

SOSA_TBOX_URL = "http://www.w3.org/ns/sosa/"
SOSA_GRAPH = "http://localhost:8080/graph/tbox/sosa"
OBS_GRAPH = "http://localhost:8080/graph/observations"


def sparql_update(endpoint: str, update: str) -> int:
    data = urllib.parse.urlencode({"update": update}).encode()
    req = urllib.request.Request(
        f"{endpoint}/update",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req) as r:
        return r.status


def load_sosa_tbox(endpoint: str) -> None:
    """Load SOSA TBox into named graph /graph/tbox/sosa."""
    print(f"Loading SOSA TBox into <{SOSA_GRAPH}>...", flush=True)
    # Use LOAD to fetch the SOSA ontology directly from W3C
    update = f"LOAD <{SOSA_TBOX_URL}> INTO GRAPH <{SOSA_GRAPH}>"
    status = sparql_update(endpoint, update)
    print(f"  SOSA TBox load: HTTP {status}", flush=True)


def load_mock_observation(endpoint: str) -> None:
    """Insert a mock SOSA Observation into /graph/observations."""
    print(f"Inserting mock observation into <{OBS_GRAPH}>...", flush=True)
    update = f"""\
PREFIX sosa: <http://www.w3.org/ns/sosa/>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
INSERT DATA {{
  GRAPH <{OBS_GRAPH}> {{
    <http://localhost:8080/entity/bootstrap-obs-001>
        a sosa:Observation ;
        sosa:hasSimpleResult "0.42"^^xsd:decimal ;
        sosa:resultTime "2026-02-22T00:00:00Z"^^xsd:dateTime .
  }}
}}"""
    status = sparql_update(endpoint, update)
    print(f"  Mock observation insert: HTTP {status}", flush=True)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--endpoint", default="http://localhost:7878",
                   help="Oxigraph HTTP endpoint (default: http://localhost:7878)")
    p.add_argument("--skip-tbox", action="store_true",
                   help="Skip SOSA TBox load (useful when W3C is unreachable)")
    args = p.parse_args()

    print(f"Bootstrap endpoint: {args.endpoint}", flush=True)
    if not args.skip_tbox:
        try:
            load_sosa_tbox(args.endpoint)
        except Exception as e:
            print(f"  WARNING: SOSA TBox load failed ({e}), continuing...", flush=True)
    load_mock_observation(args.endpoint)
    print("Bootstrap complete.", flush=True)


if __name__ == "__main__":
    main()
