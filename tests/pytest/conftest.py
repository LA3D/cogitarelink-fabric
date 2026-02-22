"""Pytest configuration for cogitarelink-fabric tests.

Integration tests expect the fabric stack running:
    docker compose up -d

Unit tests run standalone (no Docker required).
"""
import os
import sys
import pathlib
import pytest

# Add project root to sys.path so `fabric.node.main` is importable
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))

GATEWAY = os.environ.get("GATEWAY", "http://localhost:8080")
OXIGRAPH = os.environ.get("OXIGRAPH", "http://localhost:7878")


@pytest.fixture(scope="session")
def gateway_url():
    return GATEWAY


@pytest.fixture(scope="session")
def oxigraph_url():
    return OXIGRAPH
