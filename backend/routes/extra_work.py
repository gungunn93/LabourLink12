from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from extensions import db
from models import ExtraWorkRequest, Job, Application
from services.location_service import assigned_to_job
from services.notifications import notify
from utils.responses import ok, err
from utils.authz import current_user, role_required
from utils.serialize import safe_iso

extra_bp = Blueprint("extra", __name__)


def _item(req):
    return {
        "id": req.id,
        "job_id": req.job_id,
        "worker_id": req.worker_id,
        "amount": req.amount,
        "reason": req.reason,
        "status": req.status,
        "created_at": safe_iso(req.created_at),
    }


@extra_bp.post("/jobs/<int:jid>/extra-requests")
@role_required("worker")
def create_request(jid):
    job = db.session.get(Job, jid)
    if not job:
        return err("Job not found", 404)
    if not assigned_to_job(jid, current_user().id):
        return err("Only assigned workers can request additional payment", 403)
    data = request.get_json(silent=True) or {}
    reason = str(data.get("reason") or "").strip()
    try:
        amount = float(data.get("amount"))
    except (TypeError, ValueError):
        return err("Additional amount is required")
    if amount <= 0:
        return err("Amount must be greater than zero")
    if len(reason) < 8:
        return err("Please describe why extra work is required")
    req = ExtraWorkRequest(job_id=jid, worker_id=current_user().id, amount=amount, reason=reason, status="Pending")
    db.session.add(req)
    notify(job.employer_id, "Additional payment request", f"{current_user().name} requested ₹{amount:.0f} extra for {job.title}", "extra")
    db.session.commit()
    return ok(_item(req), "Request submitted")


@extra_bp.get("/extra-requests")
@jwt_required()
def list_requests():
    user = current_user()
    q = ExtraWorkRequest.query
    if user.role == "worker":
        q = q.filter_by(worker_id=user.id)
    elif user.role == "employer":
        q = q.join(Job, ExtraWorkRequest.job_id == Job.id).filter(Job.employer_id == user.id)
    items = q.order_by(ExtraWorkRequest.created_at.desc()).all()
    return ok([_item(x) for x in items])


@extra_bp.put("/extra-requests/<int:rid>/status")
@role_required("employer", "admin")
def update_status(rid):
    req = db.session.get(ExtraWorkRequest, rid)
    if not req:
        return err("Request not found", 404)
    job = db.session.get(Job, req.job_id)
    if current_user().role == "employer" and job.employer_id != current_user().id:
        return err("Forbidden", 403)
    status = (request.get_json(silent=True) or {}).get("status")
    if status not in ("Accepted", "Rejected"):
        return err("Status must be Accepted or Rejected")
    if req.status != "Pending":
        return err("Request already processed")
    req.status = status
    if status == "Accepted":
        job.extra_amount = float(job.extra_amount or 0) + float(req.amount)
        notify(req.worker_id, "Extra payment approved", f"₹{req.amount:.0f} added to payable amount", "extra")
    else:
        notify(req.worker_id, "Extra payment rejected", "Your additional payment request was rejected", "extra")
    db.session.commit()
    return ok(_item(req), "Request updated")
