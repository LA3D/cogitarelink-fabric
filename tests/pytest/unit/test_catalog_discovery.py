"""RED tests for _parse_catalog + ExternalService in agents/fabric_discovery.py (D23/D29)."""
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))

from agents.fabric_discovery import (
    _parse_catalog,
    ExternalService,
    FabricEndpoint,
    ShapeSummary,
    ExampleSummary,
)


SAMPLE_CATALOG = '''\
@prefix dct:    <http://purl.org/dc/terms/> .
@prefix dcat:   <http://www.w3.org/ns/dcat#> .
@prefix void:   <http://rdfs.org/ns/void#> .
@prefix fabric: <https://w3id.org/cogitarelink/fabric#> .
@prefix spex:   <https://purl.expasy.org/sparql-examples/ontology#> .
@prefix rdfs:   <http://www.w3.org/2000/01/rdf-schema#> .

<http://localhost:8080/external/qlever-pubchem> a dcat:DataService ;
    dct:title "QLever PubChem SPARQL Endpoint" ;
    dct:description "PubChem RDF via QLever." ;
    dcat:endpointURL <https://qlever.cs.uni-freiburg.de/api/pubchem> ;
    void:vocabulary <http://rdf.ncbi.nlm.nih.gov/pubchem/vocabulary> ,
                    <http://semanticscience.org/resource/> ;
    fabric:vouchedBy <did:webvh:abc123:localhost%253A8080> ;
    spex:SparqlExample [
        a spex:SparqlSelectExecutable ;
        rdfs:label "Lookup molecular formula by CID" ;
        spex:query """PREFIX sio: <http://semanticscience.org/resource/>
SELECT ?formula WHERE {
  <http://rdf.ncbi.nlm.nih.gov/pubchem/compound/CID2244> sio:SIO_000008 ?attr .
  ?attr a sio:CHEMINF_000335 ; sio:SIO_000300 ?formula .
} LIMIT 5"""
    ] .

<http://localhost:8080/external/qlever-wikidata> a dcat:DataService ;
    dct:title "QLever Wikidata SPARQL Endpoint" ;
    dct:description "Wikidata via QLever." ;
    dcat:endpointURL <https://qlever.cs.uni-freiburg.de/api/wikidata> ;
    void:vocabulary <http://www.wikidata.org/ontology#> ,
                    <http://schema.org/> ;
    fabric:vouchedBy <did:webvh:abc123:localhost%253A8080> ;
    spex:SparqlExample [
        a spex:SparqlSelectExecutable ;
        rdfs:label "Find manufacturer of instrument" ;
        spex:query """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
SELECT ?item WHERE { ?item wdt:P31 ?type } LIMIT 10"""
    ] ;
    spex:SparqlExample [
        a spex:SparqlSelectExecutable ;
        rdfs:label "Lookup instrument by QID" ;
        spex:query """PREFIX wd: <http://www.wikidata.org/entity/>
SELECT ?label WHERE { wd:Q185738 rdfs:label ?label } LIMIT 5"""
    ] .
'''

# Mixed catalog: contains both dcat:Dataset and dcat:DataService
MIXED_CATALOG = '''\
@prefix dct:    <http://purl.org/dc/terms/> .
@prefix dcat:   <http://www.w3.org/ns/dcat#> .
@prefix void:   <http://rdfs.org/ns/void#> .
@prefix fabric: <https://w3id.org/cogitarelink/fabric#> .
@prefix spex:   <https://purl.expasy.org/sparql-examples/ontology#> .
@prefix rdfs:   <http://www.w3.org/2000/01/rdf-schema#> .

<http://localhost:8080/catalog/obs> a dcat:Dataset ;
    dct:title "Observations" ;
    dct:description "Local observation data." .

<http://localhost:8080/external/qlever-pubchem> a dcat:DataService ;
    dct:title "QLever PubChem" ;
    dct:description "PubChem RDF via QLever." ;
    dcat:endpointURL <https://qlever.cs.uni-freiburg.de/api/pubchem> ;
    void:vocabulary <http://semanticscience.org/resource/> .
'''


class TestParseCatalogBasic:
    """_parse_catalog returns list of ExternalService from catalog Turtle."""

    def test_finds_two_data_services(self):
        result = _parse_catalog(SAMPLE_CATALOG)
        assert len(result) == 2

    def test_returns_external_service_instances(self):
        result = _parse_catalog(SAMPLE_CATALOG)
        assert all(isinstance(s, ExternalService) for s in result)

    def test_empty_catalog_returns_empty_list(self):
        result = _parse_catalog("")
        assert result == []


class TestParseCatalogSkipsDataset:
    """_parse_catalog only parses dcat:DataService, not dcat:Dataset."""

    def test_mixed_catalog_returns_one_service(self):
        result = _parse_catalog(MIXED_CATALOG)
        assert len(result) == 1

    def test_mixed_catalog_service_is_pubchem(self):
        result = _parse_catalog(MIXED_CATALOG)
        assert result[0].title == "QLever PubChem"


