"""Unit tests for InstrumentShape + SensorEntityShape SHACL validation."""
import pytest
from pyshacl import validate as pyshacl_validate
from rdflib import Graph, Namespace

SH = Namespace("http://www.w3.org/ns/shacl#")
FABRIC = Namespace("https://w3id.org/cogitarelink/fabric#")
BASE = "https://bootstrap.cogitarelink.ai"


@pytest.fixture(scope="module")
def shapes_g():
    g = Graph()
    ttl = open("shapes/endpoint-sosa.ttl").read().replace("{base}", BASE)
    g.parse(data=ttl, format="turtle")
    return g


def _validate(data_ttl, shapes_g):
    data_g = Graph()
    data_g.parse(data=data_ttl, format="turtle")
    conforms, report_g, report_text = pyshacl_validate(
        data_graph=data_g, shacl_graph=shapes_g, advanced=True,
    )
    return conforms, report_g, report_text


VALID_INSTRUMENT = f"""\
@prefix sosa: <http://www.w3.org/ns/sosa/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix schema: <https://schema.org/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<{BASE}/entity/inst-1> a sosa:Platform ;
    rdfs:label "BioLogic SP-200"^^xsd:string ;
    schema:serialNumber "SP200-001"^^xsd:string ;
    sosa:hosts <{BASE}/entity/sensor-1> .

<{BASE}/entity/sensor-1> a sosa:Sensor ;
    rdfs:label "WE Current Sensor"^^xsd:string ;
    sosa:observes <{BASE}/entity/op-current> .
"""

MISSING_LABEL_INSTRUMENT = f"""\
@prefix sosa: <http://www.w3.org/ns/sosa/> .
@prefix schema: <https://schema.org/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<{BASE}/entity/inst-2> a sosa:Platform ;
    schema:serialNumber "SP200-002"^^xsd:string ;
    sosa:hosts <{BASE}/entity/sensor-2> .

<{BASE}/entity/sensor-2> a sosa:Sensor ;
    sosa:observes <{BASE}/entity/op-voltage> .
"""

MISSING_HOSTS_INSTRUMENT = f"""\
@prefix sosa: <http://www.w3.org/ns/sosa/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix schema: <https://schema.org/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<{BASE}/entity/inst-3> a sosa:Platform ;
    rdfs:label "Orphan Instrument"^^xsd:string ;
    schema:serialNumber "SP200-003"^^xsd:string .
"""

SENSOR_MISSING_OBSERVES = f"""\
@prefix sosa: <http://www.w3.org/ns/sosa/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<{BASE}/entity/sensor-bad> a sosa:Sensor ;
    rdfs:label "Broken Sensor"^^xsd:string .
"""


def test_valid_instrument_conforms(shapes_g):
    conforms, _, _ = _validate(VALID_INSTRUMENT, shapes_g)
    assert conforms is True


def test_missing_label_fails(shapes_g):
    conforms, report_g, _ = _validate(MISSING_LABEL_INSTRUMENT, shapes_g)
    assert conforms is False
    paths = [str(o) for s, p, o in report_g.triples((None, SH.resultPath, None))]
    assert any("label" in p for p in paths)


def test_missing_hosts_fails(shapes_g):
    conforms, report_g, _ = _validate(MISSING_HOSTS_INSTRUMENT, shapes_g)
    assert conforms is False
    paths = [str(o) for s, p, o in report_g.triples((None, SH.resultPath, None))]
    assert any("hosts" in p for p in paths)


def test_sensor_missing_observes_fails(shapes_g):
    conforms, report_g, _ = _validate(SENSOR_MISSING_OBSERVES, shapes_g)
    assert conforms is False
    paths = [str(o) for s, p, o in report_g.triples((None, SH.resultPath, None))]
    assert any("observes" in p for p in paths)


def test_instrument_shape_has_agent_instructions(shapes_g):
    hints = list(shapes_g.objects(FABRIC.InstrumentShape, SH.agentInstruction))
    assert len(hints) == 1
    assert "sosa:Platform" in str(hints[0])


def test_sensor_shape_has_agent_instructions(shapes_g):
    hints = list(shapes_g.objects(FABRIC.SensorEntityShape, SH.agentInstruction))
    assert len(hints) == 1
    assert "sosa:Sensor" in str(hints[0])


def test_instrument_property_agent_hints(shapes_g):
    """Property-level sh:agentInstruction hints exist on InstrumentShape properties."""
    prop_nodes = list(shapes_g.objects(FABRIC.InstrumentShape, SH.property))
    hints = []
    for pn in prop_nodes:
        h = shapes_g.value(pn, SH.agentInstruction)
        if h:
            hints.append(str(h))
    assert len(hints) >= 3  # label, serialNumber, hosts at minimum


def test_warning_severity_on_recommended(shapes_g):
    """Manufacturer and model have sh:Warning severity (not sh:Violation)."""
    prop_nodes = list(shapes_g.objects(FABRIC.InstrumentShape, SH.property))
    warning_paths = []
    for pn in prop_nodes:
        sev = shapes_g.value(pn, SH.severity)
        if sev and str(sev) == str(SH.Warning):
            path = shapes_g.value(pn, SH.path)
            if path:
                warning_paths.append(str(path))
    assert any("manufacturer" in p for p in warning_paths)
    assert any("model" in p for p in warning_paths)
