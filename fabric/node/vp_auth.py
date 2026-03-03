"""VP Bearer token verification for SPARQL endpoint gating (D13/D14).

Pure Python helpers — no FastAPI dependency. Imported by main.py (Docker)
and unit tests (local). Same pattern as did_resolver.py and void_templates.py.
"""
import base64
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from fabric.node.registry import VALID_AGENT_ROLES


@dataclass
class AgentContext:
    """Extracted from a verified VP. Passed to route handlers."""
    agent_did: str
    agent_role: str
    authorized_graphs: list[str]
    authorized_operations: list[str]


def decode_bearer_token(auth_header: str) -> dict | None:
    """Decode Authorization: Bearer <base64url(vp_json)> → VP dict or None."""
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    try:
        padded = token + "=" * (-len(token) % 4)
        raw = base64.urlsafe_b64decode(padded)
        return json.loads(raw)
    except Exception:
        return None


def extract_agent_context(vp: dict) -> AgentContext | None:
    """Extract and validate agent context from a VP dict.

    Checks: validUntil not expired, agentRole in VALID_AGENT_ROLES,
    credentialSubject present. Does NOT verify cryptographic proofs
    (that's Credo's job via POST /presentations/verify).
    """
    valid_until = vp.get("validUntil")
    if not valid_until:
        return None
    try:
        expiry = datetime.fromisoformat(valid_until)
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if expiry < datetime.now(timezone.utc):
            return None
    except (ValueError, TypeError):
        return None

    credentials = vp.get("verifiableCredential", [])
    if not credentials:
        return None

    subject = credentials[0].get("credentialSubject", {})
    raw_role = subject.get("agentRole", "")
    role = raw_role.removeprefix("fabric:")
    if role not in VALID_AGENT_ROLES:
        return None

    return AgentContext(
        agent_did=subject.get("id", vp.get("holder", "")),
        agent_role=role,
        authorized_graphs=subject.get("authorizedGraphs", []),
        authorized_operations=subject.get("authorizedOperations", []),
    )
