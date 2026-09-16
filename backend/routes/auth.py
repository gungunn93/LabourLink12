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


@auth_bp.post("/setup-admin")
def setup_admin():
    """
    One-time endpoint to create the admin account.
    Protected by ADMIN_SETUP_KEY environment variable.
    """
    import os
    setup_key = os.getenv("ADMIN_SETUP_KEY", "").strip()
    if not setup_key:
        return err("Admin setup is not enabled. Set ADMIN_SETUP_KEY in environment variables.", 403)

    data = request.get_json(silent=True) or {}
    provided_key = str(data.get("setup_key") or "").strip()
    if provided_key != setup_key:
        return err("Invalid setup key", 403)

    email = str(data.get("email") or "admin@labourlink.com").strip().lower()
    password = str(data.get("password") or "Admin@1234")
    name = str(data.get("name") or "Admin")

    if len(password) < 8:
        return err("Password must be at least 8 characters")

    existing = User.query.filter_by(email=email).first()
    if existing:
        if existing.role == "admin":
            return ok({"email": existing.email}, "Admin already exists")
        existing.role = "admin"
        db.session.commit()
        return ok({"email": existing.email}, "User promoted to admin")

    admin = User(name=name, email=email, role="admin")
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    token = create_access_token(identity=str(admin.id), additional_claims={"role": "admin"})
    return ok({"email": email, "token": token}, "Admin account created successfully")


@auth_bp.get("/setup-admin/<string:key>")
def setup_admin_get(key):
    """
    Simple GET version — just open this URL in browser:
    /api/auth/setup-admin/YOUR_ADMIN_SETUP_KEY
    """
    import os
    setup_key = os.getenv("ADMIN_SETUP_KEY", "").strip()
    if not setup_key:
        return err("Admin setup is not enabled. Set ADMIN_SETUP_KEY in environment variables.", 403)
    if key.strip() != setup_key:
        return err("Invalid setup key", 403)

    email = "admin@labourlink.com"
    password = "Admin@1234"
    name = "Admin"

    existing = User.query.filter_by(email=email).first()
    if existing:
        if existing.role == "admin":
            return ok({"email": existing.email, "password": "Admin@1234"}, "Admin already exists — login with Admin@1234")
        existing.role = "admin"
        db.session.commit()
        return ok({"email": existing.email}, "User promoted to admin")

    admin = User(name=name, email=email, role="admin")
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    return ok({"email": email, "password": password}, "Admin created! Login with admin@labourlink.com / Admin@1234")
