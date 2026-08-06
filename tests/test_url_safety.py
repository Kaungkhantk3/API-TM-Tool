import pytest

from app.url_safety import validate_public_url


def test_rejects_localhost():
    with pytest.raises(ValueError, match="Localhost"):
        validate_public_url("https://localhost:8000")


def test_rejects_private_dns_result(monkeypatch):
    monkeypatch.setattr("app.url_safety.socket.getaddrinfo", lambda *args, **kwargs: [(None, None, None, None, ("10.0.0.10", 443))])
    with pytest.raises(ValueError, match="Private"):
        validate_public_url("https://internal.example")
