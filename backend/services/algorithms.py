from math import radians, sin, cos, asin, sqrt


def haversine(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None
    radius = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * radius * asin(sqrt(a))


def fair_wage(category, experience, duration, location, wage):
    base = max(500, float(wage or 500))
    exp = min(max(int(experience or 0), 0), 10) * 35
    dur = 0
    text = str(duration or "").lower()
    if "week" in text:
        dur = 250
    elif "hour" in text:
        dur = 0
    elif "day" in text:
        dur = 100
    category_bonus = {
        "plumbing": 180,
        "electrical": 200,
        "carpentry": 160,
        "masonry": 140,
        "painting": 120,
        "cleaning": 50,
        "construction": 130,
    }.get(str(category or "").lower(), 80)
    metro_bonus = 40 if location and any(x in location.lower() for x in ("mumbai", "delhi", "bangalore", "bengaluru", "hyderabad", "chennai", "pune")) else 0
    return round(base + exp + dur + category_bonus + metro_bonus, -1)


def match_score(worker, job):
    dist = haversine(worker.latitude, worker.longitude, job.latitude, job.longitude)
    loc = 100 if dist is None else max(0, 100 - (dist / 50) * 100)
    worker_skills = set(x.strip().lower() for x in (worker.skills or "").split(",") if x.strip())
    job_skills = set(x.strip().lower() for x in (job.required_skills or "").split(",") if x.strip())
    skill = 100 if not job_skills else (len(worker_skills & job_skills) / len(job_skills)) * 100
    required = max(1, int(job.experience_required or 0) or 1)
    exp = 100 if (worker.experience or 0) >= (job.experience_required or 0) else max(0, (worker.experience or 0) / required * 100)
    avail = 100 if str(worker.availability or "").lower() == "available" else 30
    wage = 100
    return round(0.35 * loc + 0.30 * skill + 0.15 * exp + 0.10 * avail + 0.10 * wage, 2), dist
