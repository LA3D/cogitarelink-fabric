"""Unit tests for fabric/node/registry.py — registry + agent SPARQL helpers (D12, D13, D14)."""
import pytest

# Task 1.1: RED — these imports will fail until registry.py exists
from fabric.node.registry import (
    build_registry_insert,
    build_registry_construct,
    build_registry_entry_construct,
    build_agent_insert,
    build_agents_list_construct,
    build_agent_construct,
    check_void_conformance,
    VALID_AGENT_ROLES,
    FABRIC_NS,
)


class TestRegistryInsert:
    """build_registry_insert generates valid SPARQL INSERT DATA."""

    def test_contains_fabric_node_type(self):
        sparql = build_registry_insert("http://localhost:8080", "did:webvh:abc:localhost%3A8080")
        assert "fabric:FabricNode" in sparql

    def test_contains_node_did(self):
        sparql = build_registry_insert("http://localhost:8080", "did:webvh:abc:localhost%3A8080")
        assert "did:webvh:abc:localhost%3A8080" in sparql

    def test_contains_graph_registry(self):
        sparql = build_registry_insert("http://localhost:8080", "did:webvh:abc:localhost%3A8080")
        assert "/graph/registry" in sparql

    def test_contains_endpoints(self):
        sparql = build_registry_insert("http://localhost:8080", "did:webvh:abc:localhost%3A8080")
        assert "/.well-known/void" in sparql
        assert "/sparql" in sparql
        assert "/inbox" in sparql
        assert "/1.0/identifiers/" in sparql

    def test_contains_conformance_vc(self):
        sparql = build_registry_insert("http://localhost:8080", "did:webvh:abc:localhost%3A8080")
        assert "/.well-known/conformance-vc.json" in sparql

    def test_self_registration_registered_by_self(self):
        did = "did:webvh:abc:localhost%3A8080"
        sparql = build_registry_insert("http://localhost:8080", did)
        assert "registeredBy" in sparql

    def test_remote_registered_by_different(self):
        sparql = build_registry_insert(
            "http://remote:8080",
            "did:webvh:xyz:remote%3A8080",
            registered_by="did:webvh:abc:localhost%3A8080",
        )
        assert "did:webvh:abc:localhost%3A8080" in sparql

    def test_contains_core_profile_conformance(self):
        sparql = build_registry_insert("http://localhost:8080", "did:webvh:abc:localhost%3A8080")
        assert "CoreProfile" in sparql

    def test_insert_data_syntax(self):
        sparql = build_registry_insert("http://localhost:8080", "did:webvh:abc:localhost%3A8080")
        assert "INSERT DATA" in sparql

    def test_contains_datetime(self):
        sparql = build_registry_insert("http://localhost:8080", "did:webvh:abc:localhost%3A8080")
        assert "xsd:dateTime" in sparql


class TestRegistryConstruct:
    """build_registry_construct generates SPARQL CONSTRUCT for all registry entries."""

    def test_returns_construct(self):
        sparql = build_registry_construct("http://localhost:8080")
        assert "CONSTRUCT" in sparql

    def test_queries_graph_registry(self):
        sparql = build_registry_construct("http://localhost:8080")
        assert "/graph/registry" in sparql


class TestRegistryEntryConstruct:
    """build_registry_entry_construct generates SPARQL CONSTRUCT for a single node."""

    def test_returns_construct(self):
        sparql = build_registry_entry_construct("http://localhost:8080", "did:webvh:abc:localhost%3A8080")
        assert "CONSTRUCT" in sparql

    def test_filters_by_did(self):
        sparql = build_registry_entry_construct("http://localhost:8080", "did:webvh:abc:localhost%3A8080")
        assert "did:webvh:abc:localhost%3A8080" in sparql


class TestValidAgentRoles:
    """VALID_AGENT_ROLES contains the D14 role taxonomy."""

    def test_has_seven_roles(self):
        assert len(VALID_AGENT_ROLES) == 7

    def test_contains_ingest_curator(self):
        assert "IngestCuratorRole" in VALID_AGENT_ROLES

    def test_contains_development_agent(self):
        assert "DevelopmentAgentRole" in VALID_AGENT_ROLES

    def test_contains_all_d14_roles(self):
        expected = {
            "IngestCuratorRole", "LinkingCuratorRole", "QARole",
            "MaintenanceRole", "SecurityMonitorRole",
            "IntegrityAuditorRole", "DevelopmentAgentRole",
        }
        assert set(VALID_AGENT_ROLES) == expected


class TestFabricNamespace:
    """FABRIC_NS is the correct namespace."""

    def test_namespace_value(self):
        assert FABRIC_NS == "https://w3id.org/cogitarelink/fabric#"


# --- Task 2.1/2.2/2.6: Admission helper tests ---

