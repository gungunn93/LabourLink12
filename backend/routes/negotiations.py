from datetime import datetime, timedelta
from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from extensions import db
from models import Negotiation, NegotiationMessage, Job, User, Application, WorkerProfile, JobCategory
from services.algorithms import fair_wage
from services.notifications import notify
from utils.responses import ok, err
from utils.authz import current_user
from utils.serialize import safe_iso, user_json, job_json

negotiations_bp = Blueprint("negotiations", __name__)


def _can_access(neg, user):
    return user and user.id in (neg.worker_id, neg.employer_id) or (user and user.role == "admin")


def _serialize(neg, include_messages=False):
    job = db.session.get(Job, neg.job_id)
    data = {
        "id": neg.id,
        "job_id": neg.job_id,
        "job": job_json(job) if job else {},
        "employer_id": neg.employer_id,
        "worker_id": neg.worker_id,
        "original_price": neg.original_price,
        "current_offer": neg.current_offer,
        "previous_offer": neg.previous_offer,
        "last_offer_by": neg.last_offer_by,
        "offer_sender": neg.last_offer_by,
        "offer_receiver": neg.worker_id if neg.last_offer_by == neg.employer_id else neg.employer_id,
        "suggested_wage": neg.suggested_wage,
        "status": neg.status,
        "expires_at": safe_iso(neg.expires_at),
        "updated_at": safe_iso(neg.updated_at),
        "employer": user_json(db.session.get(User, neg.employer_id)),
        "worker": user_json(db.session.get(User, neg.worker_id)),
    }
    if include_messages:
        messages = (
            NegotiationMessage.query.filter_by(negotiation_id=neg.id)
            .order_by(NegotiationMessage.created_at)
            .all()
        )
        data["messages"] = [
            {
                "sender_id": m.sender_id,
                "offer": m.offer,
                "message": m.message,
                "action": m.action,
                "date": safe_iso(m.created_at),
            }
            for m in messages
        ]
        data["history"] = data["messages"]
    return data


def _expire_if_needed(neg):
    if neg.expires_at and datetime.utcnow() > neg.expires_at and neg.status in ("Pending", "Countered"):
        neg.status = "Expired"
    return neg


@negotiations_bp.get("/negotiations")
@jwt_required()
def list_negotiations():
    user = current_user()
    q = Negotiation.query
    if user.role == "worker":
        q = q.filter_by(worker_id=user.id)
    elif user.role == "employer":
        q = q.filter_by(employer_id=user.id)
    items = q.order_by(Negotiation.updated_at.desc()).all()
    return ok([_serialize(_expire_if_needed(n)) for n in items])


@negotiations_bp.post("/negotiations")
@jwt_required()
def create_negotiation():
    data = request.get_json(silent=True) or {}
    job = db.session.get(Job, data.get("job_id"))
    if not job:
        return err("Job not found", 404)
    if not job.is_negotiable:
        return err("This job does not allow negotiation")
    user = current_user()
    worker_id = user.id if user.role == "worker" else data.get("worker_id")
    if not worker_id:
        return err("Worker ID is required")
    if user.role == "employer" and job.employer_id != user.id:
        return err("Forbidden", 403)
    if user.role == "worker" and user.id != int(worker_id):
        return err("Forbidden", 403)

    existing = Negotiation.query.filter_by(job_id=job.id, worker_id=worker_id).first()
    if existing:
        return ok(_serialize(_expire_if_needed(existing), True), "Negotiation already exists")

    try:
        offer = float(data.get("offer", job.wage or 0))
    except (TypeError, ValueError):
        return err("Offer must be a valid number")
    if offer <= 0:
        return err("Offer must be greater than zero")

    profile = WorkerProfile.query.filter_by(user_id=worker_id).first()
    category = db.session.get(JobCategory, job.category_id)
    suggested = fair_wage(category.name if category else "Other", profile.experience if profile else 0, job.duration, job.location, job.wage)
    neg = Negotiation(
        job_id=job.id,
        employer_id=job.employer_id,
        worker_id=worker_id,
        original_price=job.wage,
        current_offer=offer,
        previous_offer=None,
        last_offer_by=user.id,
        suggested_wage=suggested,
        status="Pending",
        expires_at=datetime.utcnow() + timedelta(hours=48),
    )
    db.session.add(neg)
    db.session.flush()
    db.session.add(
        NegotiationMessage(
            negotiation_id=neg.id,
            sender_id=user.id,
            offer=offer,
            message=data.get("message") or "Initial offer",
            action="offer",
        )
    )
    recipient = job.employer_id if user.role == "worker" else worker_id
    notify(recipient, "New negotiation offer", f"Offer ₹{offer:.0f} for {job.title}", "negotiation")
    db.session.commit()
    return ok(_serialize(neg, True), "Negotiation started")


