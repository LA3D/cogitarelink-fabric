"""Tests for GET /ontology/{vocab} dynamic route (WU-1, D22)."""
import pathlib
import pytest
from fastapi import HTTPException


def test_validate_vocab_rejects_sparql_injection_chars(tmp_path):
    """Vocab names with special characters are rejected before filesystem check."""
    import fabric.node.main as m
    orig = m.ONTOLOGY_DIR
    m.ONTOLOGY_DIR = tmp_path
    try:
        for bad in ["SOSA", "sosa>{}}", "sosa spaces", "123start", "../up"]:
            with pytest.raises(HTTPException) as exc_info:
                m._validate_vocab(bad)
            assert exc_info.value.status_code == 400, f"Expected 400 for {bad!r}"
    finally:
        m.ONTOLOGY_DIR = orig


def test_ontology_construct_query():
    """CONSTRUCT query targets the correct named graph."""
    from fabric.node.main import _ontology_construct
    q = _ontology_construct("http://localhost:8080", "sosa")
    assert "CONSTRUCT" in q
    assert "<http://localhost:8080/ontology/sosa>" in q
    assert "GRAPH" in q


def test_ontology_construct_query_different_vocab():
    from fabric.node.main import _ontology_construct
    q = _ontology_construct("https://bootstrap.cogitarelink.ai", "sio")
    assert "<https://bootstrap.cogitarelink.ai/ontology/sio>" in q


def test_validate_vocab_rejects_path_traversal(tmp_path):
    """Path traversal attempts must be caught."""
    (tmp_path / "legit.ttl").write_text("# ok")
    import fabric.node.main as m
    orig = m.ONTOLOGY_DIR
    m.ONTOLOGY_DIR = tmp_path
    try:
        with pytest.raises(HTTPException) as exc_info:
            m._validate_vocab("../../etc/passwd")
        assert exc_info.value.status_code == 400
    finally:
        m.ONTOLOGY_DIR = orig


def test_validate_vocab_rejects_nonexistent(tmp_path):
    """Missing ontology file returns 404."""
    import fabric.node.main as m
    orig = m.ONTOLOGY_DIR
    m.ONTOLOGY_DIR = tmp_path
    try:
        with pytest.raises(HTTPException) as exc_info:
            m._validate_vocab("nonexistent")
        assert exc_info.value.status_code == 404
    finally:
        m.ONTOLOGY_DIR = orig


def test_validate_vocab_rejects_profile_files(tmp_path):
    """Profile files (fabric-core-profile.ttl) are excluded."""
    (tmp_path / "fabric-core-profile.ttl").write_text("# profile")
    import fabric.node.main as m
    orig = m.ONTOLOGY_DIR
    m.ONTOLOGY_DIR = tmp_path
    try:
        with pytest.raises(HTTPException) as exc_info:
            m._validate_vocab("fabric-core-profile")
        assert exc_info.value.status_code == 404
    finally:
        m.ONTOLOGY_DIR = orig


def test_validate_vocab_accepts_existing_file(tmp_path):
    """Valid ontology file passes validation."""
    (tmp_path / "sosa.ttl").write_text("# sosa ontology stub")
    import fabric.node.main as m
    orig = m.ONTOLOGY_DIR
    m.ONTOLOGY_DIR = tmp_path
    try:
        result = m._validate_vocab("sosa")
        assert result.name == "sosa.ttl"
    finally:
        m.ONTOLOGY_DIR = orig


def test_all_cached_ontologies_loadable():
    """Every non-profile .ttl in ontology/ would be served by /ontology/{stem}."""
    ontology_dir = pathlib.Path(__file__).parents[3] / "ontology"
    for f in ontology_dir.glob("*.ttl"):
        if f.name.endswith("-profile.ttl"):
            continue
        # The stem should be a valid vocab name — no weird characters
        assert f.stem.isascii(), f"{f.name} has non-ASCII stem"
        assert "/" not in f.stem, f"{f.name} stem contains slash"
