from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from extensions import db
from models import Job, JobCategory, Application, EmployerProfile, User, WorkerAvailability, WorkerProfile
from services.algorithms import match_score, haversine
from services.notifications import notify
from utils.responses import ok, err
from utils.authz import current_user, role_required, optional_user
from utils.serialize import job_json, user_json, safe_iso

jobs_bp = Blueprint("jobs", __name__)


@jobs_bp.get("/categories")
def categories():
    result = [{"id": c.id, "name": c.name} for c in JobCategory.query.order_by(JobCategory.name).all()]
    return ok(result)


@jobs_bp.get("/jobs")
def list_jobs():
    query = (request.args.get("q") or "").strip().lower()
    category = request.args.get("category")
    min_wage = request.args.get("min_wage", type=float)
    max_wage = request.args.get("max_wage", type=float)
    date_filter = (request.args.get("date") or "").strip() or None
    available_only = (request.args.get("available_only") or "").lower() in ("1", "true", "yes")
    sort = request.args.get("sort", "newest")
    me = optional_user()
    available_dates = None
    if available_only and me and me.role == "worker":
        rows = WorkerAvailability.query.filter_by(worker_id=me.id, available=True).all()
        available_dates = {r.day for r in rows if r.day}
    jobs = Job.query.filter(Job.status.in_(["Open", "Assigned", "Ongoing"])).all()
    result = []
    for job in jobs:
        item = job_json(job, me)
        hay = f"{job.title or ''} {job.description or ''} {job.required_skills or ''} {job.location or ''}".lower()
        if query and query not in hay:
            continue
        if category and str(job.category_id) != str(category) and str(item["category"]).lower() != str(category).lower():
            continue
        if min_wage is not None and float(job.wage or 0) < min_wage:
            continue
        if max_wage is not None and float(job.wage or 0) > max_wage:
            continue
        if date_filter and (job.job_date or "") != date_filter:
            continue
        if available_dates is not None and (job.job_date or "") not in available_dates:
            continue
        result.append(item)
    if sort == "wage":
        result.sort(key=lambda x: float(x["wage"] or 0), reverse=True)
    elif sort == "nearest":
        result.sort(key=lambda x: x["distance_km"] if x["distance_km"] is not None else 999999)
    else:
        result.sort(key=lambda x: x["created_at"] or "", reverse=True)
    return ok(result)


@jobs_bp.get("/jobs/<int:jid>")
def job_detail(jid):
    job = db.session.get(Job, jid)
    if not job:
        return err("Job not found", 404)
    employer = db.session.get(User, job.employer_id)
    employer_profile = EmployerProfile.query.filter_by(user_id=job.employer_id).first()
    me = optional_user()
    applied = False
    if me and me.role == "worker":
        applied = Application.query.filter_by(job_id=jid, worker_id=me.id).first() is not None
    return ok(
        {
            "job": job_json(job, me),
            "employer": user_json(employer),
            "employer_profile": {
                "company_name": employer_profile.company_name,
                "rating": employer_profile.rating,
                "location": employer_profile.location,
                "about": employer_profile.about,
            }
            if employer_profile
            else {},
            "already_applied": applied,
        }
    )


@jobs_bp.post("/jobs")
@role_required("employer")
def create_job():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return err("Job title is required")
    try:
        wage = float(data.get("wage", 0) or 0)
    except (TypeError, ValueError):
        return err("Wage must be a number")
    if wage <= 0:
        return err("Wage must be greater than zero")
    category_name = data.get("category") or "Other"
    category = JobCategory.query.filter_by(name=category_name).first()
    if not category:
        category = JobCategory(name=category_name)
        db.session.add(category)
        db.session.flush()
    job = Job(
        employer_id=current_user().id,
        category_id=category.id,
        title=title,
        description=data.get("description"),
        image=data.get("image"),
        location=data.get("location"),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        wage=wage,
        payment_type=data.get("payment_type", "daily"),
        required_workers=int(data.get("required_workers", 1) or 1),
        job_date=data.get("job_date"),
        start_time=data.get("start_time"),
        duration=data.get("duration"),
        deadline=data.get("deadline"),
        required_skills=data.get("required_skills", ""),
        experience_required=int(data.get("experience_required", 0) or 0),
        tools=data.get("tools"),
        is_negotiable=bool(data.get("is_negotiable", True)),
        priority=data.get("priority", "Normal"),
    )
    db.session.add(job)
    profile = EmployerProfile.query.filter_by(user_id=current_user().id).first()
    if profile:
        profile.jobs_posted = (profile.jobs_posted or 0) + 1
    db.session.commit()
    raw_radius = data.get("notify_radius_km")
    if raw_radius in (None, ""):
        radius = 25.0
    else:
        try:
            radius = float(raw_radius)
        except (TypeError, ValueError):
            radius = 25.0
    radius = max(1.0, min(radius, 100.0))
    notified = _notify_nearest_workers(job, radius_km=radius, limit=10)
    return ok({**job_json(job), "notified_workers": notified, "notify_radius_km": radius}, "Job posted")


