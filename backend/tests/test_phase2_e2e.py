"""Phase 2 backend regression + E2E tests.

Covers new public profile endpoints and marketplace regression flow using
freshly registered isolated QA users (email prefixed `TEST_`).
"""
import os
import uuid
import time

import pytest
import requests


BASE_URL = os.environ.get("TEST_BASE_URL", "https://joblink-track.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
PASSWORD = "StrongPass123!"


# --- helpers -----------------------------------------------------------------

def _register(role, name):
    email = f"TEST_{role}_{uuid.uuid4().hex[:10]}@example.com"
    r = requests.post(f"{API}/auth/register", json={"name": name, "email": email, "password": PASSWORD, "role": role}, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()["data"]
    return {"email": email, "token": body["token"], "user": body["user"]}


def _h(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# --- module fixtures ---------------------------------------------------------

@pytest.fixture(scope="module")
def actors():
    worker = _register("worker", "TEST Worker E2E")
    employer = _register("employer", "TEST Employer E2E")
    return {"worker": worker, "employer": employer}


@pytest.fixture(scope="module")
def flow(actors):
    """Run the full marketplace flow once and reuse results."""
    emp = actors["employer"]
    wrk = actors["worker"]

    # Employer posts job
    job_payload = {
        "title": "TEST Delivery Helper",
        "description": "E2E automated job",
        "location": "Bengaluru",
        "wage": 500,
        "payment_type": "daily",
        "required_workers": 1,
        "required_skills": "delivery",
        "is_negotiable": True,
    }
    r = requests.post(f"{API}/jobs", json=job_payload, headers=_h(emp["token"]), timeout=15)
    assert r.status_code == 200, r.text
    job = r.json()["data"]
    job_id = job["id"]

    # Worker applies
    r = requests.post(f"{API}/jobs/{job_id}/apply", json={"note": "I can do it"}, headers=_h(wrk["token"]), timeout=15)
    assert r.status_code == 200, r.text

    # Employer fetches applications
    r = requests.get(f"{API}/applications", headers=_h(emp["token"]), timeout=15)
    assert r.status_code == 200
    apps = [a for a in r.json()["data"] if a["job"]["id"] == job_id]
    assert apps, "employer should see the application"
    app_id = apps[0]["id"]

    # Accept -> Ongoing -> Completed
    for status in ("Accepted", "Ongoing", "Completed"):
        r = requests.put(f"{API}/applications/{app_id}/status", json={"status": status}, headers=_h(emp["token"]), timeout=15)
        assert r.status_code == 200, f"{status}: {r.text}"

    return {"job_id": job_id, "application_id": app_id}


# --- Public profile endpoints -----------------------------------------------

class TestPublicProfiles:
    def test_worker_public_profile_shape(self, actors):
        uid = actors["worker"]["user"]["id"]
        r = requests.get(f"{API}/workers/{uid}/public", timeout=10)
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["user"]["id"] == uid
        assert d["user"]["role"] == "worker"
        for key in ("skills", "experience", "location", "availability", "languages", "completed_jobs"):
            assert key in d["profile"], f"missing profile.{key}"
        assert d["rating"]["average"] == 0
        assert d["rating"]["count"] == 0
        assert [b["stars"] for b in d["rating"]["breakdown"]] == [5, 4, 3, 2, 1]
        assert d["reviews"] == []

    def test_employer_public_profile_shape(self, actors):
        uid = actors["employer"]["user"]["id"]
        r = requests.get(f"{API}/employers/{uid}/public", timeout=10)
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["user"]["role"] == "employer"
        for key in ("company_name", "about", "employer_type", "jobs_posted", "workers_hired", "location"):
            assert key in d["profile"], f"missing profile.{key}"
        assert "breakdown" in d["rating"]

    def test_worker_public_404_for_employer_id(self, actors):
        emp_id = actors["employer"]["user"]["id"]
        r = requests.get(f"{API}/workers/{emp_id}/public", timeout=10)
        assert r.status_code == 404

    def test_employer_public_404_for_worker_id(self, actors):
        w_id = actors["worker"]["user"]["id"]
        r = requests.get(f"{API}/employers/{w_id}/public", timeout=10)
        assert r.status_code == 404

    def test_public_endpoints_no_auth_required(self, actors):
        uid = actors["worker"]["user"]["id"]
        r = requests.get(f"{API}/workers/{uid}/public", headers={}, timeout=10)
        assert r.status_code == 200


# --- End to end marketplace flow --------------------------------------------

class TestMarketplaceE2E:
    def test_flow_and_reviews_reflect_in_public_profile(self, actors, flow):
        emp = actors["employer"]
        wrk = actors["worker"]
        job_id = flow["job_id"]

        # Employer reviews worker
        r = requests.post(f"{API}/ratings", json={
            "job_id": job_id,
            "reviewee_id": wrk["user"]["id"],
            "rating": 5,
            "comment": "Excellent worker",
        }, headers=_h(emp["token"]), timeout=15)
        assert r.status_code == 200, r.text

        # Worker reviews employer
        r = requests.post(f"{API}/ratings", json={
            "job_id": job_id,
            "reviewee_id": emp["user"]["id"],
            "rating": 4,
            "comment": "Good employer",
        }, headers=_h(wrk["token"]), timeout=15)
        assert r.status_code == 200, r.text

        # Public worker profile reflects 5-star review
        r = requests.get(f"{API}/workers/{wrk['user']['id']}/public", timeout=10)
        d = r.json()["data"]
        assert d["rating"]["count"] == 1
        assert d["rating"]["average"] == 5.0
        five = next(b for b in d["rating"]["breakdown"] if b["stars"] == 5)
        assert five["count"] == 1
        assert any(rv["rating"] == 5 for rv in d["reviews"])

        # Public employer profile reflects 4-star review
        r = requests.get(f"{API}/employers/{emp['user']['id']}/public", timeout=10)
        d = r.json()["data"]
        assert d["rating"]["count"] == 1
        assert d["rating"]["average"] == 4.0

    def test_rating_rejected_before_completion(self, actors):
        # Create fresh job + application still in Pending to verify guard
        emp = actors["employer"]
        wrk = actors["worker"]
        r = requests.post(f"{API}/jobs", json={"title": "TEST Guard Job", "wage": 100, "location": "X"}, headers=_h(emp["token"]), timeout=15)
        job_id = r.json()["data"]["id"]
        r = requests.post(f"{API}/jobs/{job_id}/apply", json={}, headers=_h(wrk["token"]), timeout=15)
        assert r.status_code == 200
        r = requests.post(f"{API}/ratings", json={
            "job_id": job_id, "reviewee_id": wrk["user"]["id"], "rating": 5,
        }, headers=_h(emp["token"]), timeout=15)
        assert r.status_code == 403


# --- Regression: negotiation, chat, notifications, payments -----------------

class TestRegression:
    def test_health(self):
        r = requests.get(f"{API}/health", timeout=10)
        assert r.status_code == 200
        assert r.json()["data"]["status"] == "running"

    def test_notifications_present_after_flow(self, actors, flow):
        wrk = actors["worker"]
        r = requests.get(f"{API}/notifications", headers=_h(wrk["token"]), timeout=10)
        assert r.status_code == 200
        items = r.json()["data"]
        titles = " ".join(n["title"] for n in items)
        assert "Application accepted" in titles or "Job assigned" in titles
        assert any(n["kind"] == "job" for n in items)

    def test_conversation_and_message(self, actors, flow):
        emp = actors["employer"]
        wrk = actors["worker"]
        r = requests.post(f"{API}/conversations", json={"job_id": flow["job_id"], "worker_id": wrk["user"]["id"]}, headers=_h(emp["token"]), timeout=10)
        assert r.status_code == 200, r.text
        cid = r.json()["data"]["id"]
        r = requests.post(f"{API}/conversations/{cid}/messages", json={"text": "TEST hello"}, headers=_h(emp["token"]), timeout=10)
        assert r.status_code == 200
        r = requests.get(f"{API}/conversations/{cid}/messages", headers=_h(wrk["token"]), timeout=10)
        assert r.status_code == 200
        assert any(m["text"] == "TEST hello" for m in r.json()["data"])

    def test_negotiation_flow_agreed_wage(self, actors):
        # Fresh job for negotiation
        emp = actors["employer"]
        wrk = actors["worker"]
        r = requests.post(f"{API}/jobs", json={"title": "TEST Neg Job", "wage": 400, "location": "X", "is_negotiable": True}, headers=_h(emp["token"]), timeout=10)
        job_id = r.json()["data"]["id"]
        # Worker must apply first (application must exist to store agreed_wage)
        requests.post(f"{API}/jobs/{job_id}/apply", json={}, headers=_h(wrk["token"]), timeout=10)
        # Worker initiates offer
        r = requests.post(f"{API}/negotiations", json={"job_id": job_id, "offer": 550}, headers=_h(wrk["token"]), timeout=10)
        assert r.status_code == 200, r.text
        nid = r.json()["data"]["id"]
        # Employer counters
        r = requests.post(f"{API}/negotiations/{nid}/offer", json={"offer": 500}, headers=_h(emp["token"]), timeout=10)
        assert r.status_code == 200, r.text
        # Worker accepts
        r = requests.put(f"{API}/negotiations/{nid}/accept", json={}, headers=_h(wrk["token"]), timeout=10)
        assert r.status_code == 200, r.text
        assert r.json()["data"]["status"] == "Accepted"
        # Verify agreed_wage on application
        r = requests.get(f"{API}/applications", headers=_h(wrk["token"]), timeout=10)
        matches = [a for a in r.json()["data"] if a["job"]["id"] == job_id]
        assert matches and matches[0]["agreed_wage"] == 500

    def test_payments_order_creation_and_signature_rejection(self, actors, flow):
        # Note: after flow test, application/job is Completed. Payment/create allows Completed
        # but we need to ensure Payment doesn't already exist. So run on a NEW job.
        emp = actors["employer"]
        wrk = actors["worker"]
        r = requests.post(f"{API}/jobs", json={"title": "TEST Pay Job", "wage": 300, "location": "X"}, headers=_h(emp["token"]), timeout=10)
        job_id = r.json()["data"]["id"]
        requests.post(f"{API}/jobs/{job_id}/apply", json={}, headers=_h(wrk["token"]), timeout=10)
        # Fetch application
        r = requests.get(f"{API}/applications", headers=_h(emp["token"]), timeout=10)
        app = next(a for a in r.json()["data"] if a["job"]["id"] == job_id)
        aid = app["id"]
        # Accept -> Ongoing -> Completed
        for s in ("Accepted", "Ongoing", "Completed"):
            requests.put(f"{API}/applications/{aid}/status", json={"status": s}, headers=_h(emp["token"]), timeout=10)

        # Order create
        r = requests.post(f"{API}/payments/create", json={"job_id": job_id, "worker_id": wrk["user"]["id"], "amount": 300}, headers=_h(emp["token"]), timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()["data"]
        assert d["gateway"] == "razorpay"
        assert d.get("order_id", "").startswith("order_")
        # Secret must not be exposed anywhere in response
        assert "secret" not in r.text.lower()

        # Tampered signature should be rejected
        r = requests.post(f"{API}/payments/confirm", json={
            "payment_id": d["id"],
            "razorpay_order_id": d["order_id"],
            "razorpay_payment_id": "pay_TEST",
            "razorpay_signature": "invalid_signature_12345",
        }, headers=_h(emp["token"]), timeout=15)
        assert r.status_code == 400
        assert "verification" in r.json().get("message", "").lower() or "failed" in r.json().get("message", "").lower()

    def test_payments_config_no_secret(self, actors):
        r = requests.get(f"{API}/payments/config", headers=_h(actors["employer"]["token"]), timeout=10)
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["mode"] == "razorpay"
        assert d["key_id"]
        assert "secret" not in " ".join(str(v) for v in d.values()).lower()

    def test_location_share_start_requires_assignment(self, actors):
        # Un-assigned job -> should reject
        emp = actors["employer"]
        wrk = actors["worker"]
        r = requests.post(f"{API}/jobs", json={"title": "TEST Loc Job", "wage": 100, "location": "X"}, headers=_h(emp["token"]), timeout=10)
        job_id = r.json()["data"]["id"]
        r = requests.post(f"{API}/jobs/{job_id}/location/start", json={"latitude": 12.9, "longitude": 77.6}, headers=_h(wrk["token"]), timeout=10)
        assert r.status_code == 403

    def test_location_share_start_when_assigned(self, actors, flow):
        # flow job was Completed which is still assigned status; start location share
        wrk = actors["worker"]
        job_id = flow["job_id"]
        r = requests.post(f"{API}/jobs/{job_id}/location/start", json={"latitude": 12.97, "longitude": 77.59, "accuracy": 5}, headers=_h(wrk["token"]), timeout=10)
        assert r.status_code == 200, r.text
        # Employer can fetch worker location
        emp = actors["employer"]
        r = requests.get(f"{API}/jobs/{job_id}/location?worker_id={wrk['user']['id']}", headers=_h(emp["token"]), timeout=10)
        assert r.status_code == 200
        assert r.json()["data"]["is_active"] is True
