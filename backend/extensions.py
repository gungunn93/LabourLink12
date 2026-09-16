import os
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from flask_cors import CORS

db = SQLAlchemy()
jwt = JWTManager()
cors = CORS()

# Use eventlet in production (Render), threading for local dev
# Override with SOCKETIO_ASYNC_MODE env var if needed
def _detect_async_mode():
    explicit = os.getenv("SOCKETIO_ASYNC_MODE")
    if explicit:
        return explicit
    try:
        import eventlet  # noqa: F401
        return "eventlet"
    except ImportError:
        return "threading"

socketio = SocketIO(async_mode=_detect_async_mode())
