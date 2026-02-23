"""Test bootstrap convention auto-loading."""
from pathlib import Path
from unittest.mock import patch
import importlib


def test_bootstrap_loads_all_ttl_files(tmp_path):
    """Bootstrap should load every *.ttl in ONTOLOGY_DIR except *-profile.ttl."""
    (tmp_path / "sosa.ttl").write_text("@prefix sosa: <http://www.w3.org/ns/sosa/> .\n")
    (tmp_path / "prov.ttl").write_text("@prefix prov: <http://www.w3.org/ns/prov#> .\n")
    (tmp_path / "fabric-core-profile.ttl").write_text("@prefix prof: <http://www.w3.org/ns/dx/prof/> .\n")

    loaded = []

    def fake_put(graph_uri, ttl, retries=2):
        loaded.append(graph_uri)

    with patch.dict("os.environ", {
        "ONTOLOGY_DIR": str(tmp_path),
        "NODE_BASE": "http://test:8080",
        "OXIGRAPH_URL": "http://fake:7878",
    }):
        import fabric.node.bootstrap as mod
        importlib.reload(mod)
        mod.put_graph = fake_put
        mod.main()

    assert "http://test:8080/ontology/sosa" in loaded
    assert "http://test:8080/ontology/prov" in loaded
    assert not any("profile" in g for g in loaded)


def test_bootstrap_skips_profile_files(tmp_path):
    """Files matching *-profile.ttl must not be loaded as named graphs."""
    (tmp_path / "fabric-core-profile.ttl").write_text("@prefix x: <http://x/> .\n")
    (tmp_path / "another-profile.ttl").write_text("@prefix y: <http://y/> .\n")

    loaded = []

    def fake_put(graph_uri, ttl, retries=2):
        loaded.append(graph_uri)

    with patch.dict("os.environ", {
        "ONTOLOGY_DIR": str(tmp_path),
        "NODE_BASE": "http://test:8080",
        "OXIGRAPH_URL": "http://fake:7878",
    }):
        import fabric.node.bootstrap as mod
        importlib.reload(mod)
        mod.put_graph = fake_put
        mod.main()

    assert len(loaded) == 0


def test_bootstrap_alphabetical_order(tmp_path):
    """Ontologies must load in alphabetical order for deterministic startup."""
    for name in ["zeta.ttl", "alpha.ttl", "mid.ttl"]:
        (tmp_path / name).write_text(f"@prefix x: <http://x/{name}/> .\n")

    loaded = []

    def fake_put(graph_uri, ttl, retries=2):
        loaded.append(graph_uri)

    with patch.dict("os.environ", {
        "ONTOLOGY_DIR": str(tmp_path),
        "NODE_BASE": "http://test:8080",
        "OXIGRAPH_URL": "http://fake:7878",
    }):
        import fabric.node.bootstrap as mod
        importlib.reload(mod)
        mod.put_graph = fake_put
        mod.main()

    stems = [g.rsplit("/", 1)[-1] for g in loaded]
    assert stems == ["alpha", "mid", "zeta"]
