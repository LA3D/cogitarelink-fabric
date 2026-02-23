"""Test CoreProfile declares all L2 TBox ontologies."""
from pathlib import Path
from rdflib import Graph, Namespace

PROF = Namespace("http://www.w3.org/ns/dx/prof/")
ROLE = Namespace("http://www.w3.org/ns/dx/prof/role/")

PROFILE_PATH = Path(__file__).parents[3] / "ontology" / "fabric-core-profile.ttl"

EXPECTED_ARTIFACTS = {
    "http://www.w3.org/ns/sosa/",
    "http://www.w3.org/2006/time#",
    "http://www.w3.org/ns/prov#",
    "http://semanticscience.org/resource/",
}


def test_core_profile_declares_all_tbox_ontologies():
    g = Graph()
    g.parse(str(PROFILE_PATH), format="turtle")
    artifacts = set()
    for rd in g.subjects(PROF.hasRole, ROLE.schema):
        for art in g.objects(rd, PROF.hasArtifact):
            artifacts.add(str(art))
    for expected in EXPECTED_ARTIFACTS:
        assert expected in artifacts, f"CoreProfile missing prof:hasArtifact <{expected}>"
