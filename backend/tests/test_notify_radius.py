"""Tests for the notify_radius_km parameter on POST /api/jobs (iteration 12)."""
import os
import uuid
import time

import pytest
import requests


BASE_URL = os.environ.get(
    "TEST_BASE_URL", "https://joblink-track.preview.emergentagent.com"
).rstrip("/")
API = f"{BASE_URL}/api"

QA_EMPLOYER = {"email": "qa.employer@example.com", "password": "LabourLinkQA!2026"}
QA_WORKER = {"email": "qa.worker@example.com", "password": "LabourLinkQA!2026"}
PASSWORD = "StrongPass123!"

# MG Road Bangalore (qa.worker location)
MG_LAT, MG_LNG = 12.975, 77.606


def _h(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()["data"]
    return body["token"], body["user"]


def _register_worker(lat, lng):
    email = f"TEST_worker_{uuid.uuid4().hex[:10]}@example.com"
    r = requests.post(
        f"{API}/auth/register",
        json={"name": "TEST Radius Worker", "email": email, "password": PASSWORD, "role": "worker"},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    tok = r.json()["data"]["token"]
    r2 = requests.put(
        f"{API}/workers/profile",
        headers=_h(tok),
        json={"latitude": lat, "longitude": lng, "location": "TEST"},
        timeout=15,
    )
    assert r2.status_code == 200, r2.text
    return {"email": email, "token": tok}


def _post_job(token, extra=None, lat=MG_LAT, lng=MG_LNG):
    payload = {
        "title": f"TEST Radius {uuid.uuid4().hex[:6]}",
        "description": "radius test",
        "location": "Bengaluru",
        "latitude": lat,
        "longitude": lng,
        "wage": 800,
        "payment_type": "daily",
        "required_workers": 1,
        "job_date": "2026-02-10",
        "required_skills": "misc",
    }
    if extra:
        payload.update(extra)
    r = requests.post(f"{API}/jobs", headers=_h(token), json=payload, timeout=15)
    return r


@pytest.fixture(scope="module")
def employer_token():
    tok, _ = _login(QA_EMPLOYER["email"], QA_EMPLOYER["password"])
    return tok


# ---------- Response shape --------------------------------------------------

class TestResponseShape:
    def test_response_contains_notified_and_radius(self, employer_token):
        r = _post_job(employer_token, {"notify_radius_km": 25})
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert "notified_workers" in data, data
        assert "notify_radius_km" in data, data
        assert isinstance(data["notified_workers"], int)
        assert data["notify_radius_km"] == 25

    def test_default_radius_when_omitted(self, employer_token):
        r = _post_job(employer_token, extra=None)  # no notify_radius_km
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["notify_radius_km"] == 25

    def test_non_numeric_falls_back_to_default(self, employer_token):
        r = _post_job(employer_token, {"notify_radius_km": "abc"})
        assert r.status_code == 200, r.text
        assert r.json()["data"]["notify_radius_km"] == 25

    def test_null_falls_back_to_default(self, employer_token):
        r = _post_job(employer_token, {"notify_radius_km": None})
        assert r.status_code == 200, r.text
        assert r.json()["data"]["notify_radius_km"] == 25


# ---------- Clamping --------------------------------------------------------

class TestClamping:
    def test_upper_clamp(self, employer_token):
        r = _post_job(employer_token, {"notify_radius_km": 999})
        assert r.status_code == 200
        assert r.json()["data"]["notify_radius_km"] == 100

    def test_lower_clamp_zero(self, employer_token):
        r = _post_job(employer_token, {"notify_radius_km": 0})
        assert r.status_code == 200
        assert r.json()["data"]["notify_radius_km"] == 1

    def test_lower_clamp_negative(self, employer_token):
        r = _post_job(employer_token, {"notify_radius_km": -50})
        assert r.status_code == 200
        assert r.json()["data"]["notify_radius_km"] == 1

    def test_fractional_kept(self, employer_token):
        r = _post_job(employer_token, {"notify_radius_km": 12.5})
        assert r.status_code == 200
        assert r.json()["data"]["notify_radius_km"] == 12.5


# ---------- Radius affects notified_workers ---------------------------------

class TestRadiusEffect:
    """Register a worker ~36 km away and verify radius=5 excludes, radius=50 includes."""

    @pytest.fixture(scope="class")
    def far_worker(self):
        # ~36 km north of MG Road
        return _register_worker(13.30, 77.606)

    def test_small_radius_excludes_far(self, employer_token, far_worker):
        # Post job at MG road; only include this single far worker + any near ones.
        # We measure the "far_worker" specifically by checking their notifications list.
        # Use small radius: near workers may or may not exist, but far worker must NOT be included.
        r = _post_job(employer_token, {"notify_radius_km": 5, "job_date": "2026-02-11"})
        assert r.status_code == 200
        job = r.json()["data"]
        assert job["notify_radius_km"] == 5
        # Verify the far worker did NOT get a "New job nearby" notification for this job title
        time.sleep(0.4)
        notes = requests.get(f"{API}/notifications", headers=_h(far_worker["token"]), timeout=15).json()["data"]
        assert not any(job["title"] in (n.get("message") or "") for n in notes), \
            "far worker should NOT be notified with radius=5"

    def test_large_radius_includes_far(self, employer_token, far_worker):
        r = _post_job(employer_token, {"notify_radius_km": 50, "job_date": "2026-02-12"})
        assert r.status_code == 200
        job = r.json()["data"]
        assert job["notify_radius_km"] == 50
        time.sleep(0.5)
        notes = requests.get(f"{API}/notifications", headers=_h(far_worker["token"]), timeout=15).json()["data"]
        assert any(job["title"] in (n.get("message") or "") for n in notes), \
            "far worker (~36km) should be notified with radius=50"
        # notified_workers should be >= 1
        assert job["notified_workers"] >= 1
