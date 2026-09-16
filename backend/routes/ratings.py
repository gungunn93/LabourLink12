from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from extensions import db
from models import RatingReview, User, WorkerProfile, EmployerProfile, Job, Application
from services.notifications import notify
from utils.responses import ok, err
from utils.authz import current_user
from utils.serialize import safe_iso
from sqlalchemy.exc import IntegrityError

ratings_bp = Blueprint("ratings", __name__)


@ratings_bp.post("/ratings")
@jwt_required()
def create_rating():
    data = request.get_json(silent=True) or {}
    if any(data.get(field) is None for field in ("job_id", "reviewee_id", "rating")):
        return err("Job ID, reviewee ID and rating are required")
    job = db.session.get(Job, data["job_id"])
    if not job:
        return err("Job not found", 404)
    user = current_user()
    if user.id == int(data["reviewee_id"]):
        return err("You cannot rate yourself")
    related_worker_id = data["reviewee_id"] if user.role == "employer" else user.id
    related = Application.query.filter_by(job_id=job.id, worker_id=related_worker_id).first()
    if not related or related.status != "Completed":
        return err("Reviews are available only after the job is completed", 403)
    if user.role == "employer" and job.employer_id != user.id:
        return err("Forbidden", 403)
    if user.role == "worker" and (not related or related.worker_id != user.id):
        return err("Forbidden", 403)
    if user.role == "employer" and int(data["reviewee_id"]) != related.worker_id:
        return err("You can only review the assigned worker", 403)
    if user.role == "worker" and int(data["reviewee_id"]) != job.employer_id:
        return err("You can only review the employer", 403)
    try:
        rating_value = max(1, min(5, int(data["rating"])))
    except (TypeError, ValueError):
        return err("Rating must be a number")
    review = RatingReview(
        job_id=data["job_id"],
        reviewer_id=user.id,
        reviewee_id=data["reviewee_id"],
        rating=rating_value,
        comment=data.get("comment") or "",
    )
    db.session.add(review)
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        return err("You already reviewed this user for this job")
    ratings_list = [item.rating for item in RatingReview.query.filter_by(reviewee_id=review.reviewee_id).all()]
    profile = WorkerProfile.query.filter_by(user_id=review.reviewee_id).first() or EmployerProfile.query.filter_by(user_id=review.reviewee_id).first()
    if profile and ratings_list:
        profile.rating = round(sum(ratings_list) / len(ratings_list), 2)
    notify(review.reviewee_id, "New review", f"You received a {rating_value}-star review", "review")
    db.session.commit()
    return ok({}, "Review submitted")


@ratings_bp.get("/ratings/<int:uid>")
def list_ratings(uid):
    reviews = RatingReview.query.filter_by(reviewee_id=uid).order_by(RatingReview.created_at.desc()).all()
    result = []
    for review in reviews:
        reviewer = db.session.get(User, review.reviewer_id)
        result.append(
            {
                "rating": review.rating,
                "comment": review.comment,
                "reviewer": reviewer.name if reviewer else "User",
                "date": safe_iso(review.created_at),
            }
        )
    return ok(result)


@ratings_bp.get("/ratings")
@jwt_required()
def ratings_by_job():
    """Get ratings for a specific job — used by frontend to check if already rated."""
    job_id = request.args.get("job_id", type=int)
    if not job_id:
        return err("job_id is required")
    user = current_user()
    ratings = RatingReview.query.filter_by(job_id=job_id).all()
    return ok([
        {
            "id": r.id,
            "reviewer_id": r.reviewer_id,
            "reviewee_id": r.reviewee_id,
            "rating": r.rating,
            "comment": r.comment,
            "date": safe_iso(r.created_at),
        }
        for r in ratings
    ])
