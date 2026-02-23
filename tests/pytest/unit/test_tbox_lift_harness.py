"""Unit tests for TBox lift experiment harness helpers."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[3]))

from experiments.fabric_navigation.run_experiment import _strip_tbox_paths


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
