"""Unit tests for TBox lift experiment harness helpers."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[3]))

from experiments.fabric_navigation.run_experiment import _strip_tbox_paths
from experiments.fabric_navigation.run_experiment import _build_insert


ROUTING_PLAN_WITH_PATHS = """\
Endpoint: http://localhost:8080
SPARQL: http://localhost:8080/sparql
Profile: https://w3id.org/cogitarelink/fabric#CoreProfile

Local ontology cache (no external dereferencing needed):
  prov: <http://www.w3.org/ns/prov#> -> /ontology/prov
  sio: <http://semanticscience.org/resource/> -> /ontology/sio
  sosa: <http://www.w3.org/ns/sosa/> -> /ontology/sosa
  time: <http://www.w3.org/2006/time#> -> /ontology/time
  xsd: <http://www.w3.org/2001/XMLSchema#>
"""

def test_strip_removes_ontology_paths():
    result = _strip_tbox_paths(ROUTING_PLAN_WITH_PATHS)
    assert "-> /ontology/" not in result

def test_strip_preserves_namespace_iris():
    result = _strip_tbox_paths(ROUTING_PLAN_WITH_PATHS)
    assert "<http://www.w3.org/ns/sosa/>" in result
    assert "<http://www.w3.org/ns/prov#>" in result

def test_strip_idempotent_on_plan_without_paths():
    plan_no_paths = "  sosa: <http://www.w3.org/ns/sosa/>\n"
    assert _strip_tbox_paths(plan_no_paths) == plan_no_paths


def test_build_insert_baseline_unchanged():
    obs = {
        "subject": "http://localhost:8080/entity/obs-1",
        "sosa:madeBySensor": "http://localhost:8080/entity/sensor-1",
        "sosa:hasSimpleResult": "23.5",
        "sosa:resultTime": "2026-02-23T12:00:00Z",
        "graph": "http://localhost:8080/graph/observations",
    }
    q = _build_insert(obs)
    assert "sosa:madeBySensor" in q
    assert "23.5" in q
    assert "sosa:usedProcedure" not in q

def test_build_insert_includes_used_procedure():
    obs = {
        "subject": "http://localhost:8080/entity/obs-2",
        "sosa:madeBySensor": "http://localhost:8080/entity/sensor-1",
        "sosa:hasSimpleResult": "21.0",
        "sosa:resultTime": "2026-02-23T09:00:00Z",
        "sosa:usedProcedure": "http://localhost:8080/entity/procedure-cv-scan",
        "graph": "http://localhost:8080/graph/observations",
    }
    q = _build_insert(obs)
    assert "sosa:usedProcedure" in q
    assert "procedure-cv-scan" in q

def test_build_insert_includes_feature_of_interest():
    obs = {
        "subject": "http://localhost:8080/entity/obs-3",
        "sosa:madeBySensor": "http://localhost:8080/entity/sensor-1",
        "sosa:hasSimpleResult": "19.5",
        "sosa:resultTime": "2026-02-23T10:00:00Z",
        "sosa:hasFeatureOfInterest": "http://localhost:8080/entity/feature-sample-alpha",
        "graph": "http://localhost:8080/graph/observations",
    }
    q = _build_insert(obs)
    assert "sosa:hasFeatureOfInterest" in q
    assert "feature-sample-alpha" in q

def test_build_insert_includes_phenomenon_time():
    obs = {
        "subject": "http://localhost:8080/entity/obs-4",
        "sosa:madeBySensor": "http://localhost:8080/entity/sensor-1",
        "sosa:hasSimpleResult": "24.7",
        "sosa:resultTime": "2026-02-23T12:00:00Z",
        "sosa:phenomenonTime": "2026-02-23T11:30:00Z",
        "graph": "http://localhost:8080/graph/observations",
    }
    q = _build_insert(obs)
    assert "sosa:phenomenonTime" in q
    assert "11:30:00" in q


def test_build_insert_sio_measurement_chain():
    """SIO has-attribute -> MeasuredValue -> has-value chain."""
    obs = {
        "subject": "http://localhost:8080/entity/obs-sio-1",
        "sosa:madeBySensor": "http://localhost:8080/entity/sensor-1",
        "sosa:resultTime": "2026-02-23T09:00:00Z",
        "sio:has-attribute": "http://localhost:8080/entity/mv-1",
        "sio:mv-type": "http://semanticscience.org/resource/MeasuredValue",
        "sio:has-value": "21.3",
        "graph": "http://localhost:8080/graph/observations",
    }
    q = _build_insert(obs)
    assert "sio:has-attribute" in q
    assert "<http://localhost:8080/entity/mv-1>" in q
    assert "sio:MeasuredValue" in q
    assert 'sio:has-value "21.3"' in q


def test_build_insert_sio_unit():
    """SIO measurement with has-unit and rdfs:label on unit node."""
    obs = {
        "subject": "http://localhost:8080/entity/obs-sio-2",
        "sosa:madeBySensor": "http://localhost:8080/entity/sensor-1",
        "sosa:resultTime": "2026-02-23T10:00:00Z",
        "sio:has-attribute": "http://localhost:8080/entity/mv-2",
        "sio:mv-type": "http://semanticscience.org/resource/MeasuredValue",
        "sio:has-value": "42.7",
        "sio:has-unit": "http://localhost:8080/entity/unit-millimol",
        "sio:unit-label": "MilliMOL",
        "graph": "http://localhost:8080/graph/observations",
    }
    q = _build_insert(obs)
    assert "sio:has-unit" in q
    assert "unit-millimol" in q
    assert 'rdfs:label "MilliMOL"' in q


def test_build_insert_sio_is_about():
    """SIO is-about linking to ChemicalEntity with rdfs:label."""
    obs = {
        "subject": "http://localhost:8080/entity/obs-sio-3",
        "sosa:madeBySensor": "http://localhost:8080/entity/sensor-1",
        "sosa:hasSimpleResult": "18.9",
        "sosa:resultTime": "2026-02-23T11:00:00Z",
        "sio:is-about": "http://localhost:8080/entity/chem-kcl",
        "sio:chem-type": "http://semanticscience.org/resource/ChemicalEntity",
        "sio:chem-label": "potassium chloride",
        "graph": "http://localhost:8080/graph/observations",
    }
    q = _build_insert(obs)
    assert "sio:is-about" in q
    assert "chem-kcl" in q
    assert "sio:ChemicalEntity" in q
    assert 'rdfs:label "potassium chloride"' in q
