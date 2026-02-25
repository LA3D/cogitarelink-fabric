"""Unit tests for fabric/node/catalog.py — VoID→DCAT extraction helpers (D23)."""
import pytest

from fabric.node.catalog import (
    extract_dcat_from_void,
    build_catalog_insert,
    build_catalog_construct,
)


SAMPLE_VOID = """\
@prefix void: <http://rdfs.org/ns/void#> .
@prefix dct:  <http://purl.org/dc/terms/> .

<http://localhost:8080/.well-known/void>
    a void:Dataset ;
    dct:title "cogitarelink-fabric node" ;
    void:sparqlEndpoint <http://localhost:8080/sparql> ;
    void:vocabulary <http://www.w3.org/ns/sosa/> ;
    void:vocabulary <http://www.w3.org/ns/prov#> ;
    dct:conformsTo <https://w3id.org/cogitarelink/fabric#CoreProfile> ;
    void:subset [
        a void:Dataset ;
        dct:title "Observations" ;
        void:sparqlGraphEndpoint <http://localhost:8080/graph/observations> ;
        dct:conformsTo <https://w3id.org/cogitarelink/fabric#ObservationShape> ;
    ] ;
    void:subset [
        a void:Dataset ;
        dct:title "Entities" ;
        dct:description "Sensor descriptions." ;
        void:sparqlGraphEndpoint <http://localhost:8080/graph/entities> ;
        dct:conformsTo <https://w3id.org/cogitarelink/fabric#EntityShape> ;
    ] .
"""


class TestExtractDcatFromVoid:
    """extract_dcat_from_void parses void:subset blocks."""

    def test_returns_list(self):
        result = extract_dcat_from_void(SAMPLE_VOID, "http://localhost:8080")
        assert isinstance(result, list)

    def test_finds_two_datasets(self):
        result = extract_dcat_from_void(SAMPLE_VOID, "http://localhost:8080")
        assert len(result) == 2

    def test_first_dataset_title(self):
        result = extract_dcat_from_void(SAMPLE_VOID, "http://localhost:8080")
        titles = [d["title"] for d in result]
        assert "Observations" in titles

    def test_second_dataset_title(self):
        result = extract_dcat_from_void(SAMPLE_VOID, "http://localhost:8080")
        titles = [d["title"] for d in result]
        assert "Entities" in titles

    def test_graph_endpoint_extracted(self):
        result = extract_dcat_from_void(SAMPLE_VOID, "http://localhost:8080")
        obs = [d for d in result if d["title"] == "Observations"][0]
        assert obs["graph_endpoint"] == "http://localhost:8080/graph/observations"

    def test_vocabularies_inherited(self):
        result = extract_dcat_from_void(SAMPLE_VOID, "http://localhost:8080")
        obs = [d for d in result if d["title"] == "Observations"][0]
        assert "http://www.w3.org/ns/sosa/" in obs["vocabularies"]

    def test_empty_input(self):
        result = extract_dcat_from_void("", "http://localhost:8080")
        assert result == []


class TestBuildCatalogInsert:
    """build_catalog_insert generates SPARQL INSERT DATA for /graph/catalog."""

    def test_contains_dcat_dataset(self):
        datasets = [{"title": "Test", "graph_endpoint": "http://x/graph/test", "vocabularies": []}]
        sparql = build_catalog_insert("http://x", "did:webvh:abc:x", datasets)
        assert "dcat:Dataset" in sparql

    def test_contains_graph_catalog(self):
        datasets = [{"title": "Test", "graph_endpoint": "http://x/graph/test", "vocabularies": []}]
        sparql = build_catalog_insert("http://x", "did:webvh:abc:x", datasets)
        assert "/graph/catalog" in sparql

    def test_contains_title(self):
        datasets = [{"title": "My Dataset", "graph_endpoint": "http://x/graph/test", "vocabularies": []}]
        sparql = build_catalog_insert("http://x", "did:webvh:abc:x", datasets)
        assert "My Dataset" in sparql

    def test_contains_access_service(self):
        datasets = [{"title": "Test", "graph_endpoint": "http://x/graph/test", "vocabularies": []}]
        sparql = build_catalog_insert("http://x", "did:webvh:abc:x", datasets)
        assert "/sparql" in sparql

    def test_contains_publisher_did(self):
        datasets = [{"title": "Test", "graph_endpoint": "http://x/graph/test", "vocabularies": []}]
        sparql = build_catalog_insert("http://x", "did:webvh:abc:x", datasets)
        assert "did:webvh:abc:x" in sparql

    def test_contains_vocabulary(self):
        datasets = [{"title": "Test", "graph_endpoint": "http://x/graph/test",
                      "vocabularies": ["http://www.w3.org/ns/sosa/"]}]
        sparql = build_catalog_insert("http://x", "did:webvh:abc:x", datasets)
        assert "http://www.w3.org/ns/sosa/" in sparql

    def test_empty_datasets(self):
        sparql = build_catalog_insert("http://x", "did:webvh:abc:x", [])
        assert "INSERT DATA" in sparql


class TestBuildCatalogConstruct:
    """build_catalog_construct generates SPARQL CONSTRUCT for catalog."""

    def test_returns_construct(self):
        sparql = build_catalog_construct("http://localhost:8080")
        assert "CONSTRUCT" in sparql

    def test_queries_graph_catalog(self):
        sparql = build_catalog_construct("http://localhost:8080")
        assert "/graph/catalog" in sparql
