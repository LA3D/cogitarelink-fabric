"""Unit tests for VP Bearer token verification (D13/D14)."""
import base64
import json
import pytest
from datetime import datetime, timezone, timedelta
from fabric.node.vp_auth import (
    decode_bearer_token,
    extract_agent_context,
    AgentContext,
    VALID_AGENT_ROLES,
)


def _make_vp(role="DevelopmentAgentRole", valid_minutes=5, graphs=None, ops=None):
    """Build a mock VP for testing."""
    now = datetime.now(timezone.utc)
    return {
        "@context": ["https://www.w3.org/ns/credentials/v2"],
        "type": ["VerifiablePresentation"],
        "holder": "did:webvh:abc:bootstrap.cogitarelink.ai:agents:test-agent",
        "verifiableCredential": [{
            "@context": ["https://www.w3.org/ns/credentials/v2"],
            "type": ["VerifiableCredential", "AgentAuthorizationCredential"],
            "credentialSubject": {
                "id": "did:webvh:abc:bootstrap.cogitarelink.ai:agents:test-agent",
                "agentRole": f"fabric:{role}",
                "authorizedGraphs": graphs or ["/graph/observations"],
                "authorizedOperations": ops or ["read"],
                "homeNode": "did:webvh:abc:bootstrap.cogitarelink.ai",
            },
            "proof": {"type": "DataIntegrityProof"},
        }],
        "validUntil": (now + timedelta(minutes=valid_minutes)).isoformat(),
        "proof": {"type": "DataIntegrityProof", "cryptosuite": "eddsa-jcs-2022"},
    }


def _encode_vp(vp: dict) -> str:
    """Base64url-encode a VP dict."""
    return base64.urlsafe_b64encode(json.dumps(vp).encode()).decode().rstrip("=")


class TestDecodeBearer:
    def test_valid_bearer(self):
        vp = _make_vp()
        token = _encode_vp(vp)
        result = decode_bearer_token(f"Bearer {token}")
        assert result["type"] == ["VerifiablePresentation"]

    def test_missing_bearer_prefix(self):
        assert decode_bearer_token("NotBearer xyz") is None

    def test_empty_header(self):
        assert decode_bearer_token("") is None

    def test_none_header(self):
        assert decode_bearer_token(None) is None

    def test_invalid_base64(self):
        assert decode_bearer_token("Bearer !!!invalid!!!") is None

    def test_invalid_json(self):
        token = base64.urlsafe_b64encode(b"not json").decode()
        assert decode_bearer_token(f"Bearer {token}") is None


class TestExtractAgentContext:
    def test_valid_vp(self):
        vp = _make_vp(role="QARole", graphs=["/graph/observations"], ops=["read"])
        ctx = extract_agent_context(vp)
        assert isinstance(ctx, AgentContext)
        assert ctx.agent_did == "did:webvh:abc:bootstrap.cogitarelink.ai:agents:test-agent"
        assert ctx.agent_role == "QARole"
        assert ctx.authorized_graphs == ["/graph/observations"]
        assert ctx.authorized_operations == ["read"]

    def test_expired_vp(self):
        vp = _make_vp(valid_minutes=-1)
        assert extract_agent_context(vp) is None

    def test_missing_valid_until(self):
        vp = _make_vp()
        del vp["validUntil"]
        assert extract_agent_context(vp) is None

    def test_invalid_role(self):
        vp = _make_vp(role="BogusRole")
        assert extract_agent_context(vp) is None

    def test_role_strips_fabric_prefix(self):
        vp = _make_vp(role="IngestCuratorRole")
        ctx = extract_agent_context(vp)
        assert ctx.agent_role == "IngestCuratorRole"

    def test_no_credentials(self):
        vp = _make_vp()
        vp["verifiableCredential"] = []
        assert extract_agent_context(vp) is None

    def test_valid_agent_roles_matches_registry(self):
        from fabric.node.registry import VALID_AGENT_ROLES as REGISTRY_ROLES
        assert VALID_AGENT_ROLES == REGISTRY_ROLES

    def test_all_roles_accepted(self):
        for role in VALID_AGENT_ROLES:
            vp = _make_vp(role=role)
            ctx = extract_agent_context(vp)
            assert ctx is not None, f"Role {role} should be accepted"
            assert ctx.agent_role == role