def _notify_nearest_workers(job, radius_km=25, limit=10):
    """Notify workers close to the job's location. Skips workers marked Busy
    on the job's date (if job_date + availability rows exist).
    Returns the number of workers notified."""
    if job.latitude is None or job.longitude is None:
        return 0
    candidates = (
        db.session.query(WorkerProfile, User)
        .join(User, WorkerProfile.user_id == User.id)
        .filter(User.role == "worker", User.is_active == True)  # noqa: E712
        .filter(WorkerProfile.latitude.isnot(None), WorkerProfile.longitude.isnot(None))
        .all()
    )
    busy_workers = set()
    if job.job_date:
        rows = WorkerAvailability.query.filter_by(day=job.job_date, available=False).all()
        busy_workers = {r.worker_id for r in rows}
    scored = []
    for wp, wu in candidates:
        if wu.id in busy_workers:
            continue
        dist = haversine(wp.latitude, wp.longitude, job.latitude, job.longitude)
        if dist is None or dist > radius_km:
            continue
        scored.append((dist, wu.id))
    scored.sort(key=lambda x: x[0])
    count = 0
    for dist, worker_id in scored[:limit]:
        km = round(dist, 1)
        notify(
            worker_id,
            "New job nearby",
            f"{job.title} · ₹{int(job.wage)} · {km} km away in {job.location or 'nearby'}",
            "job",
        )
        count += 1
    if scored:
        db.session.commit()
    return count


@jobs_bp.put("/jobs/<int:jid>")
@role_required("employer")
def update_job(jid):
    job = db.session.get(Job, jid)
    if not job:
        return err("Job not found", 404)
    if job.employer_id != current_user().id:
        return err("Forbidden", 403)
    data = request.get_json(silent=True) or {}
    allowed = [
        "title", "description", "image", "location", "latitude", "longitude", "wage",
        "payment_type", "required_workers", "job_date", "start_time", "duration",
        "deadline", "required_skills", "experience_required", "tools", "is_negotiable",
        "priority", "status",
    ]
    for field in allowed:
        if field in data:
            setattr(job, field, data[field])
    db.session.commit()
    return ok(job_json(job), "Job updated")


@jobs_bp.delete("/jobs/<int:jid>")
@role_required("employer", "admin")
def delete_job(jid):
    job = db.session.get(Job, jid)
    if not job:
        return err("Job not found", 404)
    if current_user().role == "employer" and job.employer_id != current_user().id:
        return err("Forbidden", 403)
    job.status = "Disabled"
    db.session.commit()
    return ok({}, "Job disabled")


# ── Saved Jobs ────────────────────────────────────────────────────────────────
from models import SavedJob  # noqa: E402 (already imported above via models)


@jobs_bp.get("/jobs/saved")
@jwt_required()
def saved_jobs():
    user = current_user()
    saves = SavedJob.query.filter_by(user_id=user.id).order_by(SavedJob.created_at.desc()).all()
    result = []
    for s in saves:
        job = db.session.get(Job, s.job_id)
        if job:
            result.append(job_json(job, user))
    return ok(result)


@jobs_bp.post("/jobs/<int:jid>/save")
@jwt_required()
def save_job(jid):
    user = current_user()
    job = db.session.get(Job, jid)
    if not job:
        return err("Job not found", 404)
    existing = SavedJob.query.filter_by(user_id=user.id, job_id=jid).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return ok({"saved": False}, "Job removed from saved")
    db.session.add(SavedJob(user_id=user.id, job_id=jid))
    db.session.commit()
    return ok({"saved": True}, "Job saved")
