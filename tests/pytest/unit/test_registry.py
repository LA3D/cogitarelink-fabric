"""Unit tests for fabric/node/registry.py — registry + agent SPARQL helpers (D12, D13, D14)."""
import pytest

# Task 1.1: RED — these imports will fail until registry.py exists
from fabric.node.registry import (
    build_registry_insert,
    build_registry_construct,
    build_registry_entry_construct,
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
