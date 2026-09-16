from datetime import datetime
from flask import current_app
from extensions import db, socketio
from models import Application, LocationShare, Job
from services.algorithms import haversine


def assigned_to_job(job_id, worker_id):
    return Application.query.filter(
        Application.job_id == job_id,
        Application.worker_id == worker_id,
        Application.status.in_(["Accepted", "Assigned", "Ongoing", "Completed"]),
    ).first()


def upsert_share(job_id, worker_id, lat, lng, accuracy=None, active=True):
    if lat is None or lng is None:
        raise ValueError("Latitude and longitude are required")
    lat = float(lat)
    lng = float(lng)
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise ValueError("Invalid coordinates")

    share = LocationShare.query.filter_by(job_id=job_id, worker_id=worker_id).first()
    if not share:
        share = LocationShare(job_id=job_id, worker_id=worker_id)
        db.session.add(share)
    share.latitude = lat
    share.longitude = lng
    share.accuracy = accuracy
    share.is_active = active
    share.updated_at = datetime.utcnow()
    db.session.flush()
    payload = {
        "job_id": job_id,
        "worker_id": worker_id,
        "latitude": lat,
        "longitude": lng,
        "accuracy": accuracy,
        "is_active": active,
        "updated_at": share.updated_at.isoformat(),
    }
    try:
        socketio.emit("location:update", payload, to=f"job_{job_id}")
    except Exception:
        current_app.logger.warning("Location emit failed", exc_info=True)
    return payload


def job_distance(job: Job, lat, lng):
    return haversine(lat, lng, job.latitude, job.longitude)
