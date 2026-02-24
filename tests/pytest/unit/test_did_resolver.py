"""Unit tests for DID resolver helper module (D3, D5, D25)."""
import json

from fabric.node.did_resolver import (
    classify_identifier,
    is_valid_uuid,
    parse_did_log,
    build_resolution_result,
    build_deref_result,
    build_error_result,
    decode_webvh_domain,
    sparql_escape,
    uuid7,
)

NODE_BASE = "http://localhost:8080"


# --- classify_identifier ---

def test_classify_local_did():
    # did:webvh format: did:webvh:{scid}:{encoded-domain}
    did = "did:webvh:abc123scid:localhost%3A8080"
    assert classify_identifier(did, NODE_BASE) == "local-did"


def test_classify_local_did_double_encoded():
    # Credo 0.6.x produces double-percent-encoded domains
    did = "did:webvh:QmV7DDucsu8u:localhost%253A8080"
    assert classify_identifier(did, NODE_BASE) == "local-did"


def test_classify_remote_did():
    did = "did:webvh:xyz789scid:example.com%3A8080"
    assert classify_identifier(did, NODE_BASE) == "remote-did"


def test_classify_did_key():
    did = "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK"
    assert classify_identifier(did, NODE_BASE) == "did-key"


def test_classify_local_entity():
    uri = "http://localhost:8080/entity/01945abc-def0-7000-8000-000000000001"
    assert classify_identifier(uri, NODE_BASE) == "local-entity"


def test_classify_external_http():
    uri = "https://example.org/vocab/Thing"
    assert classify_identifier(uri, NODE_BASE) == "external-http"


def test_classify_invalid():
    assert classify_identifier("garbage", NODE_BASE) == "invalid"


def test_classify_domain_suffix_not_confused():
    # "8080" and "ost:8080" are suffixes of "localhost:8080" but not the same host
    assert classify_identifier("did:webvh:abc:8080", NODE_BASE) == "remote-did"
    assert classify_identifier("did:webvh:abc:ost%3A8080", NODE_BASE) == "remote-did"
    assert classify_identifier("did:webvh:ost%3A8080:abc", NODE_BASE) == "remote-did"


# --- parse_did_log ---

SAMPLE_LOG_ENTRY = {
    "versionId": "1",
    "versionTime": "2026-02-24T12:00:00Z",
    "state": {
        "id": "did:webvh:abc123:localhost%3A8080",
        "@context": ["https://www.w3.org/ns/did/v1"],
        "verificationMethod": [{"id": "#key-1", "type": "Multikey"}],
        "authentication": ["#key-1"],
        "assertionMethod": ["#key-1"],
    },
}


def test_parse_did_log():
    # Multi-line JSONL — should return last entry's state
    line1 = json.dumps({"versionId": "0", "state": {"id": "old"}})
    line2 = json.dumps(SAMPLE_LOG_ENTRY)
    text = f"{line1}\n{line2}\n"

    result = parse_did_log(text)
    assert result is not None
    did_doc, metadata = result
    assert did_doc["id"] == "did:webvh:abc123:localhost%3A8080"
    assert metadata["versionId"] == "1"


def test_parse_did_log_empty():
    assert parse_did_log("") is None
    assert parse_did_log("   \n  ") is None


def test_parse_did_log_malformed_json():
    import pytest
    with pytest.raises(json.JSONDecodeError):
        parse_did_log("this is not json\n")


def test_parse_did_log_no_state_field():
    # Entry without "state" falls back to the entry itself
    entry = json.dumps({"id": "did:webvh:fallback:localhost%3A8080", "versionId": "1"})
    result = parse_did_log(entry)
    assert result is not None
    did_doc, metadata = result
    assert did_doc["id"] == "did:webvh:fallback:localhost%3A8080"


def test_parse_did_log_created_updated_metadata():
    entry_with_timestamps = {
        "versionId": "2",
        "versionTime": "2026-02-24T14:00:00Z",
        "created": "2026-02-24T12:00:00Z",
        "updated": "2026-02-24T14:00:00Z",
        "state": {"id": "did:webvh:ts123:localhost%3A8080"},
    }
    result = parse_did_log(json.dumps(entry_with_timestamps))
    assert result is not None
    _, metadata = result
    assert metadata["created"] == "2026-02-24T12:00:00Z"
    assert metadata["updated"] == "2026-02-24T14:00:00Z"
    assert metadata["versionId"] == "2"
    assert metadata["versionTime"] == "2026-02-24T14:00:00Z"


def test_parse_did_log_target_did():
    entry = json.dumps(SAMPLE_LOG_ENTRY)
    # Matching DID
    result = parse_did_log(entry, target_did="did:webvh:abc123:localhost%3A8080")
    assert result is not None
    # Non-matching DID
    result = parse_did_log(entry, target_did="did:webvh:other:xyz")
    assert result is None


