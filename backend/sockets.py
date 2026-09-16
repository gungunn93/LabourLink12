from flask import request
from flask_socketio import join_room, leave_room
from flask_jwt_extended import decode_token
from extensions import socketio, db
from models import User, Conversation, Job, Application

CONNECTED_USERS = {}


def _user_from_auth(auth):
    token = (auth or {}).get("token")
    if not token:
        return None
    try:
        decoded = decode_token(token)
        return db.session.get(User, int(decoded["sub"]))
    except Exception:
        return None


@socketio.on("connect")
def on_connect(auth=None):
    user = _user_from_auth(auth)
    if not user:
        return False
    CONNECTED_USERS[request.sid] = user.id
    join_room(f"user_{user.id}")
    return True


@socketio.on("disconnect")
def on_disconnect():
    CONNECTED_USERS.pop(request.sid, None)


@socketio.on("join_conversation")
def join_conversation(data):
    user_id = CONNECTED_USERS.get(request.sid)
    user = db.session.get(User, user_id) if user_id else None
    if not user:
        return
    try:
        cid = int(data.get("conversation_id"))
    except (TypeError, ValueError):
        return
    conversation = db.session.get(Conversation, cid)
    if conversation and user.id in (conversation.worker_id, conversation.employer_id):
        join_room(f"conversation_{cid}")


@socketio.on("leave_conversation")
def leave_conversation(data):
    cid = int((data or {}).get("conversation_id", 0) or 0)
    user_id = CONNECTED_USERS.get(request.sid)
    conversation = db.session.get(Conversation, cid) if cid else None
    if conversation and user_id in (conversation.worker_id, conversation.employer_id):
        leave_room(f"conversation_{cid}")


@socketio.on("join_job_location")
def join_job_location(data):
    user_id = CONNECTED_USERS.get(request.sid)
    user = db.session.get(User, user_id) if user_id else None
    if not user:
        return
    try:
        job_id = int(data.get("job_id"))
    except (TypeError, ValueError):
        return
    job = db.session.get(Job, job_id)
    if not job:
        return
    allowed = job.employer_id == user.id or Application.query.filter_by(
        job_id=job_id, worker_id=user.id
    ).filter(Application.status.in_(["Accepted", "Assigned", "Ongoing", "Completed"])).first()
    if allowed:
        join_room(f"job_{job_id}")
