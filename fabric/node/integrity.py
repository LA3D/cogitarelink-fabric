"""Content integrity utilities — pure Python, no FastAPI dependency (D26).

Same pattern as did_resolver.py and void_templates.py:
imported by main.py (Docker) and unit tests (local).

Implements VC Data Model 2.0 §5.3 relatedResource + digestMultibase.
"""
import base64
import hashlib

_B58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'


def b58_encode(data: bytes) -> str:
    """Base58btc encode (Bitcoin alphabet)."""
    if not data:
        return ''
    n = int.from_bytes(data, 'big')
    result = []
    while n > 0:
        n, r = divmod(n, 58)
        result.append(_B58_ALPHABET[r])
    for b in data:
        if b == 0:
            result.append(_B58_ALPHABET[0])
        else:
            break
    return ''.join(reversed(result))


def b58_decode(s: str) -> bytes:
    """Base58btc decode."""
    if not s:
        return b''
    n = 0
    for c in s:
        n = n * 58 + _B58_ALPHABET.index(c)
    pad = 0
    for c in s:
        if c == _B58_ALPHABET[0]:
            pad += 1
        else:
            break
    result = n.to_bytes((n.bit_length() + 7) // 8, 'big') if n else b''
    return b'\x00' * pad + result


def compute_digest_multibase(content: bytes) -> str:
    """SHA-256 hash, return as multibase base58btc ('z' prefix)."""
    h = hashlib.sha256(content).digest()
    return 'z' + b58_encode(h)


def compute_digest_sri(content: bytes) -> str:
    """SHA-256 hash, return as SRI format (sha256-{base64})."""
    h = hashlib.sha256(content).digest()
    return 'sha256-' + base64.b64encode(h).decode('ascii')


def verify_digest_multibase(content: bytes, expected: str) -> bool:
    """Verify content matches expected digestMultibase."""
    return compute_digest_multibase(content) == expected


def verify_related_resources(vc: dict, fetcher=None) -> list[dict]:
    """Verify all relatedResource entries in a VC.

    Args:
        vc: Parsed VC JSON (must have 'relatedResource' array)
        fetcher: callable(url) -> bytes; if None, uses httpx synchronous GET

    Returns:
        List of {url, expected, actual, match, mediaType} dicts
    """
    resources = vc.get('relatedResource', [])
    if not resources:
        return []

    if fetcher is None:
        import httpx
        def fetcher(url):
            r = httpx.get(url)
            r.raise_for_status()
            return r.content

    results = []
    for res in resources:
        url = res.get('id', '')
        expected = res.get('digestMultibase', '')
        try:
            content = fetcher(url)
            actual = compute_digest_multibase(content)
            results.append({
                'url': url,
                'expected': expected,
                'actual': actual,
                'match': actual == expected,
                'mediaType': res.get('mediaType', ''),
            })
        except Exception as e:
            results.append({
                'url': url,
                'expected': expected,
                'actual': None,
                'match': False,
                'error': str(e),
            })
    return results
