from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from flask_cors import CORS

db = SQLAlchemy()
jwt = JWTManager()
cors = CORS()

# threading mode works on all Python versions including 3.14
# WebSocket support is handled by simple-websocket (no gevent/eventlet needed)
socketio = SocketIO(async_mode="threading")