@negotiations_bp.get("/negotiations/<int:nid>")
@jwt_required()
def get_negotiation(nid):
    neg = db.session.get(Negotiation, nid)
    if not neg:
        return err("Negotiation not found", 404)
    if not _can_access(neg, current_user()):
        return err("Access denied", 403)
    return ok(_serialize(_expire_if_needed(neg), True))


@negotiations_bp.post("/negotiations/<int:nid>/offer")
@jwt_required()
def counter_offer(nid):
    neg = db.session.get(Negotiation, nid)
    if not neg:
        return err("Negotiation not found", 404)
    user = current_user()
    if not _can_access(neg, user):
        return err("Access denied", 403)
    _expire_if_needed(neg)
    if neg.status not in ("Pending", "Countered"):
        return err(f"Negotiation is {neg.status} and cannot be updated")
    data = request.get_json(silent=True) or {}
    try:
        offer = float(data.get("offer"))
    except (TypeError, ValueError):
        return err("Offer amount is required")
    if offer <= 0:
        return err("Offer must be greater than zero")
    if neg.last_offer_by == user.id:
        return err("Wait for the other party to respond before sending another offer")
    neg.previous_offer = neg.current_offer
    neg.current_offer = offer
    neg.last_offer_by = user.id
    neg.status = "Countered"
    neg.expires_at = datetime.utcnow() + timedelta(hours=48)
    db.session.add(
        NegotiationMessage(
            negotiation_id=neg.id,
            sender_id=user.id,
            offer=offer,
            message=data.get("message") or "Counter offer",
            action="counter",
        )
    )
    recipient = neg.worker_id if user.id == neg.employer_id else neg.employer_id
    job = db.session.get(Job, neg.job_id)
    notify(recipient, "Counter offer", f"New offer ₹{offer:.0f} for {job.title if job else 'job'}", "negotiation")
    db.session.commit()
    return ok(_serialize(neg, True), "Counter offer sent")


@negotiations_bp.put("/negotiations/<int:nid>/accept")
@jwt_required()
def accept(nid):
    neg = db.session.get(Negotiation, nid)
    if not neg:
        return err("Negotiation not found", 404)
    user = current_user()
    if not _can_access(neg, user):
        return err("Access denied", 403)
    if neg.status not in ("Pending", "Countered"):
        return err(f"Negotiation is {neg.status}")
    if neg.last_offer_by == user.id:
        return err("You cannot accept your own offer")
    neg.status = "Accepted"
    job = db.session.get(Job, neg.job_id)
    if job:
        job.agreed_wage = neg.current_offer
    application = Application.query.filter_by(job_id=neg.job_id, worker_id=neg.worker_id).first()
    if application:
        application.agreed_wage = neg.current_offer
    db.session.add(
        NegotiationMessage(
            negotiation_id=neg.id,
            sender_id=user.id,
            offer=neg.current_offer,
            message="Offer accepted",
            action="accept",
        )
    )
    recipient = neg.worker_id if user.id == neg.employer_id else neg.employer_id
    notify(recipient, "Negotiation accepted", f"Offer ₹{neg.current_offer:.0f} accepted", "negotiation")
    db.session.commit()
    return ok(_serialize(neg, True), "Negotiation accepted")


@negotiations_bp.put("/negotiations/<int:nid>/reject")
@jwt_required()
def reject(nid):
    neg = db.session.get(Negotiation, nid)
    if not neg:
        return err("Negotiation not found", 404)
    user = current_user()
    if not _can_access(neg, user):
        return err("Access denied", 403)
    if neg.status not in ("Pending", "Countered"):
        return err(f"Negotiation is {neg.status}")
    neg.status = "Rejected"
    db.session.add(
        NegotiationMessage(
            negotiation_id=neg.id,
            sender_id=user.id,
            offer=neg.current_offer,
            message="Offer rejected",
            action="reject",
        )
    )
    db.session.commit()
    return ok(_serialize(neg, True), "Negotiation rejected")
