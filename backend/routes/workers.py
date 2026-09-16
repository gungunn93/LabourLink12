from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from extensions import db
from models import WorkerProfile, Wallet, WalletTransaction, Application, Job, RatingReview, User, WorkerPortfolio, WorkerAvailability
from services.algorithms import match_score
from utils.responses import ok, err
from utils.authz import current_user, role_required
from utils.serialize import user_json, job_json, safe_iso

workers_bp = Blueprint("workers", __name__)


ISO_DATE_LEN = 10  # YYYY-MM-DD


def _valid_iso_date(value):
    if not isinstance(value, str) or len(value) != ISO_DATE_LEN:
        return False
    try:
        from datetime import date
        date.fromisoformat(value)
        return True
    except Exception:
        return False


def _availability_for(worker_id):
    rows = WorkerAvailability.query.filter_by(worker_id=worker_id).all()
    return sorted(
        [{"date": r.day, "available": bool(r.available)} for r in rows if r.day and len(r.day) == ISO_DATE_LEN],
        key=lambda x: x["date"],
    )


def _rating_breakdown(user_id):
    reviews = RatingReview.query.filter_by(reviewee_id=user_id).order_by(RatingReview.created_at.desc()).all()
    breakdown = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    total = 0
    for review in reviews:
        key = max(1, min(5, int(review.rating or 0)))
        breakdown[key] += 1
        total += review.rating or 0
    count = len(reviews)
    average = round(total / count, 2) if count else 0
    return reviews, {
        "average": average,
        "count": count,
        "breakdown": [{"stars": stars, "count": breakdown[stars]} for stars in (5, 4, 3, 2, 1)],
    }


def _serialize_reviews(reviews):
    output = []
    for review in reviews:
        reviewer = db.session.get(User, review.reviewer_id)
        job = db.session.get(Job, review.job_id) if review.job_id else None
        application = None
        if job and review.job_id:
            application = Application.query.filter_by(job_id=review.job_id, worker_id=review.reviewee_id).first()
            if not application:
                application = Application.query.filter_by(job_id=review.job_id, worker_id=review.reviewer_id).first()
        verified = bool(application and application.status == "Completed")
        output.append(
            {
                "rating": review.rating,
                "comment": review.comment,
                "reviewer": reviewer.name if reviewer else "User",
                "date": safe_iso(review.created_at),
                "job_id": review.job_id,
                "job_title": job.title if job else None,
                "verified": verified,
            }
        )
    return output

PROFILE_FIELDS = [
    "skills", "experience", "location", "latitude", "longitude", "availability",
    "preferred_area", "languages", "photo", "document",
]


@workers_bp.get("/workers/profile")
@role_required("worker")
def profile():
    user = current_user()
    profile = WorkerProfile.query.filter_by(user_id=user.id).first()
    wallet = Wallet.query.filter_by(worker_id=user.id).first()
    profile_data = {c.name: getattr(profile, c.name) for c in profile.__table__.columns} if profile else {}
    reviews = RatingReview.query.filter_by(reviewee_id=user.id).order_by(RatingReview.created_at.desc()).all()
    return ok(
        {
            "user": user_json(user),
            "profile": profile_data,
            "reviews": [{"rating": r.rating, "comment": r.comment, "reviewer": (db.session.get(User, r.reviewer_id).name if db.session.get(User, r.reviewer_id) else "User"), "date": safe_iso(r.created_at)} for r in reviews],
            "wallet": {
                "balance": wallet.balance if wallet else 0,
                "total_earnings": wallet.total_earnings if wallet else 0,
                "pending": wallet.pending if wallet else 0,
            },
        }
    )


@workers_bp.put("/workers/profile")
@role_required("worker")
def update_profile():
    profile = WorkerProfile.query.filter_by(user_id=current_user().id).first()
    if not profile:
        profile = WorkerProfile(user_id=current_user().id)
        db.session.add(profile)
    data = request.get_json(silent=True) or {}
    if "name" in data:
        current_user().name = data["name"]
    for field in PROFILE_FIELDS:
        if field in data:
            setattr(profile, field, data[field])
    db.session.commit()
    return ok({}, "Profile updated")


@workers_bp.get("/workers/jobs")
@role_required("worker")
def recommended():
    profile = WorkerProfile.query.filter_by(user_id=current_user().id).first()
    if not profile:
        return err("Worker profile not found", 404)
    jobs = Job.query.filter_by(status="Open").all()
    scored = []
    for job in jobs:
        try:
            score, _ = match_score(profile, job)
        except Exception:
            score = 0
        scored.append((score, job))
    scored.sort(key=lambda item: item[0], reverse=True)
    return ok([job_json(job, current_user()) | {"match_score": score} for score, job in scored])


@workers_bp.get("/workers/applications")
@role_required("worker")
def apps():
    applications = Application.query.filter_by(worker_id=current_user().id).order_by(Application.applied_at.desc()).all()
    result = []
    for application in applications:
        job = db.session.get(Job, application.job_id)
        result.append(
            {
                "id": application.id,
                "job": job_json(job) if job else {},
                "status": application.status,
                "agreed_wage": application.agreed_wage,
                "applied_at": safe_iso(application.applied_at),
            }
        )
    return ok(result)


