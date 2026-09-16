"""Tests for /api/jobs date + available_only filters (iteration 9)."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://joblink-track.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

WORKER = {"email": "qa.worker@example.com", "password": "LabourLinkQA!2026"}
EMPLOYER = {"email": "qa.employer@example.com", "password": "LabourLinkQA!2026"}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=20)
    assert r.status_code == 200, r.text
    body = r.json()
    tok = (body.get("data") or {}).get("token") or body.get("token")
    assert tok, body
    return tok


@pytest.fixture(scope="module")
def worker_headers():
    return {"Authorization": f"Bearer {_login(WORKER)}"}


@pytest.fixture(scope="module")
def employer_headers():
    return {"Authorization": f"Bearer {_login(EMPLOYER)}"}


def _jobs(params=None, headers=None):
    r = requests.get(f"{API}/jobs", params=params or {}, headers=headers or {}, timeout=20)
    assert r.status_code == 200, r.text
    return r.json().get("data") or []


# Regression: baseline
def test_jobs_no_filter_returns_all_open_like():
    data = _jobs()
    assert isinstance(data, list)
    assert len(data) >= 3
    for j in data:
        assert j["status"] in ("Open", "Assigned", "Ongoing")


# Date filter
def test_jobs_date_filter_sept_5():
    data = _jobs({"date": "2026-09-05"})
    assert len(data) >= 1
    for j in data:
        assert j.get("job_date") == "2026-09-05"


def test_jobs_date_filter_no_match():
    data = _jobs({"date": "1999-01-01"})
    assert data == []


# available_only with worker JWT
def test_jobs_available_only_worker(worker_headers):
    data = _jobs({"available_only": "true"}, headers=worker_headers)
    dates = {j.get("job_date") for j in data}
    # Worker available Sept 5,6,10; busy Sept 8
    assert "2026-09-08" not in dates
    assert None not in dates
    # Should include Sept 5 and Sept 10
    assert "2026-09-05" in dates
    assert "2026-09-10" in dates


# available_only anonymous is no-op
def test_jobs_available_only_anonymous_is_noop():
    all_jobs = _jobs()
    anon = _jobs({"available_only": "true"})
    assert len(anon) == len(all_jobs)


# available_only employer is no-op
def test_jobs_available_only_employer_is_noop(employer_headers):
    all_jobs = _jobs(headers=employer_headers)
    filtered = _jobs({"available_only": "true"}, headers=employer_headers)
    assert len(filtered) == len(all_jobs)


# combination with q/category/available_only
def test_jobs_combined_filters(worker_headers):
    data = _jobs(
        {"available_only": "true", "q": "paint", "date": "2026-09-05"},
        headers=worker_headers,
    )
    for j in data:
        assert j.get("job_date") == "2026-09-05"
        hay = f"{j.get('title','')} {j.get('description','')} {j.get('required_skills','')}".lower()
        assert "paint" in hay


# regression: q, category, min_wage, max_wage, sort
def test_jobs_query_filter():
    data = _jobs({"q": "cleaning"})
    for j in data:
        hay = f"{j.get('title','')} {j.get('description','')}".lower()
        assert "cleaning" in hay


def test_jobs_sort_wage():
    data = _jobs({"sort": "wage"})
    wages = [float(j.get("wage") or 0) for j in data]
    assert wages == sorted(wages, reverse=True)


def test_jobs_min_max_wage():
    data = _jobs({"min_wage": 100, "max_wage": 100000})
    for j in data:
        w = float(j.get("wage") or 0)
        assert 100 <= w <= 100000
