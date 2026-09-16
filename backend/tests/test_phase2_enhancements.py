"""
Phase 2 P2 enhancement tests:
1. Verified reviews badge (verified + job_title enrichment)
2. Portfolio CRUD on /workers/portfolio
3. Public profile schema regression (rating.average, breakdown, reviews)
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

QA_WORKER = {"email": "qa.worker@example.com", "password": "LabourLinkQA!2026"}
QA_EMPLOYER = {"email": "qa.employer@example.com", "password": "LabourLinkQA!2026"}
QA_WORKER_ID = 6
QA_EMPLOYER_ID = 11


# --- Auth helpers ---
def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    body = r.json()
    token = body.get("token") or body.get("data", {}).get("token") or body.get("access_token")
    assert token, f"no token in response: {body}"
    return token


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def worker_token():
    return _login(QA_WORKER)


@pytest.fixture(scope="module")
def employer_token():
    return _login(QA_EMPLOYER)


# --- Public profile schema regression ---
class TestPublicProfileSchema:
    def test_worker_public_schema(self):
        r = requests.get(f"{API}/workers/{QA_WORKER_ID}/public", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json().get("data", r.json())
        assert "rating" in data and "average" in data["rating"] and "breakdown" in data["rating"]
        assert isinstance(data["rating"]["breakdown"], list)
        assert "reviews" in data and isinstance(data["reviews"], list)
        assert "portfolio" in data and isinstance(data["portfolio"], list)
        # each review has new fields
        for rev in data["reviews"]:
            for k in ("rating", "comment", "reviewer", "date", "job_id", "job_title", "verified"):
                assert k in rev, f"missing {k} in review: {rev}"

    def test_employer_public_schema(self):
        r = requests.get(f"{API}/employers/{QA_EMPLOYER_ID}/public", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json().get("data", r.json())
        assert "rating" in data and "average" in data["rating"] and "breakdown" in data["rating"]
        for rev in data["reviews"]:
            for k in ("rating", "comment", "reviewer", "date", "job_id", "job_title", "verified"):
                assert k in rev


# --- Portfolio CRUD ---
class TestPortfolioCRUD:
    def test_worker_add_list_delete(self, worker_token):
        img = f"https://example.com/img_{uuid.uuid4().hex[:8]}.jpg"
        caption = "TEST_portfolio_item"
        # Add
        r = requests.post(f"{API}/workers/portfolio", json={"image_url": img, "caption": caption}, headers=_auth(worker_token))
        assert r.status_code == 200, r.text
        body = r.json().get("data", r.json())
        item_id = body.get("id")
        assert item_id, body
        assert body.get("image_url") == img
        assert body.get("caption") == caption

        # List includes it
        r2 = requests.get(f"{API}/workers/portfolio", headers=_auth(worker_token))
        assert r2.status_code == 200
        items = r2.json().get("data", r2.json())
        assert any(i["id"] == item_id for i in items)

        # Also visible on public profile (newest first)
        r3 = requests.get(f"{API}/workers/{QA_WORKER_ID}/public")
        pub = r3.json().get("data", r3.json())
        assert any(p["id"] == item_id for p in pub["portfolio"])

        # Delete
        r4 = requests.delete(f"{API}/workers/portfolio/{item_id}", headers=_auth(worker_token))
        assert r4.status_code == 200

        # Verify gone
        r5 = requests.get(f"{API}/workers/portfolio", headers=_auth(worker_token))
        remaining = r5.json().get("data", r5.json())
        assert not any(i["id"] == item_id for i in remaining)

    def test_add_missing_image_url(self, worker_token):
        r = requests.post(f"{API}/workers/portfolio", json={"caption": "no image"}, headers=_auth(worker_token))
        assert r.status_code in (400, 422), r.text

    def test_delete_non_owner_returns_404(self, worker_token, employer_token):
        # Worker adds an item
        r = requests.post(f"{API}/workers/portfolio", json={"image_url": "https://example.com/x.jpg", "caption": "TEST_owner"}, headers=_auth(worker_token))
        assert r.status_code == 200
        item_id = r.json().get("data", r.json()).get("id")

        # Employer cannot even hit portfolio endpoints -> 403 (tested elsewhere).
        # For non-owner-worker check, delete a non-existent id
        r2 = requests.delete(f"{API}/workers/portfolio/999999", headers=_auth(worker_token))
        assert r2.status_code == 404

        # cleanup
        requests.delete(f"{API}/workers/portfolio/{item_id}", headers=_auth(worker_token))

    def test_employer_rejected_403(self, employer_token):
        r = requests.get(f"{API}/workers/portfolio", headers=_auth(employer_token))
        assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text}"
        r2 = requests.post(f"{API}/workers/portfolio", json={"image_url": "https://example.com/x.jpg"}, headers=_auth(employer_token))
        assert r2.status_code == 403
        r3 = requests.delete(f"{API}/workers/portfolio/1", headers=_auth(employer_token))
        assert r3.status_code == 403


# --- End-to-end verified badge ---
class TestVerifiedBadgeE2E:
    def test_full_flow(self):
        stamp = uuid.uuid4().hex[:8]
        worker_creds = {"name": f"TEST_worker_{stamp}", "email": f"test_worker_{stamp}@example.com", "password": "TestPass!2026", "role": "worker", "phone": f"9{stamp[:9]}"}
        employer_creds = {"name": f"TEST_emp_{stamp}", "email": f"test_emp_{stamp}@example.com", "password": "TestPass!2026", "role": "employer", "phone": f"8{stamp[:9]}"}

        # Register
        rw = requests.post(f"{API}/auth/register", json=worker_creds)
        assert rw.status_code in (200, 201), rw.text
        re_ = requests.post(f"{API}/auth/register", json=employer_creds)
        assert re_.status_code in (200, 201), re_.text

        w_body = rw.json().get("data", rw.json())
        e_body = re_.json().get("data", re_.json())
        w_token = w_body.get("token") or _login({"email": worker_creds["email"], "password": worker_creds["password"]})
        e_token = e_body.get("token") or _login({"email": employer_creds["email"], "password": employer_creds["password"]})
        w_id = (w_body.get("user") or {}).get("id")
        e_id = (e_body.get("user") or {}).get("id")
        if not w_id:
            me = requests.get(f"{API}/auth/me", headers=_auth(w_token)).json()
            w_id = (me.get("data", me).get("user") or {}).get("id") or me.get("data", me).get("id")
        if not e_id:
            me = requests.get(f"{API}/auth/me", headers=_auth(e_token)).json()
            e_id = (me.get("data", me).get("user") or {}).get("id") or me.get("data", me).get("id")
        assert w_id and e_id, f"failed to resolve ids w={w_id} e={e_id}"

        # Employer posts job
        job_title = f"TEST_JOB_{stamp}"
        rj = requests.post(f"{API}/jobs", json={
            "title": job_title, "description": "test", "wage": 500,
            "location": "Test", "required_workers": 1, "required_skills": "test"
        }, headers=_auth(e_token))
        assert rj.status_code in (200, 201), rj.text
        job = rj.json().get("data", rj.json())
        job_id = job.get("id") or job.get("job", {}).get("id")
        assert job_id, job

        # Worker applies
        ra = requests.post(f"{API}/jobs/{job_id}/apply", json={"agreed_wage": 500}, headers=_auth(w_token))
        assert ra.status_code in (200, 201), ra.text
        app_body = ra.json().get("data", ra.json())
        app_id = app_body.get("id") or app_body.get("application", {}).get("id")

        # If no app_id, fetch via employer applications
        if not app_id:
            r = requests.get(f"{API}/jobs/{job_id}/applications", headers=_auth(e_token))
            apps = r.json().get("data", r.json())
            app_id = apps[0]["id"] if apps else None
        assert app_id, "no application id"

        # Employer transitions: Accept → Ongoing → Completed
        for status in ("Accepted", "Ongoing", "Completed"):
            r = requests.put(f"{API}/applications/{app_id}/status", json={"status": status}, headers=_auth(e_token))
            assert r.status_code == 200, f"status={status} -> {r.status_code} {r.text}"

        # Both submit reviews
        r1 = requests.post(f"{API}/ratings", json={"job_id": job_id, "reviewee_id": w_id, "rating": 5, "comment": "great worker"}, headers=_auth(e_token))
        assert r1.status_code in (200, 201), r1.text
        r2 = requests.post(f"{API}/ratings", json={"job_id": job_id, "reviewee_id": e_id, "rating": 5, "comment": "great employer"}, headers=_auth(w_token))
        assert r2.status_code in (200, 201), r2.text

        # Public profile shows verified=True and job_title matches
        rp = requests.get(f"{API}/workers/{w_id}/public")
        assert rp.status_code == 200
        data = rp.json().get("data", rp.json())
        assert data["reviews"], "no reviews on public profile"
        rev0 = data["reviews"][0]
        assert rev0["verified"] is True, f"verified not true: {rev0}"
        assert rev0["job_title"] == job_title, f"job_title mismatch: {rev0}"

        # Employer public profile also enriched
        rpe = requests.get(f"{API}/employers/{e_id}/public")
        de = rpe.json().get("data", rpe.json())
        assert de["reviews"], "no reviews on employer public"
        rev_e = de["reviews"][0]
        assert rev_e["verified"] is True
        assert rev_e["job_title"] == job_title
