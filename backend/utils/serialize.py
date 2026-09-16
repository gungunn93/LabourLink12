from extensions import db
from models import JobCategory, WorkerProfile
from services.algorithms import haversine


def safe_iso(value):
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def user_json(user, extra=None):
    if not user:
        return {}
    data = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
        "active": user.is_active,
    }
    if extra:
        data.update(extra)
    return data


def job_json(job, me=None):
    if not job:
        return {}
    category = db.session.get(JobCategory, job.category_id) if job.category_id else None
    distance = None
    if me and me.role == "worker":
        profile = WorkerProfile.query.filter_by(user_id=me.id).first()
        if (
            profile
            and profile.latitude is not None
            and profile.longitude is not None
            and job.latitude is not None
            and job.longitude is not None
        ):
            distance = haversine(profile.latitude, profile.longitude, job.latitude, job.longitude)
    return {
        "id": job.id,
        "title": job.title,
        "description": job.description,
        "image": job.image,
        "category": category.name if category else "Other",
        "category_id": job.category_id,
        "employer_id": job.employer_id,
        "location": job.location,
        "latitude": job.latitude,
        "longitude": job.longitude,
        "wage": job.wage,
        "agreed_wage": job.agreed_wage,
        "extra_amount": job.extra_amount or 0,
        "payable_amount": float(job.agreed_wage or job.wage or 0) + float(job.extra_amount or 0),
        "payment_type": job.payment_type,
        "required_workers": job.required_workers,
        "job_date": safe_iso(job.job_date),
        "start_time": safe_iso(job.start_time),
        "duration": job.duration,
        "deadline": safe_iso(job.deadline),
        "required_skills": job.required_skills,
        "experience_required": job.experience_required,
        "tools": job.tools,
        "is_negotiable": job.is_negotiable,
        "priority": job.priority,
        "status": job.status,
        "distance_km": round(distance, 2) if distance is not None else None,
        "created_at": safe_iso(job.created_at),
    }
