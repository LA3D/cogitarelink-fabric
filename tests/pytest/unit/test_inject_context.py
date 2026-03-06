"""Tests for WU-3: _inject_context() helper (D22, Phase 2.5a)."""
import json
import pytest


def test_inject_bare_array():
    """Oxigraph bare JSON array gets wrapped with @context + @graph."""
    from fabric.node.main import _inject_context
    bare = json.dumps([{"@id": "http://example.org/s", "http://example.org/p": [{"@value": "v"}]}]).encode()
    result = json.loads(_inject_context(bare, "data"))
    assert "@context" in result
    assert "@graph" in result
    assert isinstance(result["@graph"], list)
    assert len(result["@graph"]) == 1


def test_inject_dict_no_context():
    """Dict without @context gets @context added."""
    from fabric.node.main import _inject_context
    doc = json.dumps({"@id": "http://example.org/s"}).encode()
    result = json.loads(_inject_context(doc, "meta"))
    assert "@context" in result
    assert "meta" in result["@context"]


def test_inject_dict_existing_context():
    """Dict with existing @context gets our URL prepended."""
    from fabric.node.main import _inject_context
    doc = json.dumps({"@context": "http://existing.org/ctx", "@id": "http://example.org/s"}).encode()
    result = json.loads(_inject_context(doc, "discovery"))
    assert isinstance(result["@context"], list)
    assert len(result["@context"]) == 2
    assert "discovery" in result["@context"][0]


def test_inject_dict_existing_array_context():
    """Dict with existing array @context gets our URL prepended."""
    from fabric.node.main import _inject_context
    doc = json.dumps({"@context": ["http://a.org", "http://b.org"], "@id": "x"}).encode()
    result = json.loads(_inject_context(doc, "data"))
    assert isinstance(result["@context"], list)
    assert len(result["@context"]) == 3
    assert "data" in result["@context"][0]


def test_inject_context_types():
    """Each context type maps to a valid URL."""
    from fabric.node.main import _CONTEXT_MAP
    assert "data" in _CONTEXT_MAP
    assert "discovery" in _CONTEXT_MAP
    assert "meta" in _CONTEXT_MAP
    for url in _CONTEXT_MAP.values():
        assert "/.well-known/context/" in url
        assert url.endswith(".jsonld")


def test_inject_empty_array():
    """Empty array still gets wrapped."""
    from fabric.node.main import _inject_context
    result = json.loads(_inject_context(b"[]", "data"))
    assert "@context" in result
    assert result["@graph"] == []
