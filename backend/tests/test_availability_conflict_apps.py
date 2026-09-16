"""Backend tests for GET /api/applications availability enrichment."""
import os
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://joblink-track.preview.emergentagent.com").rstrip("/")
WORKER = {"email": "qa.worker@example.com", "password": "LabourLinkQA!2026"}
EMPLOYER = {"email": "qa.employer@example.com", "password": "LabourLinkQA!2026"}


def _login(creds):
    r = requests.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=20)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    body = r.json()
    tok = body.get("data", {}).get("token") or body.get("token") or body.get("access_token")
    assert tok, f"no token in {body}"
    return tok


def _apps(token):
    r = requests.get(f"{BASE_URL}/api/applications", headers={"Authorization": f"Bearer {token}"}, timeout=20)
    assert r.status_code == 200, r.text
    return r.json().get("data", [])


def test_employer_sees_availability_fields():
    tok = _login(EMPLOYER)
    apps = _apps(tok)
    assert len(apps) > 0
    for a in apps:
        assert "worker_availability" in a
        assert "availability_conflict" in a
        assert isinstance(a["availability_conflict"], bool)


def test_employer_only_sees_own_jobs():
    tok = _login(EMPLOYER)
    apps = _apps(tok)
    # All jobs must belong to employer id 11
    for a in apps:
        assert a["job"].get("employer_id") == 11, a


def test_qa_worker_sept5_available_and_sept8_busy():
    tok = _login(EMPLOYER)
    apps = _apps(tok)
    by_id = {a["id"]: a for a in apps}
    # Seeded: app 25 = Painting Sept 5 (available), app 26 = Cleaning Sept 8 (busy)
    assert 25 in by_id, f"app 25 missing among {list(by_id)}"
    assert 26 in by_id, f"app 26 missing among {list(by_id)}"
    a25 = by_id[25]
    a26 = by_id[26]
    assert a25["worker_availability"] is True, a25
    assert a25["availability_conflict"] is False, a25
    assert a26["worker_availability"] is False, a26
    assert a26["availability_conflict"] is True, a26


def test_worker_view_own_applications_have_fields():
    tok = _login(WORKER)
    apps = _apps(tok)
    assert len(apps) > 0
    for a in apps:
        assert a["worker"]["id"] == 6
        assert "worker_availability" in a
        assert "availability_conflict" in a


def test_no_job_date_yields_null_availability():
    # scan all applications; if any has no job_date, availability must be null and conflict False
    tok = _login(EMPLOYER)
    apps = _apps(tok)
    for a in apps:
        if not a["job"].get("job_date"):
            assert a["worker_availability"] is None, a
            assert a["availability_conflict"] is False, a
