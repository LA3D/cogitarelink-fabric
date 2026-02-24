"""DID resolution helpers — pure Python, no FastAPI dependency (D3, D5, D25).

Same pattern as void_templates.py: imported by main.py and unit tests.
"""
import json
import os
import re
import time
import urllib.parse


_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def is_valid_uuid(s: str) -> bool:
    return bool(_UUID_RE.match(s))


def sparql_escape(s: str) -> str:
    """Escape a string for embedding in a SPARQL double-quoted literal."""
    return (s
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t"))


def classify_identifier(identifier: str, node_base: str) -> str:
    """Return: 'local-did', 'remote-did', 'did-key', 'local-entity', 'external-http', 'invalid'."""
    if identifier.startswith("did:webvh:"):
        domain = decode_webvh_domain(identifier)
        node_host = urllib.parse.urlparse(node_base).netloc
        if domain and domain == node_host:
            return "local-did"
        return "remote-did"
    if identifier.startswith("did:key:"):
        return "did-key"
    if identifier.startswith(node_base.rstrip("/") + "/entity/"):
        return "local-entity"
    if identifier.startswith("http://") or identifier.startswith("https://"):
        return "external-http"
    return "invalid"


def _fully_decode(s: str) -> str:
    """Iteratively percent-decode until stable (handles double+ encoding)."""
    prev = None
    while prev != s:
        prev = s
        s = urllib.parse.unquote(s)
    return s


def parse_did_log(did_jsonl_text: str, target_did: str | None = None) -> tuple[dict, dict] | None:
    """Parse did.jsonl, return (did_document, metadata) from last matching entry."""
    lines = [l.strip() for l in did_jsonl_text.strip().split("\n") if l.strip()]
    if not lines:
        return None

    last_entry = json.loads(lines[-1])
    did_doc = last_entry.get("state", last_entry)

    if target_did and _fully_decode(did_doc.get("id", "")) != _fully_decode(target_did):
        return None

    metadata = {
        k: last_entry[k]
        for k in ("versionId", "versionTime", "created", "updated")
        if k in last_entry
    }
    return did_doc, metadata


def build_resolution_result(did_doc: dict, metadata: dict) -> dict:
    """Build W3C DID Resolution Result three-field envelope."""
    return {
        "didDocument": did_doc,
        "didResolutionMetadata": {"contentType": "application/did+ld+json"},
        "didDocumentMetadata": metadata,
    }


def build_deref_result(content: dict, content_type: str) -> dict:
    """Build W3C Dereferencing Result envelope."""
    return {
        "content": content,
        "dereferencingMetadata": {"contentType": content_type},
        "contentMetadata": {},
    }


def build_error_result(error_code: str, message: str) -> dict:
    """Build W3C DID Resolution error envelope."""
    return {
        "didDocument": None,
        "didResolutionMetadata": {"error": error_code, "message": message},
        "didDocumentMetadata": {},
    }


def decode_webvh_domain(did: str) -> str | None:
    """Extract and decode domain from did:webvh:{scid}:{encoded-domain}.

    did:webvh format: did:webvh:<scid>:<encoded-domain>
    The domain may be double-percent-encoded (%253A → %3A → :).
    """
    # Split after "did:webvh:" — take the last colon-separated segment as domain
    parts = did.split(":")
    if len(parts) < 4 or parts[0] != "did" or parts[1] != "webvh":
        return None
    # Domain is everything after scid (last segment, may contain encoded colons)
    # Rejoin parts[3:] in case domain itself had unencoded colons (unlikely but safe)
    encoded_domain = ":".join(parts[3:])
    # Decode iteratively — handles double encoding (%253A → %3A → :)
    decoded = encoded_domain
    prev = None
    while prev != decoded:
        prev = decoded
        decoded = urllib.parse.unquote(decoded)
    return decoded


def uuid7() -> str:
    """Generate UUIDv7 per RFC 9562 — timestamp-sortable, no external deps (D11)."""
    ms = int(time.time() * 1000)
    rand = int.from_bytes(os.urandom(10), "big")
    # 48 bits timestamp | 4 bits version (0x7) | 12 bits rand_a
    # 2 bits variant (0b10) | 62 bits rand_b
    hi = (ms << 16) | 0x7000 | ((rand >> 62) & 0x0FFF)
    lo = (0b10 << 62) | (rand & 0x3FFFFFFFFFFFFFFF)
    h = f"{hi:016x}{lo:016x}"
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"
