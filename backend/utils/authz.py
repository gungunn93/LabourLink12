from functools import wraps
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity, decode_token
from extensions import db
from models import User
from utils.responses import err


def current_user():
    identity = get_jwt_identity()
    if identity is None:
        return None
    try:
        return db.session.get(User, int(identity))
    except (TypeError, ValueError):
        return None


def optional_user():
    header = request.headers.get("Authorization") or ""
    if not header.startswith("Bearer "):
        return None
    try:
        decoded = decode_token(header.split(" ", 1)[1])
        return db.session.get(User, int(decoded["sub"]))
    except Exception:
        return None


def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            user = current_user()
            if user is None:
                return err("User not found", 401)
            if not user.is_active:
                return err("Account is inactive", 403)
            if roles and user.role not in roles:
                return err("Access denied", 403)
            return fn(*args, **kwargs)

        return wrapper

    return decorator