class TestExternalServiceFields:
    """ExternalService dataclass has correct fields from catalog Turtle."""

    def test_title_extracted(self):
        result = _parse_catalog(SAMPLE_CATALOG)
        titles = {s.title for s in result}
        assert "QLever PubChem SPARQL Endpoint" in titles
        assert "QLever Wikidata SPARQL Endpoint" in titles

    def test_endpoint_url_extracted(self):
        result = _parse_catalog(SAMPLE_CATALOG)
        urls = {s.endpoint_url for s in result}
        assert "https://qlever.cs.uni-freiburg.de/api/pubchem" in urls
        assert "https://qlever.cs.uni-freiburg.de/api/wikidata" in urls

    def test_description_extracted(self):
        result = _parse_catalog(SAMPLE_CATALOG)
        pubchem = [s for s in result if "PubChem" in s.title][0]
        assert pubchem.description == "PubChem RDF via QLever."

    def test_vocabularies_extracted(self):
        result = _parse_catalog(SAMPLE_CATALOG)
        pubchem = [s for s in result if "PubChem" in s.title][0]
        assert "http://semanticscience.org/resource/" in pubchem.vocabularies
        assert "http://rdf.ncbi.nlm.nih.gov/pubchem/vocabulary" in pubchem.vocabularies

    def test_wikidata_vocabularies(self):
        result = _parse_catalog(SAMPLE_CATALOG)
        wd = [s for s in result if "Wikidata" in s.title][0]
        assert "http://www.wikidata.org/ontology#" in wd.vocabularies
        assert "http://schema.org/" in wd.vocabularies


class TestExternalServiceExamples:
    """spex:SparqlExample with spex:query are extracted as example queries."""

    def test_pubchem_has_one_example(self):
        result = _parse_catalog(SAMPLE_CATALOG)
        pubchem = [s for s in result if "PubChem" in s.title][0]
        assert len(pubchem.examples) == 1

    def test_wikidata_has_two_examples(self):
        result = _parse_catalog(SAMPLE_CATALOG)
        wd = [s for s in result if "Wikidata" in s.title][0]
        assert len(wd.examples) == 2

    def test_example_has_label_and_query(self):
        result = _parse_catalog(SAMPLE_CATALOG)
        pubchem = [s for s in result if "PubChem" in s.title][0]
        ex = pubchem.examples[0]
        assert ex["label"] == "Lookup molecular formula by CID"
        assert "SELECT ?formula" in ex["query"]

    def test_example_query_contains_sparql(self):
        result = _parse_catalog(SAMPLE_CATALOG)
        wd = [s for s in result if "Wikidata" in s.title][0]
        queries = [e["query"] for e in wd.examples]
        assert any("wdt:P31" in q for q in queries)

    def test_no_examples_when_none_declared(self):
        result = _parse_catalog(MIXED_CATALOG)
        pubchem = result[0]
        assert pubchem.examples == []


# --- routing_plan integration -------------------------------------------------

def _make_endpoint(**overrides) -> FabricEndpoint:
    defaults = dict(
        base="http://x",
        sparql_url="http://x/sparql",
        void_ttl="",
        profile_ttl="",
        shapes_ttl="",
        examples_ttl="",
        vocabularies=["http://www.w3.org/ns/sosa/"],
        conforms_to="https://w3id.org/cogitarelink/fabric#CoreProfile",
        uri_space="http://x/entity/",
        prefix_declarations={"sosa": "http://www.w3.org/ns/sosa/"},
        named_graphs=[{"title": "Observations", "graph_uri": "http://x/graph/observations"}],
        shapes=[ShapeSummary(
            name="ObservationShape",
            target_class="sosa:Observation",
            agent_instruction="hint",
            properties=["sosa:madeBySensor"],
        )],
        examples=[ExampleSummary(
            label="List observations",
            comment="Returns observations.",
            sparql="SELECT ?obs WHERE { ?obs a sosa:Observation }",
            target="http://x/sparql",
        )],
    )
    defaults.update(overrides)
    return FabricEndpoint(**defaults)


class TestRoutingPlanExternalServices:
    """routing_plan includes External SPARQL Services section when present."""

    def test_routing_plan_includes_external_section(self):
        services = [
            ExternalService(
                title="QLever PubChem",
                endpoint_url="https://qlever.cs.uni-freiburg.de/api/pubchem",
                description="PubChem RDF via QLever.",
                vocabularies=["http://semanticscience.org/resource/"],
                examples=[{"label": "Lookup formula", "query": "SELECT ?f WHERE { ?x ?p ?f }"}],
            ),
        ]
        ep = _make_endpoint(external_services=services)
        plan = ep.routing_plan
        assert "External SPARQL Services" in plan

    def test_routing_plan_shows_service_title(self):
        services = [
            ExternalService(
                title="QLever PubChem",
                endpoint_url="https://qlever.cs.uni-freiburg.de/api/pubchem",
                description="PubChem via QLever.",
                vocabularies=[],
                examples=[],
            ),
        ]
        ep = _make_endpoint(external_services=services)
        plan = ep.routing_plan
        assert "QLever PubChem" in plan

    def test_routing_plan_shows_endpoint_url(self):
        services = [
            ExternalService(
                title="QLever PubChem",
                endpoint_url="https://qlever.cs.uni-freiburg.de/api/pubchem",
                description="PubChem via QLever.",
                vocabularies=[],
                examples=[],
            ),
        ]
        ep = _make_endpoint(external_services=services)
        plan = ep.routing_plan
        assert "qlever.cs.uni-freiburg.de/api/pubchem" in plan

    def test_routing_plan_shows_example_query(self):
        services = [
            ExternalService(
                title="QLever PubChem",
                endpoint_url="https://qlever.cs.uni-freiburg.de/api/pubchem",
                description="PubChem via QLever.",
                vocabularies=[],
                examples=[{"label": "Lookup formula", "query": "SELECT ?f WHERE { ?x ?p ?f }"}],
            ),
        ]
        ep = _make_endpoint(external_services=services)
        plan = ep.routing_plan
        assert "SELECT ?f WHERE" in plan

    def test_routing_plan_omits_section_when_no_services(self):
        ep = _make_endpoint()
        plan = ep.routing_plan
        assert "External SPARQL Services" not in plan

    def test_routing_plan_omits_section_when_empty_list(self):
        ep = _make_endpoint(external_services=[])
        plan = ep.routing_plan
        assert "External SPARQL Services" not in plan
