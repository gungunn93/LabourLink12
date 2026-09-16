from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from extensions import db
from models import Job, LocationShare, WorkerProfile
from services.location_service import assigned_to_job, upsert_share
from utils.responses import ok, err
from utils.authz import current_user, role_required
from utils.serialize import safe_iso

location_bp = Blueprint("location", __name__)


def _employer_owns(job, user):
    return job and user and job.employer_id == user.id


@location_bp.post("/jobs/<int:jid>/location/start")
@role_required("worker")
def start_share(jid):
    job = db.session.get(Job, jid)
    if not job:
        return err("Job not found", 404)
    if not assigned_to_job(jid, current_user().id):
        return err("Location sharing is only allowed for an assigned job", 403)
    data = request.get_json(silent=True) or {}
    try:
        payload = upsert_share(jid, current_user().id, data.get("latitude"), data.get("longitude"), data.get("accuracy"), True)
    except ValueError as exc:
        return err(str(exc))
    profile = WorkerProfile.query.filter_by(user_id=current_user().id).first()
    if profile:
        profile.latitude = payload["latitude"]
        profile.longitude = payload["longitude"]
    db.session.commit()
    return ok(payload, "Location sharing started")


@location_bp.post("/jobs/<int:jid>/location/update")
@role_required("worker")
def update_share(jid):
    share = LocationShare.query.filter_by(job_id=jid, worker_id=current_user().id).first()
    if not share or not share.is_active:
        return err("Start location sharing first", 403)
    if not assigned_to_job(jid, current_user().id):
        return err("Not authorized", 403)
    data = request.get_json(silent=True) or {}
    try:
        payload = upsert_share(jid, current_user().id, data.get("latitude"), data.get("longitude"), data.get("accuracy"), True)
    except ValueError as exc:
        return err(str(exc))
    profile = WorkerProfile.query.filter_by(user_id=current_user().id).first()
    if profile:
        profile.latitude = payload["latitude"]
        profile.longitude = payload["longitude"]
    db.session.commit()
    return ok(payload, "Location updated")


@location_bp.post("/jobs/<int:jid>/location/stop")
@role_required("worker")
def stop_share(jid):
    share = LocationShare.query.filter_by(job_id=jid, worker_id=current_user().id).first()
    if not share:
        return err("No active location session", 404)
    share.is_active = False
    db.session.commit()
    return ok({"job_id": jid, "is_active": False}, "Location sharing stopped")


@location_bp.get("/jobs/<int:jid>/location")
@jwt_required()
def get_location(jid):
    job = db.session.get(Job, jid)
    if not job:
        return err("Job not found", 404)
    user = current_user()
    worker_id = request.args.get("worker_id", type=int)
    if user.role == "worker":
        worker_id = user.id
        if not assigned_to_job(jid, user.id):
            return err("Access denied", 403)
    elif user.role == "employer":
        if not _employer_owns(job, user):
            return err("Access denied", 403)
        if not worker_id:
            share = LocationShare.query.filter_by(job_id=jid, is_active=True).first()
            if not share:
                return ok({"is_active": False}, "Worker is not sharing location")
            worker_id = share.worker_id
        if not assigned_to_job(jid, worker_id):
            return err("Worker is not assigned to this job", 403)
    elif user.role != "admin":
        return err("Access denied", 403)

    share = LocationShare.query.filter_by(job_id=jid, worker_id=worker_id).first()
    if not share:
        return ok({"is_active": False}, "No location available")
    return ok(
        {
            "job_id": jid,
            "worker_id": worker_id,
            "latitude": share.latitude,
            "longitude": share.longitude,
            "accuracy": share.accuracy,
            "is_active": share.is_active,
            "updated_at": safe_iso(share.updated_at),
            "job_latitude": job.latitude,
            "job_longitude": job.longitude,
        }
    )
