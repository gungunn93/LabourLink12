import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


def _require(name, default=None):
    """Return env var value; raise at startup if missing in production and no default."""
    val = os.getenv(name, default)
    if val is None:
        raise RuntimeError(f"Required environment variable '{name}' is not set")
    return val


class Config:
    # ── Security ────────────────────────────────────────────────────────────
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", os.getenv("SECRET_KEY", "dev-secret-change-in-production"))
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=int(os.getenv("JWT_EXPIRES_DAYS", "7")))

    # ── Database ─────────────────────────────────────────────────────────────
    _raw_db_url = os.getenv("DATABASE_URL", "sqlite:///labourlink_dev.db")
    # Render/Heroku provide postgres:// but SQLAlchemy 1.4+ requires postgresql://
    SQLALCHEMY_DATABASE_URI = (
        _raw_db_url.replace("postgres://", "postgresql://", 1)
        if _raw_db_url.startswith("postgres://")
        else _raw_db_url
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # ── CORS / Origins ───────────────────────────────────────────────────────
    APP_ENV = os.getenv("APP_ENV", "development")
    # Comma-separated list of allowed frontend origins, e.g.:
    # CORS_ORIGINS=https://labourlink.onrender.com,https://www.labourlink.com
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
    # Legacy single-origin support
    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "")

    # ── Uploads ──────────────────────────────────────────────────────────────
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB

    # ── Business logic ───────────────────────────────────────────────────────
    PLATFORM_FEE_PERCENT = float(os.getenv("PLATFORM_FEE_PERCENT", "5"))

    # ── Payments ─────────────────────────────────────────────────────────────
    PAYMENT_GATEWAY = os.getenv("PAYMENT_GATEWAY", "razorpay")
    RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
    # Cashfree (free alternative to Razorpay — signup at cashfree.com)
    CASHFREE_APP_ID = os.getenv("CASHFREE_APP_ID", "")
    CASHFREE_SECRET_KEY = os.getenv("CASHFREE_SECRET_KEY", "")
    CASHFREE_ENV = os.getenv("CASHFREE_ENV", "sandbox")

    # ── Maps ─────────────────────────────────────────────────────────────────
    MAP_TILE_URL = os.getenv("MAP_CONFIG", "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png")
