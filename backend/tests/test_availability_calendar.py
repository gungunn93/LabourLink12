"""
Availability Calendar feature tests
Covers:
- GET /workers/availability (worker JWT)
- PUT /workers/availability upsert + remove
- Invalid date silent-ignore
- Non-worker role rejection (403)
- Public GET /workers/<id>/availability
- Public profile availability_days key
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

QA_WORKER = {"email": "qa.worker@example.com", "password": "LabourLinkQA!2026"}
QA_EMPLOYER = {"email": "qa.employer@example.com", "password": "LabourLinkQA!2026"}
QA_WORKER_ID = 6
QA_EMPLOYER_ID = 11


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    body = r.json()
    token = body.get("token") or body.get("data", {}).get("token") or body.get("access_token")
    assert token
    return token


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


def _data(resp):
    j = resp.json()
    return j.get("data", j)


@pytest.fixture(scope="module")
def worker_token():
    return _login(QA_WORKER)


@pytest.fixture(scope="module")
def employer_token():
    return _login(QA_EMPLOYER)


@pytest.fixture(scope="module", autouse=True)
def restore_seed(worker_token):
    """After tests, restore the seed state: sep 2026 => 5,6,10 available; 8 busy."""
    yield
    # get current, remove all, then re-add seed
    r = requests.get(f"{API}/workers/availability", headers=_auth(worker_token), timeout=15)
    current = _data(r) or []
    removals = [{"date": d["date"], "remove": True} for d in current]
    if removals:
        requests.put(f"{API}/workers/availability", headers=_auth(worker_token),
                     json={"days": removals}, timeout=15)
    seed = [
        {"date": "2026-09-05", "available": True},
        {"date": "2026-09-06", "available": True},
        {"date": "2026-09-10", "available": True},
        {"date": "2026-09-08", "available": False},
    ]
    requests.put(f"{API}/workers/availability", headers=_auth(worker_token),
                 json={"days": seed}, timeout=15)


class TestAvailabilityGET:
    def test_get_my_availability_sorted(self, worker_token):
        r = requests.get(f"{API}/workers/availability", headers=_auth(worker_token), timeout=15)
        assert r.status_code == 200, r.text
        rows = _data(r)
        assert isinstance(rows, list)
        # sorted by date ascending
        dates = [row["date"] for row in rows]
        assert dates == sorted(dates), f"not sorted: {dates}"
        # each row has date + available
        for row in rows:
            assert "date" in row and "available" in row
            assert isinstance(row["available"], bool)

    def test_get_requires_auth(self):
        r = requests.get(f"{API}/workers/availability", timeout=15)
        assert r.status_code in (401, 422), r.text

    def test_get_rejects_employer(self, employer_token):
        r = requests.get(f"{API}/workers/availability", headers=_auth(employer_token), timeout=15)
        assert r.status_code == 403, r.text


class TestAvailabilityPUT:
    def test_put_upsert_and_remove(self, worker_token):
        payload = {"days": [
            {"date": "2026-09-15", "available": True},
            {"date": "2026-09-16", "available": False},
            {"date": "2026-09-15", "remove": True},  # removes the just-created
        ]}
        r = requests.put(f"{API}/workers/availability", headers=_auth(worker_token),
                         json=payload, timeout=15)
        assert r.status_code == 200, r.text
        rows = _data(r)
        dates = {row["date"]: row["available"] for row in rows}
        assert "2026-09-15" not in dates, f"remove failed: {dates}"
        assert dates.get("2026-09-16") is False

    def test_put_toggle_existing(self, worker_token):
        # flip 2026-09-05 from available=True to available=False
        r = requests.put(f"{API}/workers/availability", headers=_auth(worker_token),
                         json={"days": [{"date": "2026-09-05", "available": False}]}, timeout=15)
        assert r.status_code == 200
        rows = {row["date"]: row["available"] for row in _data(r)}
        assert rows.get("2026-09-05") is False
        # flip back
        r2 = requests.put(f"{API}/workers/availability", headers=_auth(worker_token),
                          json={"days": [{"date": "2026-09-05", "available": True}]}, timeout=15)
        rows2 = {row["date"]: row["available"] for row in _data(r2)}
        assert rows2.get("2026-09-05") is True

    def test_put_invalid_dates_silently_ignored(self, worker_token):
        before = _data(requests.get(f"{API}/workers/availability",
                                    headers=_auth(worker_token), timeout=15))
        r = requests.put(
            f"{API}/workers/availability",
            headers=_auth(worker_token),
            json={"days": [
                {"date": "not-a-date", "available": True},
                {"date": "", "available": True},
                {"date": "2026/09/05", "available": True},
                {"date": None, "available": True},
            ]},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        after = _data(r)
        # unchanged state
        assert sorted([(d["date"], d["available"]) for d in before]) == \
               sorted([(d["date"], d["available"]) for d in after])

    def test_put_rejects_employer(self, employer_token):
        r = requests.put(f"{API}/workers/availability", headers=_auth(employer_token),
                         json={"days": [{"date": "2026-09-20", "available": True}]}, timeout=15)
        assert r.status_code == 403, r.text


class TestPublicAvailability:
    def test_public_no_auth(self):
        r = requests.get(f"{API}/workers/{QA_WORKER_ID}/availability", timeout=15)
        assert r.status_code == 200, r.text
        rows = _data(r)
        assert isinstance(rows, list)
        assert all("date" in x and "available" in x for x in rows)

    def test_public_404_for_non_worker(self):
        r = requests.get(f"{API}/workers/{QA_EMPLOYER_ID}/availability", timeout=15)
        assert r.status_code == 404, r.text

    def test_public_404_for_missing_id(self):
        r = requests.get(f"{API}/workers/999999/availability", timeout=15)
        assert r.status_code == 404, r.text

    def test_public_profile_contains_availability_days(self):
        r = requests.get(f"{API}/workers/{QA_WORKER_ID}/public", timeout=15)
        assert r.status_code == 200, r.text
        data = _data(r)
        assert "availability_days" in data, f"missing key. keys={list(data.keys())}"
        assert isinstance(data["availability_days"], list)
        # existing keys not broken
        for k in ("user", "profile", "rating", "reviews", "portfolio"):
            assert k in data, f"regression: {k} missing"
