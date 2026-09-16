from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import Application, Job, User, EmployerProfile, WorkerAvailability
from services.notifications import notify
from services.chat_service import get_or_create_conversation
from utils.responses import ok, err
from utils.authz import current_user, role_required
from utils.serialize import job_json, user_json, safe_iso

applications_bp = Blueprint("applications", __name__)


def _worker_availability_on(worker_id, iso_day):
    if not worker_id or not iso_day:
        return None
    row = WorkerAvailability.query.filter_by(worker_id=worker_id, day=iso_day).first()
    if not row:
        return None
    return bool(row.available)


def _serialize(application):
    job = db.session.get(Job, application.job_id)
    worker = db.session.get(User, application.worker_id)
    availability = _worker_availability_on(application.worker_id, job.job_date if job else None) if job and job.job_date else None
    return {
        "id": application.id,
        "job": job_json(job) if job else {},
        "worker": user_json(worker),
        "status": application.status,
        "note": application.note,
        "agreed_wage": application.agreed_wage,
        "applied_at": safe_iso(application.applied_at),
        "worker_availability": availability,  # true/false/null
        "availability_conflict": availability is False,
    }


@applications_bp.post("/jobs/<int:jid>/apply")
@role_required("worker")
def apply(jid):
    job = db.session.get(Job, jid)
    if not job:
        return err("Job not found", 404)
    if job.status not in ("Open",):
        return err("This job is not accepting applications")
    existing = Application.query.filter_by(job_id=jid, worker_id=current_user().id).first()
    if existing:
        return err("Already applied")
    data = request.get_json(silent=True) or {}
    application = Application(job_id=jid, worker_id=current_user().id, note=data.get("note"), status="Pending")
    db.session.add(application)
    notify(job.employer_id, "New application", f"{current_user().name} applied for {job.title}", "application")
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return err("Already applied")
    return ok({"id": application.id}, "Application submitted")


@applications_bp.get("/applications")
@jwt_required()
def applications():
    user = current_user()
    if not user:
        return err("User not found", 401)
    if user.role == "admin":
        records = Application.query.order_by(Application.applied_at.desc()).all()
    elif user.role == "employer":
        records = (
            Application.query.join(Job, Application.job_id == Job.id)
            .filter(Job.employer_id == user.id)
            .order_by(Application.applied_at.desc())
            .all()
        )
    else:
        records = Application.query.filter_by(worker_id=user.id).order_by(Application.applied_at.desc()).all()
    return ok([_serialize(item) for item in records])


@applications_bp.put("/applications/<int:aid>/status")
@jwt_required()
def app_status(aid):
    application = db.session.get(Application, aid)
    if not application:
        return err("Application not found", 404)
    user = current_user()
    job = db.session.get(Job, application.job_id)
    if not job:
        return err("Job not found", 404)
    if user.role == "employer" and job.employer_id != user.id:
        return err("Forbidden", 403)
    if user.role not in ("employer", "admin"):
        return err("Only the employer can change application status", 403)
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    allowed = {"Pending", "Accepted", "Rejected", "Assigned", "Ongoing", "Completed", "Cancelled"}
    if status not in allowed:
        return err("Invalid application status")
    application.status = status
    if status in ("Accepted", "Assigned"):
        application.agreed_wage = application.agreed_wage or job.agreed_wage or job.wage
        job.agreed_wage = application.agreed_wage
        if job.status == "Open":
            job.status = "Assigned"
        profile = EmployerProfile.query.filter_by(user_id=job.employer_id).first()
        if profile:
            profile.workers_hired = (profile.workers_hired or 0) + 1
        get_or_create_conversation(job.id, application.worker_id, job.employer_id)
        notify(application.worker_id, "Application accepted", f"You were selected for {job.title}", "application")
        notify(application.worker_id, "Job assigned", f"{job.title} is now assigned to you", "job")
    elif status == "Rejected":
        notify(application.worker_id, "Application rejected", f"Your application for {job.title} was rejected", "application")
    elif status == "Ongoing":
        job.status = "Ongoing"
        notify(application.worker_id, "Job started", f"{job.title} is now in progress", "job")
    elif status == "Completed":
        job.status = "Completed"
        notify(application.worker_id, "Job completed", f"{job.title} was marked complete", "job")
    db.session.commit()
    return ok(_serialize(application), "Application status updated")