def test_parse_did_log_target_did_double_encoded():
    """Credo stores %253A but URL-decoded identifier has %3A — should still match."""
    double_encoded = {
        "versionId": "1",
        "state": {"id": "did:webvh:abc123:localhost%253A8080"},
    }
    entry = json.dumps(double_encoded)
    # URL-decoded form (%253A → %3A) should match stored %253A form
    result = parse_did_log(entry, target_did="did:webvh:abc123:localhost%3A8080")
    assert result is not None
    # Fully decoded form should also match
    result = parse_did_log(entry, target_did="did:webvh:abc123:localhost:8080")
    assert result is not None


# --- build_resolution_result ---

def test_build_resolution_result():
    did_doc = {"id": "did:webvh:abc123:localhost%3A8080"}
    metadata = {"versionId": "1", "versionTime": "2026-02-24T12:00:00Z"}
    result = build_resolution_result(did_doc, metadata)

    assert result["didDocument"]["id"] == "did:webvh:abc123:localhost%3A8080"
    assert result["didResolutionMetadata"]["contentType"] == "application/did+ld+json"
    assert "didDocumentMetadata" in result
    assert result["didDocumentMetadata"]["versionId"] == "1"


# --- build_error_result ---

def test_build_error_result():
    result = build_error_result("notFound", "DID not found")
    assert result["didDocument"] is None
    assert result["didResolutionMetadata"]["error"] == "notFound"
    assert result["didResolutionMetadata"]["message"] == "DID not found"
    assert result["didDocumentMetadata"] == {}


# --- build_deref_result ---

def test_build_deref_result():
    content = {"@id": "http://localhost:8080/entity/abc", "http://www.w3.org/ns/sosa/observes": {}}
    result = build_deref_result(content, "application/ld+json")
    assert result["content"] == content
    assert result["dereferencingMetadata"]["contentType"] == "application/ld+json"
    assert result["contentMetadata"] == {}


# --- decode_webvh_domain ---

def test_decode_webvh_domain():
    # did:webvh:{scid}:{encoded-domain}
    did = "did:webvh:abc123scid:localhost%3A8080"
    domain = decode_webvh_domain(did)
    assert domain == "localhost:8080"


def test_decode_webvh_domain_double_encoded():
    # Credo 0.6.x double-percent-encodes the domain
    did = "did:webvh:QmV7scid:localhost%253A8080"
    domain = decode_webvh_domain(did)
    assert domain == "localhost:8080"


def test_decode_webvh_domain_no_port():
    did = "did:webvh:abc123scid:example.com"
    domain = decode_webvh_domain(did)
    assert domain == "example.com"


def test_decode_webvh_domain_invalid():
    assert decode_webvh_domain("did:key:z6Mk...") is None
    assert decode_webvh_domain("garbage") is None


# --- sparql_escape ---

def test_sparql_escape_quotes():
    assert sparql_escape('say "hello"') == 'say \\"hello\\"'


def test_sparql_escape_backslash():
    assert sparql_escape("path\\to") == "path\\\\to"


def test_sparql_escape_newlines():
    assert sparql_escape("line1\nline2\r\n") == "line1\\nline2\\r\\n"


def test_sparql_escape_injection_attempt():
    # Simulates SPARQL injection via actor field
    malicious = '" . } } INSERT DATA { GRAPH <http://evil> { <x> <y> <z> } } #'
    escaped = sparql_escape(malicious)
    assert '"' not in escaped.replace('\\"', '')  # no unescaped quotes


# --- is_valid_uuid ---

def test_is_valid_uuid():
    assert is_valid_uuid("01945abc-def0-7000-8000-000000000001")
    assert is_valid_uuid("A1945ABC-DEF0-7000-8000-000000000001")  # case insensitive


def test_is_valid_uuid_rejects_bad():
    assert not is_valid_uuid("not-a-uuid")
    assert not is_valid_uuid("test> <evil> <y> <z")
    assert not is_valid_uuid("")


# --- uuid7 ---

def test_uuid7_format():
    u = uuid7()
    assert is_valid_uuid(u)


def test_uuid7_version_bits():
    # RFC 9562: version nibble (bits 48-51) = 0x7
    u = uuid7()
    assert u[14] == "7"  # version nibble at position 14


def test_uuid7_variant_bits():
    # RFC 9562: variant bits (bits 64-65) = 0b10 → hex digit 8,9,a,b
    u = uuid7()
    assert u[19] in "89ab"


def test_uuid7_monotonic():
    # Two UUIDs generated in sequence should be ordered
    import time
    u1 = uuid7()
    time.sleep(0.002)
    u2 = uuid7()
    assert u1 < u2
