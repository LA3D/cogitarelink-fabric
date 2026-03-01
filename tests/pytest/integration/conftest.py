import os
import ssl
import pytest

GATEWAY = os.environ.get("FABRIC_GATEWAY", "https://bootstrap.cogitarelink.ai")
CA_CERT = os.environ.get("FABRIC_CA_CERT", "caddy-root.crt")


@pytest.fixture(scope="session")
def ssl_context():
    ctx = ssl.create_default_context()
    ctx.load_verify_locations(CA_CERT)
    return ctx
