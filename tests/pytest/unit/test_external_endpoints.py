"""Unit tests for D29 external endpoint attestation helpers."""
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parents[3] / "fabric" / "node"))

from external_endpoints import load_external_endpoints_ttl

BASE = "http://localhost:8080"
DID = "did:webvh:abc123:localhost%253A8080"


class TestLoadExternalEndpointsTtl:
    def test_substitutes_base(self):
        ttl = load_external_endpoints_ttl(BASE, DID)
        assert BASE in ttl
        assert "{base}" not in ttl

    def test_substitutes_node_did(self):
        ttl = load_external_endpoints_ttl(BASE, DID)
        assert DID in ttl
        assert "{node_did}" not in ttl

    def test_all_three_endpoints_present(self):
        ttl = load_external_endpoints_ttl(BASE, DID)
        assert "qlever-pubchem" in ttl
        assert "qlever-wikidata" in ttl
        assert "qlever-osm" in ttl

    def test_endpoint_urls_present(self):
        ttl = load_external_endpoints_ttl(BASE, DID)
        assert "qlever.cs.uni-freiburg.de/api/pubchem" in ttl
        assert "qlever.cs.uni-freiburg.de/api/wikidata" in ttl
        assert "qlever.cs.uni-freiburg.de/api/osm-planet" in ttl

    def test_vouched_by_present(self):
        ttl = load_external_endpoints_ttl(BASE, DID)
        assert "vouchedBy" in ttl

    def test_dcat_data_service_type(self):
        ttl = load_external_endpoints_ttl(BASE, DID)
        assert "dcat:DataService" in ttl

    def test_sparql_examples_present(self):
        ttl = load_external_endpoints_ttl(BASE, DID)
        assert ttl.count("spex:SparqlExample") >= 3

    def test_void_vocabulary_present(self):
        ttl = load_external_endpoints_ttl(BASE, DID)
        assert "void:vocabulary" in ttl

    def test_valid_turtle(self):
        from rdflib import Graph
        ttl = load_external_endpoints_ttl(BASE, DID)
        g = Graph()
        g.parse(data=ttl, format="turtle")
        assert len(g) > 0

    def test_rdflib_finds_data_service_type(self):
        from rdflib import Graph, Namespace
        from rdflib.namespace import RDF
        DCAT = Namespace("http://www.w3.org/ns/dcat#")
        ttl = load_external_endpoints_ttl(BASE, DID)
        g = Graph()
        g.parse(data=ttl, format="turtle")
        services = list(g.subjects(RDF.type, DCAT.DataService))
        assert len(services) == 3

    def test_rdflib_finds_vouched_by(self):
        from rdflib import Graph, Namespace, URIRef
        FABRIC = Namespace("https://w3id.org/cogitarelink/fabric#")
        ttl = load_external_endpoints_ttl(BASE, DID)
        g = Graph()
        g.parse(data=ttl, format="turtle")
        vouchers = list(g.objects(predicate=FABRIC.vouchedBy))
        assert len(vouchers) == 3
        assert all(str(v) == DID for v in vouchers)

    def test_rdflib_finds_endpoint_urls(self):
        from rdflib import Graph, Namespace, URIRef
        DCAT = Namespace("http://www.w3.org/ns/dcat#")
        ttl = load_external_endpoints_ttl(BASE, DID)
        g = Graph()
        g.parse(data=ttl, format="turtle")
        urls = {str(o) for o in g.objects(predicate=DCAT.endpointURL)}
        assert "https://qlever.cs.uni-freiburg.de/api/pubchem" in urls
        assert "https://qlever.cs.uni-freiburg.de/api/wikidata" in urls
        assert "https://qlever.cs.uni-freiburg.de/api/osm-planet" in urls
