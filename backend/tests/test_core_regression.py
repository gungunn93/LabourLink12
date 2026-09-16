import os
import uuid

import requests


BASE_URL = os.environ.get("TEST_BASE_URL", "http://127.0.0.1:8001").rstrip("/")


def test_health():
    response = requests.get(f"{BASE_URL}/api/health", timeout=10)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "running"
    assert data["payment_gateway"] == "razorpay"


def test_registration_and_me():
    email = f"TEST_{uuid.uuid4().hex}@example.com"
    payload = {"name": "TEST Worker", "email": email, "password": "StrongPass123!", "role": "worker"}
    response = requests.post(f"{BASE_URL}/api/auth/register", json=payload, timeout=10)
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["user"]["email"] == email.lower()
    assert body["user"]["role"] == "worker"
    me = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {body['token']}"}, timeout=10)
    assert me.status_code == 200
    assert me.json()["data"]["email"] == email.lower()


def test_protected_endpoint_rejects_missing_token():
    response = requests.get(f"{BASE_URL}/api/payments/history", timeout=10)
    assert response.status_code == 401


def test_razorpay_config_is_available_for_authenticated_user():
    email = f"TEST_{uuid.uuid4().hex}@example.com"
    response = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"name": "TEST Employer", "email": email, "password": "StrongPass123!", "role": "employer"},
        timeout=10,
    )
    assert response.status_code == 200
    token = response.json()["data"]["token"]
    config = requests.get(f"{BASE_URL}/api/payments/config", headers={"Authorization": f"Bearer {token}"}, timeout=10)
    assert config.status_code == 200
    assert config.json()["data"]["mode"] == "razorpay"
    assert config.json()["data"]["key_id"]