class TestCheckVoidConformance:
    """check_void_conformance validates CoreProfile in VoID via rdflib parsing."""

    _VOID_PREFIX = """\
@prefix void: <http://rdfs.org/ns/void#> .
@prefix dct:  <http://purl.org/dc/terms/> .
@prefix fabric: <https://w3id.org/cogitarelink/fabric#> .
"""

    def test_valid_void_with_core_profile(self):
        void = self._VOID_PREFIX + """
<http://example.org/void> a void:Dataset ;
    dct:conformsTo fabric:CoreProfile .
"""
        assert check_void_conformance(void) is True

    def test_missing_profile(self):
        void = self._VOID_PREFIX + """
<http://example.org/void> a void:Dataset ;
    dct:conformsTo <https://example.org/SomeOtherProfile> .
"""
        assert check_void_conformance(void) is False

    def test_empty_string(self):
        assert check_void_conformance("") is False

    def test_partial_namespace_no_match(self):
        void = self._VOID_PREFIX + """
<http://example.org/void> a void:Dataset ;
    dct:conformsTo <https://w3id.org/cogitarelink/other#CoreProfile> .
"""
        assert check_void_conformance(void) is False

    def test_rejects_substring_in_comment(self):
        """Regression: old substring check matched comments."""
        void = self._VOID_PREFIX + """
# cogitarelink/fabric#CoreProfile mentioned in comment only
<http://example.org/void> a void:Dataset ;
    dct:conformsTo <https://example.org/SomeOtherProfile> .
"""
        assert check_void_conformance(void) is False

    def test_rejects_substring_in_literal(self):
        """Regression: old substring check matched string literals."""
        void = self._VOID_PREFIX + """
<http://example.org/void> a void:Dataset ;
    dct:title "cogitarelink/fabric#CoreProfile is referenced" ;
    dct:conformsTo <https://example.org/SomeOtherProfile> .
"""
        assert check_void_conformance(void) is False

    def test_invalid_turtle_returns_false(self):
        assert check_void_conformance("this is not valid turtle {{{}}}") is False


# --- Task 3.1/3.2: Agent SPARQL builder tests ---

class TestBuildAgentInsert:
    """build_agent_insert generates valid SPARQL INSERT DATA for agents."""

    def test_contains_registered_agent_type(self):
        sparql = build_agent_insert(
            "http://localhost:8080", "did:webvh:abc:localhost%3A8080:agents:test-uuid",
            "IngestCuratorRole", ["/graph/observations"], ["read", "write"])
        assert "fabric:RegisteredAgent" in sparql

    def test_contains_agent_did(self):
        agent_did = "did:webvh:abc:localhost%3A8080:agents:test-uuid"
        sparql = build_agent_insert(
            "http://localhost:8080", agent_did,
            "IngestCuratorRole", ["/graph/observations"], ["read"])
        assert agent_did in sparql

    def test_contains_role(self):
        sparql = build_agent_insert(
            "http://localhost:8080", "did:webvh:abc:agents:test",
            "LinkingCuratorRole", ["/graph/crosswalks"], ["read"])
        assert "fabric:LinkingCuratorRole" in sparql

    def test_contains_authorized_graphs(self):
        sparql = build_agent_insert(
            "http://localhost:8080", "did:webvh:abc:agents:test",
            "IngestCuratorRole", ["/graph/observations", "/graph/entities"], ["write"])
        assert "/graph/observations" in sparql
        assert "/graph/entities" in sparql

    def test_contains_authorized_operations(self):
        sparql = build_agent_insert(
            "http://localhost:8080", "did:webvh:abc:agents:test",
            "QARole", ["/graph/observations"], ["read", "write"])
        assert '"read"' in sparql
        assert '"write"' in sparql

    def test_contains_graph_agents(self):
        sparql = build_agent_insert(
            "http://localhost:8080", "did:webvh:abc:agents:test",
            "MaintenanceRole", [], [])
        assert "/graph/agents" in sparql

    def test_invalid_role_raises(self):
        with pytest.raises(ValueError, match="Invalid agent role"):
            build_agent_insert(
                "http://localhost:8080", "did:webvh:abc:agents:test",
                "BogusRole", [], [])

    def test_contains_home_node(self):
        sparql = build_agent_insert(
            "http://localhost:8080", "did:webvh:abc:agents:test",
            "SecurityMonitorRole", [], [])
        assert "http://localhost:8080" in sparql
        assert "homeNode" in sparql

    def test_contains_datetime(self):
        sparql = build_agent_insert(
            "http://localhost:8080", "did:webvh:abc:agents:test",
            "IntegrityAuditorRole", [], [])
        assert "xsd:dateTime" in sparql


class TestBuildAgentsListConstruct:
    """build_agents_list_construct generates SPARQL CONSTRUCT for all agents."""

    def test_returns_construct(self):
        sparql = build_agents_list_construct("http://localhost:8080")
        assert "CONSTRUCT" in sparql

    def test_queries_graph_agents(self):
        sparql = build_agents_list_construct("http://localhost:8080")
        assert "/graph/agents" in sparql


class TestBuildAgentConstruct:
    """build_agent_construct generates SPARQL CONSTRUCT for a single agent."""

    def test_returns_construct(self):
        sparql = build_agent_construct("http://localhost:8080", "did:webvh:abc:agents:test")
        assert "CONSTRUCT" in sparql

    def test_filters_by_did(self):
        sparql = build_agent_construct("http://localhost:8080", "did:webvh:abc:agents:test")
        assert "did:webvh:abc:agents:test" in sparql
