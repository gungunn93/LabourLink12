from datetime import datetime
from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from extensions import db, socketio
from models import Conversation, Message, Job, User
from services.notifications import notify
from services.chat_service import get_or_create_conversation
from utils.responses import ok, err
from utils.authz import current_user
from utils.serialize import safe_iso, user_json

chat_bp = Blueprint("chat", __name__)


def _allowed(conversation, user):
    return user and user.id in (conversation.worker_id, conversation.employer_id)


@chat_bp.get("/conversations")
@jwt_required()
def conversations():
    user = current_user()
    items = Conversation.query.filter(
        (Conversation.worker_id == user.id) | (Conversation.employer_id == user.id)
    ).order_by(Conversation.created_at.desc()).all()
    result = []
    for conversation in items:
        last = (
            Message.query.filter_by(conversation_id=conversation.id)
            .order_by(Message.created_at.desc())
            .first()
        )
        other_id = conversation.employer_id if user.id == conversation.worker_id else conversation.worker_id
        job = db.session.get(Job, conversation.job_id) if conversation.job_id else None
        result.append(
            {
                "id": conversation.id,
                "job_id": conversation.job_id,
                "job_title": job.title if job else None,
                "worker_id": conversation.worker_id,
                "employer_id": conversation.employer_id,
                "other_user": user_json(db.session.get(User, other_id)),
                "last_message": last.text if last else None,
                "last_at": safe_iso(last.created_at) if last else safe_iso(conversation.created_at),
            }
        )
    return ok(result)


@chat_bp.post("/conversations")
@jwt_required()
def conversation_create():
    data = request.get_json(silent=True) or {}
    user = current_user()
    job_id = data.get("job_id")
    if user.role == "employer":
        worker_id = data.get("worker_id")
        employer_id = user.id
        if not worker_id:
            return err("Worker ID is required")
    elif user.role == "worker":
        worker_id = user.id
        employer_id = data.get("employer_id")
        if not employer_id and job_id:
            job = db.session.get(Job, job_id)
            employer_id = job.employer_id if job else None
        if not employer_id:
            return err("Employer ID is required")
    else:
        return err("Forbidden", 403)
    conversation, _ = get_or_create_conversation(job_id, worker_id, employer_id)
    db.session.commit()
    return ok({"id": conversation.id}, "Conversation ready")


@chat_bp.get("/conversations/<int:cid>/messages")
@jwt_required()
def messages(cid):
    conversation = db.session.get(Conversation, cid)
    if not conversation:
        return err("Conversation not found", 404)
    user = current_user()
    if not _allowed(conversation, user):
        return err("Access denied", 403)
    items = Message.query.filter_by(conversation_id=cid).order_by(Message.created_at).all()
    # Mark messages sent by the other person as read
    Message.query.filter_by(conversation_id=cid, is_read=False).filter(
        Message.sender_id != user.id
    ).update({"is_read": True})
    db.session.commit()
    return ok(
        [
            {
                "id": m.id,
                "sender_id": m.sender_id,
                "text": m.text,
                "attachment": m.attachment,
                "is_read": m.is_read,
                "date": safe_iso(m.created_at),
            }
            for m in items
        ]
    )


@chat_bp.post("/conversations/<int:cid>/messages")
@jwt_required()
def send_message(cid):
    conversation = db.session.get(Conversation, cid)
    if not conversation:
        return err("Conversation not found", 404)
    user = current_user()
    if not _allowed(conversation, user):
        return err("Access denied", 403)
    data = request.get_json(silent=True) or {}
    text = str(data.get("text") or "").strip()
    if not text:
        return err("Message cannot be empty")
    message = Message(conversation_id=cid, sender_id=user.id, text=text, attachment=data.get("attachment"))
    db.session.add(message)
    recipient = conversation.employer_id if user.id == conversation.worker_id else conversation.worker_id
    notify(recipient, "New chat message", text[:120], "message")
    db.session.commit()
    payload = {
        "id": message.id,
        "conversation_id": cid,
        "sender_id": user.id,
        "text": message.text,
        "date": datetime.utcnow().isoformat(),
    }
    socketio.emit("chat:message", payload, to=f"conversation_{cid}")
    socketio.emit("chat:message", payload, to=f"user_{recipient}")
    return ok(payload, "Message sent")
