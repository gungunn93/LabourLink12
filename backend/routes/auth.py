from flask import Blueprint, request
from flask_jwt_extended import create_access_token, jwt_required

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


