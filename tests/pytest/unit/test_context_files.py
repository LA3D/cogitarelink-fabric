"""Tests for WU-2: purpose-specific @context files (D22, Phase 2.5a)."""
import json
import pathlib
import pytest


CONTEXTS_DIR = pathlib.Path(__file__).parents[3] / "fabric" / "node" / "contexts"


def test_data_context_valid_json():
    ctx = json.loads((CONTEXTS_DIR / "data.jsonld").read_text())
    assert "@context" in ctx
    assert isinstance(ctx["@context"], dict)


def test_data_context_has_expected_prefixes():
    ctx = json.loads((CONTEXTS_DIR / "data.jsonld").read_text())
    prefixes = ctx["@context"]
    for ns in ["sosa", "ssn", "sio", "prov", "fabric", "time", "qudt", "xsd", "dct", "rdfs", "owl", "skos"]:
        assert ns in prefixes, f"Missing prefix {ns}"


def test_discovery_context_valid_json():
    ctx = json.loads((CONTEXTS_DIR / "discovery.jsonld").read_text())
    assert "@context" in ctx
    for ns in ["void", "sd", "dcat", "dct", "prof", "fabric", "rdfs", "foaf", "ldp"]:
        assert ns in ctx["@context"], f"Missing prefix {ns}"


def test_meta_context_valid_json():
    ctx = json.loads((CONTEXTS_DIR / "meta.jsonld").read_text())
    assert "@context" in ctx
    for ns in ["rdfs", "owl", "sh", "skos", "xsd", "vann", "dct"]:
        assert ns in ctx["@context"], f"Missing prefix {ns}"


def test_aggregate_context_references_all_three():
    ctx = json.loads((CONTEXTS_DIR / "fabric-context.jsonld").read_text())
    assert "@context" in ctx
    refs = ctx["@context"]
    assert isinstance(refs, list)
    assert len(refs) == 3
    assert any("data" in r for r in refs)
    assert any("discovery" in r for r in refs)
    assert any("meta" in r for r in refs)


def test_all_namespace_uris_end_with_separator():
    """Namespace URIs must end with / or # for prefix compaction to work."""
    for fname in ["data.jsonld", "discovery.jsonld", "meta.jsonld"]:
        ctx = json.loads((CONTEXTS_DIR / fname).read_text())
        for prefix, uri in ctx["@context"].items():
            assert uri.endswith("/") or uri.endswith("#"), (
                f"{fname}: {prefix} → {uri} must end with / or #"
            )


def test_context_route_serves_data():
    from fabric.node.main import well_known_context
    import asyncio
    resp = asyncio.run(well_known_context("data.jsonld"))
    assert resp.status_code == 200
    body = json.loads(resp.body)
    assert "@context" in body


def test_context_route_rejects_invalid_name():
    from fabric.node.main import well_known_context
    from fastapi import HTTPException
    import asyncio
    with pytest.raises(HTTPException):
        asyncio.run(well_known_context("../../etc/passwd"))


def test_context_route_404_for_missing():
    from fabric.node.main import well_known_context
    from fastapi import HTTPException
    import asyncio
    with pytest.raises(HTTPException):
        asyncio.run(well_known_context("nonexistent.jsonld"))
