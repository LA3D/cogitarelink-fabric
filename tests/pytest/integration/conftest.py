import os
import ssl
import pytest
import httpx

GATEWAY = os.environ.get("FABRIC_GATEWAY", "https://bootstrap.cogitarelink.ai")
CA_CERT = os.environ.get("FABRIC_CA_CERT", "caddy-root.crt")


@pytest.fixture(scope="session")
def ssl_context():
    ctx = ssl.create_default_context()
    ctx.load_verify_locations(CA_CERT)
    return ctx


@pytest.fixture(scope="session")
def vp_token():
    """Obtain a VP Bearer token for auth-gated SPARQL endpoints."""
    if os.environ.get("FABRIC_AUTH_ENABLED", "true").lower() != "true":
        return None
    r = httpx.post(
        f"{GATEWAY}/test/create-vp",
        json={
            "agentRole": "DevelopmentAgentRole",
            "authorizedGraphs": ["*"],
            "authorizedOperations": ["read", "write"],
        },
        timeout=15.0,
        verify=False,
    )
    r.raise_for_status()
    return r.json()["token"]


def _auth_headers(vp_token, extra=None):
    """Build headers dict with optional VP Bearer auth."""
    h = extra or {}
    if vp_token:
        h["Authorization"] = f"Bearer {vp_token}"
    return h


@pytest.fixture(scope="session")
def sparql_headers(vp_token):
    """Headers for SPARQL update requests, with auth if enabled."""
    h = {"Content-Type": "application/x-www-form-urlencoded"}
    if vp_token:
        h["Authorization"] = f"Bearer {vp_token}"
    return h


@pytest.fixture(scope="session")
def sparql_query_headers(vp_token):
    """Headers for SPARQL query requests, with auth if enabled."""
    h = {"Accept": "text/turtle"}
    if vp_token:
        h["Authorization"] = f"Bearer {vp_token}"
    return h
