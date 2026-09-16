"""Backend tests for the nearest-worker notification pipeline on job creation.

Covers:
- Notification created for workers within 25 km (nearest first, cap 10)
- Workers marked busy for the job's date are skipped
- Workers with no lat/lng skipped
- Workers > 25 km skipped
- Job posted without lat/lng => no notifications, no crash
- /api/notifications returns newest-first
- Smoke: existing location tracking endpoints still respond
"""
import os
import uuid
import time

import pytest
import requests


BASE_URL = os.environ.get(
    "TEST_BASE_URL", "https://joblink-track.preview.emergentagent.com"
).rstrip("/")
API = f"{BASE_URL}/api"
PASSWORD = "StrongPass123!"

QA_EMPLOYER = {"email": "qa.employer@example.com", "password": "LabourLinkQA!2026"}
QA_WORKER = {"email": "qa.worker@example.com", "password": "LabourLinkQA!2026"}

# MG Road Bangalore ~= (12.975, 77.606)
JOB_LAT, JOB_LNG = 12.975, 77.606


# ---------- helpers ----------------------------------------------------------

def _h(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    body = r.json()["data"]
    return body["token"], body["user"]


def _register(role, name_prefix="TEST"):
    email = f"TEST_{role}_{uuid.uuid4().hex[:10]}@example.com"
    r = requests.post(
        f"{API}/auth/register",
        json={"name": f"{name_prefix} {role}", "email": email, "password": PASSWORD, "role": role},
        timeout=15,
    )
    assert r.status_code == 200, f"register failed: {r.text}"
    body = r.json()["data"]
    return {"email": email, "token": body["token"], "user": body["user"]}


def _update_worker_profile(token, lat, lng):
    r = requests.put(
        f"{API}/workers/profile",
        headers=_h(token),
        json={"latitude": lat, "longitude": lng, "location": "TEST Bangalore"},
        timeout=15,
    )
    assert r.status_code == 200, r.text


def _set_availability(token, day, available):
    r = requests.put(
        f"{API}/workers/availability",
        headers=_h(token),
        json={"days": [{"date": day, "available": available}]},
        timeout=15,
    )
    assert r.status_code == 200, r.text


def _list_notifications(token):
    r = requests.get(f"{API}/notifications", headers=_h(token), timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def _post_job(token, **overrides):
    payload = {
        "title": f"TEST Nearest Job {uuid.uuid4().hex[:6]}",
        "description": "Nearest-worker notify test",
        "location": "Bengaluru",
        "latitude": JOB_LAT,
        "longitude": JOB_LNG,
        "wage": 700,
        "payment_type": "daily",
        "required_workers": 1,
        "job_date": "2026-01-15",
        "required_skills": "delivery",
        "is_negotiable": True,
    }
    payload.update(overrides)
    r = requests.post(f"{API}/jobs", headers=_h(token), json=payload, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def _latest_new_job_nearby(token, since_id=0, job_title=None):
    items = _list_notifications(token)
    for item in items:
        if item.get("title") != "New job nearby":
            continue
        if item["id"] <= since_id:
            continue
        if job_title and job_title not in (item.get("message") or ""):
            continue
        return item
    return None


# ---------- fixtures ---------------------------------------------------------

@pytest.fixture(scope="module")
def employer():
    token, user = _login(QA_EMPLOYER["email"], QA_EMPLOYER["password"])
    return {"token": token, "user": user}


@pytest.fixture(scope="module")
def qa_worker():
    token, user = _login(QA_WORKER["email"], QA_WORKER["password"])
    return {"token": token, "user": user}


@pytest.fixture(scope="module")
def near_worker():
    """~1.7 km from MG Road."""
    w = _register("worker")
    _update_worker_profile(w["token"], 12.99, 77.60)
    return w


@pytest.fixture(scope="module")
def mid_worker():
    """~5 km from MG Road."""
    w = _register("worker")
    _update_worker_profile(w["token"], 12.98, 77.65)
    return w


@pytest.fixture(scope="module")
def far_worker():
    """~36 km outside 25 km radius."""
    w = _register("worker")
    _update_worker_profile(w["token"], 13.30, 77.60)
    return w


@pytest.fixture(scope="module")
def no_geo_worker():
    """Worker without lat/lng saved."""
    w = _register("worker")
    # explicitly leave lat/lng None (skip PUT)
    return w


@pytest.fixture(scope="module")
def busy_worker():
    """Near worker but marked busy on the job date."""
    w = _register("worker")
    _update_worker_profile(w["token"], 12.985, 77.61)
    _set_availability(w["token"], "2026-01-20", False)
    return w


# ---------- tests ------------------------------------------------------------


class TestNearestNotifications:
    def test_near_worker_gets_notification(self, employer, near_worker):
        before = _list_notifications(near_worker["token"])
        last_id = max([n["id"] for n in before], default=0)
        job = _post_job(employer["token"])
        time.sleep(0.5)
        note = _latest_new_job_nearby(near_worker["token"], since_id=last_id, job_title=job["title"])
        assert note is not None, "near worker did not receive 'New job nearby' notification"
        assert note["kind"] == "job"
        assert "km" in (note.get("message") or "").lower()
        # message should include the job title & wage
        msg = note["message"]
        assert job["title"] in msg
        assert "700" in msg

    def test_qa_worker_gets_notification(self, employer, qa_worker):
        before = _list_notifications(qa_worker["token"])
        last_id = max([n["id"] for n in before], default=0)
        job = _post_job(employer["token"], job_date="2026-01-15")
        time.sleep(0.5)
        note = _latest_new_job_nearby(qa_worker["token"], since_id=last_id, job_title=job["title"])
        assert note is not None, "seeded qa.worker did not receive notification"

    def test_far_worker_not_notified(self, employer, far_worker):
        before = _list_notifications(far_worker["token"])
        last_id = max([n["id"] for n in before], default=0)
        job = _post_job(employer["token"])
        time.sleep(0.5)
        note = _latest_new_job_nearby(far_worker["token"], since_id=last_id, job_title=job["title"])
        assert note is None, "far worker (>25km) should not be notified"

    def test_no_geo_worker_not_notified(self, employer, no_geo_worker):
        before = _list_notifications(no_geo_worker["token"])
        last_id = max([n["id"] for n in before], default=0)
        job = _post_job(employer["token"])
        time.sleep(0.5)
        note = _latest_new_job_nearby(no_geo_worker["token"], since_id=last_id, job_title=job["title"])
        assert note is None, "worker without lat/lng should not be notified"

    def test_busy_worker_skipped_for_that_date(self, employer, busy_worker):
        before = _list_notifications(busy_worker["token"])
        last_id = max([n["id"] for n in before], default=0)
        job = _post_job(employer["token"], job_date="2026-01-20")
        time.sleep(0.5)
        note = _latest_new_job_nearby(busy_worker["token"], since_id=last_id, job_title=job["title"])
        assert note is None, "worker marked busy on job_date should be skipped"

    def test_busy_worker_notified_on_other_date(self, employer, busy_worker):
        before = _list_notifications(busy_worker["token"])
        last_id = max([n["id"] for n in before], default=0)
        job = _post_job(employer["token"], job_date="2026-01-21")
        time.sleep(0.5)
        note = _latest_new_job_nearby(busy_worker["token"], since_id=last_id, job_title=job["title"])
        assert note is not None, "busy on 01-20 but should receive on 01-21"

    def test_job_without_latlng_no_notification(self, employer, near_worker):
        before = _list_notifications(near_worker["token"])
        last_id = max([n["id"] for n in before], default=0)
        # explicitly omit lat/lng
        payload = {
            "title": f"TEST NoGeo Job {uuid.uuid4().hex[:6]}",
            "description": "No lat/lng",
            "location": "Bengaluru",
            "wage": 500,
            "payment_type": "daily",
            "required_workers": 1,
            "job_date": "2026-01-15",
            "required_skills": "delivery",
        }
        r = requests.post(f"{API}/jobs", headers=_h(employer["token"]), json=payload, timeout=15)
        assert r.status_code == 200, r.text
        job = r.json()["data"]
        time.sleep(0.5)
        note = _latest_new_job_nearby(near_worker["token"], since_id=last_id, job_title=job["title"])
        assert note is None, "job without lat/lng must not trigger notifications"

    def test_notifications_newest_first(self, employer, near_worker):
        # post two jobs
        job1 = _post_job(employer["token"])
        time.sleep(0.4)
        job2 = _post_job(employer["token"])
        time.sleep(0.5)
        items = _list_notifications(near_worker["token"])
        # created_at sorted desc → ids also desc
        ids = [n["id"] for n in items]
        assert ids == sorted(ids, reverse=True), "notifications not sorted newest-first"
        # find both
        titles_in_msgs = [n.get("message") or "" for n in items[:10]]
        assert any(job2["title"] in m for m in titles_in_msgs)
        assert any(job1["title"] in m for m in titles_in_msgs)

    def test_nearest_first_ordering_within_cap(self, employer, near_worker, mid_worker):
        """When both workers are within radius, the nearer worker gets notified
        before the mid-distance one (checked via notification id ordering)."""
        before_near = _list_notifications(near_worker["token"])
        before_mid = _list_notifications(mid_worker["token"])
        last_near = max([n["id"] for n in before_near], default=0)
        last_mid = max([n["id"] for n in before_mid], default=0)

        job = _post_job(employer["token"])
        time.sleep(0.6)

        n_near = _latest_new_job_nearby(near_worker["token"], since_id=last_near, job_title=job["title"])
        n_mid = _latest_new_job_nearby(mid_worker["token"], since_id=last_mid, job_title=job["title"])
        assert n_near is not None and n_mid is not None
        # notify() flushes each insert -> IDs are assigned in insertion order
        assert n_near["id"] < n_mid["id"], (
            f"nearest worker should be notified first: near_id={n_near['id']} mid_id={n_mid['id']}"
        )


class TestLocationSmoke:
    """Regression smoke: existing location endpoints still respond correctly."""

    def test_start_location_requires_assignment(self, employer, near_worker):
        # post a job (no assignment) and try to start sharing → expect 403
        job = _post_job(employer["token"])
        r = requests.post(
            f"{API}/jobs/{job['id']}/location/start",
            headers=_h(near_worker["token"]),
            json={"latitude": 12.99, "longitude": 77.60},
            timeout=15,
        )
        assert r.status_code == 403, r.text

    def test_get_location_ok_shape(self, employer, near_worker):
        job = _post_job(employer["token"])
        # employer viewing their own job → should return 200 with is_active:false
        r = requests.get(
            f"{API}/jobs/{job['id']}/location",
            headers=_h(employer["token"]),
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data.get("is_active") is False