@workers_bp.get("/workers/assigned")
@role_required("worker")
def assigned():
    applications = Application.query.filter(
        Application.worker_id == current_user().id,
        Application.status.in_(["Accepted", "Assigned", "Ongoing", "Completed"]),
    ).all()
    return ok(
        [
            {
                "id": a.id,
                "status": a.status,
                "agreed_wage": a.agreed_wage,
                "job": job_json(db.session.get(Job, a.job_id), current_user()),
            }
            for a in applications
        ]
    )


@workers_bp.get("/workers/earnings")
@role_required("worker")
def earnings():
    wallet = Wallet.query.filter_by(worker_id=current_user().id).first()
    if not wallet:
        return ok({"wallet": {"balance": 0, "total_earnings": 0, "pending": 0}, "transactions": []})
    transactions = WalletTransaction.query.filter_by(wallet_id=wallet.id).order_by(WalletTransaction.created_at.desc()).all()
    return ok(
        {
            "wallet": {"balance": wallet.balance, "total_earnings": wallet.total_earnings, "pending": wallet.pending},
            "transactions": [
                {"amount": t.amount, "kind": t.kind, "description": t.description, "date": safe_iso(t.created_at)}
                for t in transactions
            ],
        }
    )


@workers_bp.get("/workers/<int:uid>/public")
def public_worker_profile(uid):
    user = db.session.get(User, uid)
    if not user or user.role != "worker":
        return err("Worker not found", 404)
    profile = WorkerProfile.query.filter_by(user_id=uid).first()
    reviews, rating = _rating_breakdown(uid)
    completed = Application.query.filter_by(worker_id=uid, status="Completed").count()
    portfolio = WorkerPortfolio.query.filter_by(worker_id=uid).order_by(WorkerPortfolio.created_at.desc()).all()
    return ok(
        {
            "user": {"id": user.id, "name": user.name, "role": user.role},
            "profile": {
                "skills": (profile.skills if profile else "") or "",
                "experience": (profile.experience if profile else 0) or 0,
                "location": (profile.location if profile else "") or "",
                "availability": (profile.availability if profile else "") or "",
                "languages": (profile.languages if profile else "") or "",
                "photo": (profile.photo if profile else None),
                "completed_jobs": (profile.completed_jobs if profile else 0) or completed,
            },
            "rating": rating,
            "reviews": _serialize_reviews(reviews),
            "portfolio": [
                {"id": item.id, "image_url": item.image_url, "caption": item.caption or "", "date": safe_iso(item.created_at)}
                for item in portfolio
            ],
            "availability_days": _availability_for(uid),
        }
    )


@workers_bp.get("/workers/portfolio")
@role_required("worker")
def list_portfolio():
    items = WorkerPortfolio.query.filter_by(worker_id=current_user().id).order_by(WorkerPortfolio.created_at.desc()).all()
    return ok([{"id": i.id, "image_url": i.image_url, "caption": i.caption or "", "date": safe_iso(i.created_at)} for i in items])


@workers_bp.post("/workers/portfolio")
@role_required("worker")
def add_portfolio():
    data = request.get_json(silent=True) or {}
    image_url = (data.get("image_url") or "").strip()
    if not image_url:
        return err("image_url is required")
    item = WorkerPortfolio(worker_id=current_user().id, image_url=image_url, caption=(data.get("caption") or "").strip())
    db.session.add(item)
    db.session.commit()
    return ok({"id": item.id, "image_url": item.image_url, "caption": item.caption, "date": safe_iso(item.created_at)}, "Added")


@workers_bp.delete("/workers/portfolio/<int:pid>")
@role_required("worker")
def delete_portfolio(pid):
    item = db.session.get(WorkerPortfolio, pid)
    if not item or item.worker_id != current_user().id:
        return err("Portfolio item not found", 404)
    db.session.delete(item)
    db.session.commit()
    return ok({}, "Deleted")


@workers_bp.get("/workers/availability")
@role_required("worker")
def my_availability():
    return ok(_availability_for(current_user().id))


@workers_bp.put("/workers/availability")
@role_required("worker")
def update_availability():
    data = request.get_json(silent=True) or {}
    entries = data.get("days") or []
    if not isinstance(entries, list):
        return err("days must be a list")
    worker_id = current_user().id
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        d = entry.get("date")
        if not _valid_iso_date(d):
            continue
        available = bool(entry.get("available"))
        row = WorkerAvailability.query.filter_by(worker_id=worker_id, day=d).first()
        if entry.get("remove"):
            if row:
                db.session.delete(row)
            continue
        if row:
            row.available = available
        else:
            db.session.add(WorkerAvailability(worker_id=worker_id, day=d, available=available))
    db.session.commit()
    return ok(_availability_for(worker_id), "Availability updated")


@workers_bp.get("/workers/<int:uid>/availability")
def public_availability(uid):
    user = db.session.get(User, uid)
    if not user or user.role != "worker":
        return err("Worker not found", 404)
    return ok(_availability_for(uid))
