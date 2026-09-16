from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from extensions import db
from models import EmployerProfile, Job, RatingReview, User, Application
from utils.responses import ok, err
from utils.authz import current_user, role_required
from utils.serialize import user_json, job_json, safe_iso

employers_bp = Blueprint("employers", __name__)
FIELDS = ["company_name", "location", "latitude", "longitude", "about", "employer_type", "logo"]


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
            application = Application.query.filter_by(job_id=review.job_id, worker_id=review.reviewer_id).first()
            if not application:
                application = Application.query.filter_by(job_id=review.job_id, worker_id=review.reviewee_id).first()
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


@employers_bp.get("/employers/jobs")
@role_required("employer")
def jobs():
    jobs_list = Job.query.filter_by(employer_id=current_user().id).order_by(Job.created_at.desc()).all()
    return ok([job_json(job) for job in jobs_list])


@employers_bp.get("/employers/profile")
@role_required("employer")
def profile():
    user = current_user()
    profile = EmployerProfile.query.filter_by(user_id=user.id).first()
    profile_data = {c.name: getattr(profile, c.name) for c in profile.__table__.columns} if profile else {}
    reviews = RatingReview.query.filter_by(reviewee_id=user.id).order_by(RatingReview.created_at.desc()).all()
    return ok({"user": user_json(user), "profile": profile_data, "reviews": [{"rating": r.rating, "comment": r.comment, "reviewer": (db.session.get(User, r.reviewer_id).name if db.session.get(User, r.reviewer_id) else "User"), "date": r.created_at.isoformat() if r.created_at else None} for r in reviews]})


@employers_bp.put("/employers/profile")
@role_required("employer")
def update_profile():
    profile = EmployerProfile.query.filter_by(user_id=current_user().id).first()
    if not profile:
        profile = EmployerProfile(user_id=current_user().id)
        db.session.add(profile)
    data = request.get_json(silent=True) or {}
    if "name" in data:
        current_user().name = data["name"]
    for field in FIELDS:
        if field in data:
            setattr(profile, field, data[field])
    db.session.commit()
    return ok({}, "Profile updated")


@employers_bp.get("/employers/<int:uid>/public")
def public_employer_profile(uid):
    user = db.session.get(User, uid)
    if not user or user.role != "employer":
        return err("Employer not found", 404)
    profile = EmployerProfile.query.filter_by(user_id=uid).first()
    reviews, rating = _rating_breakdown(uid)
    jobs_posted = Job.query.filter_by(employer_id=uid).count()
    return ok(
        {
            "user": {"id": user.id, "name": user.name, "role": user.role},
            "profile": {
                "company_name": (profile.company_name if profile else "") or "",
                "location": (profile.location if profile else "") or "",
                "about": (profile.about if profile else "") or "",
                "employer_type": (profile.employer_type if profile else "") or "",
                "logo": (profile.logo if profile else None),
                "jobs_posted": (profile.jobs_posted if profile else 0) or jobs_posted,
                "workers_hired": (profile.workers_hired if profile else 0) or 0,
            },
            "rating": rating,
            "reviews": _serialize_reviews(reviews),
        }
    )
