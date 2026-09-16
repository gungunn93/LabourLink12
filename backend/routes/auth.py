from flask import Blueprint, request
from flask_jwt_extended import create_access_token, jwt_required
import secrets
from datetime import datetime, timedelta

from extensions import db
from models import User, WorkerProfile, EmployerProfile, Wallet
from utils.responses import ok, err
from utils.authz import current_user
from utils.serialize import user_json

auth_bp = Blueprint("auth", __name__)


def _normalize_phone(phone):
    digits = "".join(ch for ch in str(phone or "") if ch.isdigit())
    return digits[-10:] if len(digits) >= 10 else digits


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    required = ["name", "email", "password", "role"]
    if any(not str(data.get(field) or "").strip() for field in required):
        return err("Name, email, phone, password and role are required")

    role = str(data["role"]).lower()
    email = str(data["email"]).strip().lower()
    phone = _normalize_phone(data.get("phone")) or None
    password = str(data["password"])

    if role not in ("worker", "employer"):
        return err("Invalid role")
    if len(password) < 8:
        return err("Password must be at least 8 characters")
    if User.query.filter_by(email=email).first():
        return err("Email already registered")
    if phone and User.query.filter_by(phone=phone).first():
        return err("Mobile number already registered")

    user = User(name=str(data["name"]).strip(), email=email, phone=phone, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    if role == "worker":
        db.session.add(
            WorkerProfile(
                user_id=user.id,
                skills=data.get("skills", ""),
                experience=int(data.get("experience", 0) or 0),
                location=data.get("location"),
                latitude=data.get("latitude"),
                longitude=data.get("longitude"),
                availability=data.get("availability", "Available"),
                preferred_area=data.get("preferred_area"),
                languages=data.get("languages", ""),
            )
        )
        db.session.add(Wallet(worker_id=user.id))
    else:
        db.session.add(
            EmployerProfile(
                user_id=user.id,
                company_name=data.get("company_name") or user.name,
                location=data.get("location"),
                latitude=data.get("latitude"),
                longitude=data.get("longitude"),
                about=data.get("about"),
                employer_type=data.get("employer_type"),
            )
        )

    db.session.commit()
    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    return ok({"token": token, "user": user_json(user)}, "Registration successful")


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    identifier = str(data.get("email") or data.get("username") or "").strip()
    password = data.get("password") or ""
    if not identifier or not password:
        return err("Email or username and password are required")
    email = identifier.lower()
    user = User.query.filter((User.email == email) | (User.phone == identifier)).first()
    if not user or not user.check_password(password):
        return err("Invalid email or password", 401)
    if not user.is_active:
        return err("Account is inactive", 403)
    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    return ok({"token": token, "user": user_json(user)}, "Login successful")


@auth_bp.get("/me")
@jwt_required()
def me():
    user = current_user()
    if not user:
        return err("User not found", 404)
    return ok(user_json(user))




# In-memory token store (works for single-worker deployments)
_reset_tokens = {}  # token -> {user_id, expires_at}


@auth_bp.post("/forgot-password")
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email") or "").strip().lower()
    if not email:
        return err("Email is required")
    user = User.query.filter_by(email=email).first()
    # Always return success — never reveal whether email exists (security)
    if not user:
        return ok({}, "If that email is registered, a reset link has been sent.")
    token = secrets.token_urlsafe(32)
    _reset_tokens[token] = {
        "user_id": user.id,
        "expires_at": datetime.utcnow() + timedelta(hours=1),
    }
    # In production: send this token via email (e.g. SendGrid, SMTP)
    # For now: return the token in response so it can be used directly
    # (Remove the token from response once email is configured)
    import os
    if os.getenv("APP_ENV") == "development":
        return ok({"reset_token": token, "note": "Dev mode: use this token directly"}, "Reset token generated")
    return ok({}, "If that email is registered, a reset link has been sent.")


@auth_bp.post("/reset-password")
def reset_password():
    data = request.get_json(silent=True) or {}
    token = str(data.get("token") or "").strip()
    new_password = str(data.get("password") or "")
    if not token or not new_password:
        return err("Token and new password are required")
    if len(new_password) < 8:
        return err("Password must be at least 8 characters")
    entry = _reset_tokens.get(token)
    if not entry:
        return err("Invalid or expired reset token", 400)
    if datetime.utcnow() > entry["expires_at"]:
        del _reset_tokens[token]
        return err("Reset token has expired. Please request a new one.", 400)
    user = db.session.get(User, entry["user_id"])
    if not user:
        return err("User not found", 404)
    user.set_password(new_password)
    db.session.commit()
    del _reset_tokens[token]
    return ok({}, "Password reset successfully. You can now log in.")
