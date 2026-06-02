import pytest
from app.services.auth import AuthService


def test_password_hash_and_verify():
    svc = AuthService()
    hashed = svc.hash_password("secret123")
    assert svc.verify_password("secret123", hashed)
    assert not svc.verify_password("wrong", hashed)


def test_create_and_decode_access_token():
    svc = AuthService()
    token = svc.create_access_token("testuser")
    claims = svc.decode_token(token)
    assert claims["sub"] == "testuser"
    assert claims["type"] == "access"


def test_create_and_decode_refresh_token():
    svc = AuthService()
    token = svc.create_refresh_token("testuser")
    claims = svc.decode_token(token)
    assert claims["type"] == "refresh"


def test_decode_invalid_token_returns_none():
    svc = AuthService()
    assert svc.decode_token("not.a.valid.token") is None
