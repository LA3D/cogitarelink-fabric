"""Unit tests for content integrity module (D26)."""
import hashlib

from fabric.node.integrity import (
    b58_encode,
    b58_decode,
    compute_digest_multibase,
    compute_digest_sri,
    verify_digest_multibase,
    verify_related_resources,
)


# --- b58 round-trip ---

def test_b58_roundtrip():
    data = b'\x00\x01\x02\xff' * 8
    assert b58_decode(b58_encode(data)) == data


def test_b58_roundtrip_zeros():
    data = b'\x00\x00\x00'
    assert b58_decode(b58_encode(data)) == data


def test_b58_roundtrip_empty():
    assert b58_decode(b58_encode(b'')) == b''


# --- compute_digest_multibase ---

def test_compute_digest_multibase_z_prefix():
    assert compute_digest_multibase(b'').startswith('z')
    assert len(compute_digest_multibase(b'')) > 10


def test_compute_digest_multibase_deterministic():
    content = b'hello world'
    assert compute_digest_multibase(content) == compute_digest_multibase(content)


def test_compute_digest_multibase_known_vector():
    # SHA-256("hello world") = b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9
    content = b'hello world'
    digest = compute_digest_multibase(content)
    # Verify by decoding back to raw hash and comparing hex
    raw = b58_decode(digest[1:])  # strip 'z' prefix
    assert raw.hex() == 'b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9'


# --- compute_digest_sri ---

def test_compute_digest_sri_prefix():
    sri = compute_digest_sri(b'hello world')
    assert sri.startswith('sha256-')


def test_compute_digest_sri_known_vector():
    import base64
    content = b'hello world'
    expected_hash = hashlib.sha256(content).digest()
    expected_sri = 'sha256-' + base64.b64encode(expected_hash).decode('ascii')
    assert compute_digest_sri(content) == expected_sri


# --- verify_digest_multibase ---

def test_verify_digest_multibase_match():
    content = b'test content'
    digest = compute_digest_multibase(content)
    assert verify_digest_multibase(content, digest)


def test_verify_digest_multibase_mismatch():
    assert not verify_digest_multibase(b'content A', compute_digest_multibase(b'content B'))


# --- verify_related_resources ---

def test_verify_related_resources_match():
    content_a = b'void turtle content'
    content_b = b'shacl turtle content'
    vc = {
        'relatedResource': [
            {'id': 'http://example.org/void', 'digestMultibase': compute_digest_multibase(content_a), 'mediaType': 'text/turtle'},
            {'id': 'http://example.org/shacl', 'digestMultibase': compute_digest_multibase(content_b), 'mediaType': 'text/turtle'},
        ]
    }
    fetcher = lambda url: content_a if 'void' in url else content_b
    results = verify_related_resources(vc, fetcher=fetcher)
    assert len(results) == 2
    assert all(r['match'] for r in results)


def test_verify_related_resources_mismatch():
    vc = {
        'relatedResource': [
            {'id': 'http://example.org/void', 'digestMultibase': 'zBadHash', 'mediaType': 'text/turtle'},
        ]
    }
    results = verify_related_resources(vc, fetcher=lambda url: b'actual content')
    assert len(results) == 1
    assert not results[0]['match']


def test_verify_related_resources_empty():
    assert verify_related_resources({}) == []
    assert verify_related_resources({'relatedResource': []}) == []


def test_verify_related_resources_fetch_error():
    def bad_fetcher(url):
        raise ConnectionError("down")
    vc = {
        'relatedResource': [
            {'id': 'http://example.org/void', 'digestMultibase': 'zXYZ', 'mediaType': 'text/turtle'},
        ]
    }
    results = verify_related_resources(vc, fetcher=bad_fetcher)
    assert len(results) == 1
    assert not results[0]['match']
    assert 'error' in results[0]
