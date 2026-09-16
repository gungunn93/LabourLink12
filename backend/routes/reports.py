from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from extensions import db
from models import Report
from utils.responses import ok, err
from utils.authz import current_user

reports_bp = Blueprint("reports", __name__)


@reports_bp.post("/reports")
@jwt_required()
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
