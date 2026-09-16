from flask import Blueprint, request
from extensions import db
from models import User, Job, Payment, Report, AdminLog, Application, ExtraWorkRequest
from services.notifications import notify
from utils.responses import ok, err
from utils.authz import role_required, current_user
from utils.serialize import user_json, job_json, safe_iso

admin_bp = Blueprint("admin", __name__)


@admin_bp.get("/admin/dashboard")
@role_required("admin")
def dashboard():
    paid = Payment.query.filter_by(status="Paid").all()
    return ok(
        {
            "users": User.query.count(),
            "workers": User.query.filter_by(role="worker").count(),
            "employers": User.query.filter_by(role="employer").count(),
            "jobs": Job.query.count(),
            "active_jobs": Job.query.filter_by(status="Open").count(),
            "assigned_jobs": Job.query.filter(Job.status.in_(["Assigned", "Ongoing"])).count(),
            "completed_jobs": Job.query.filter_by(status="Completed").count(),
            "applications": Application.query.count(),
            "pending_applications": Application.query.filter_by(status="Pending").count(),
            "transactions": Payment.query.count(),
            "revenue": sum(float(p.amount or 0) for p in paid),
            "platform_fees": sum(float(p.platform_fee or 0) for p in paid),
            "open_reports": Report.query.filter_by(status="Open").count(),
        }
    )


@admin_bp.get("/admin/users")
@role_required("admin")
def users():
    role = request.args.get("role")
    q = User.query
    if role:
        q = q.filter_by(role=role)
    users = q.order_by(User.created_at.desc()).all()
    return ok(
        [
            user_json(user)
                | {"created_at": safe_iso(user.created_at)}
            for user in users
        ]
    )


@admin_bp.put("/admin/users/<int:uid>/status")
@role_required("admin")
def user_status(uid):
    user = db.session.get(User, uid)
    if not user:
        return err("User not found", 404)
    if user.role == "admin":
        return err("Cannot change admin status")
    data = request.get_json(silent=True) or {}
    user.is_active = bool(data.get("active", True))
    db.session.add(AdminLog(admin_id=current_user().id, action=f"Changed user {uid} active={user.is_active}"))
    db.session.commit()
    return ok({}, "User status updated")


@admin_bp.get("/admin/jobs")
@role_required("admin")
def jobs():
    return ok([job_json(job) for job in Job.query.order_by(Job.created_at.desc()).all()])


@admin_bp.get("/admin/applications")
@role_required("admin")
def applications():
    items = Application.query.order_by(Application.applied_at.desc()).all()
    return ok(
        [
            {
                "id": a.id,
                "job_id": a.job_id,
                "worker_id": a.worker_id,
                "status": a.status,
                "applied_at": safe_iso(a.applied_at),
            }
            for a in items
        ]
    )


@admin_bp.get("/admin/payments")
@role_required("admin")
def payments():
    return ok(
        [
            {
                "id": p.id,
                "job_id": p.job_id,
                "employer_id": p.employer_id,
                "worker_id": p.worker_id,
                "amount": p.amount,
                "fee": p.platform_fee,
                "total": p.total_amount,
                "status": p.status,
                "reference_id": p.reference_id,
                "gateway": p.gateway,
                "created_at": safe_iso(p.created_at),
            }
            for p in Payment.query.order_by(Payment.created_at.desc()).all()
        ]
    )


@admin_bp.get("/admin/reports")
@role_required("admin")
def reports():
    return ok(
        [
            {
                "id": r.id,
                "reporter_id": r.reporter_id,
                "target_type": r.target_type,
                "target_id": r.target_id,
                "reason": r.reason,
                "status": r.status,
                "created_at": safe_iso(r.created_at),
            }
            for r in Report.query.order_by(Report.created_at.desc()).all()
        ]
    )


@admin_bp.post("/admin/reports")
@role_required("worker", "employer", "admin")
def create_report():
    data = request.get_json(silent=True) or {}
    if not data.get("reason") or not data.get("target_type"):
        return err("Reason and target are required")
    report = Report(
        reporter_id=current_user().id,
        target_type=data.get("target_type"),
        target_id=data.get("target_id"),
        reason=data.get("reason"),
    )
    db.session.add(report)
    db.session.commit()
    return ok({"id": report.id}, "Report submitted")


@admin_bp.put("/admin/reports/<int:rid>")
@role_required("admin")
def update_report(rid):
    report = db.session.get(Report, rid)
    if not report:
        return err("Report not found", 404)
    report.status = (request.get_json(silent=True) or {}).get("status", "Reviewed")
    db.session.commit()
    return ok({}, "Report updated")
