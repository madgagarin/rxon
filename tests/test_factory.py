import pytest

from rxon.transports.factory import create_transport


def test_create_transport_http():
    t = create_transport("http://localhost:8080", "worker-1", "token")
    assert t.base_url == "http://localhost:8080"


def test_create_transport_https():
    t = create_transport("https://api.example.com", "worker-1", "token")
    assert t.base_url == "https://api.example.com"


def test_create_transport_invalid_scheme():
    with pytest.raises(ValueError) as exc:
        create_transport("ftp://localhost", "worker-1", "token")
    assert "Unsupported transport scheme" in str(exc.value)
