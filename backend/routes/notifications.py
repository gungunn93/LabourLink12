from flask import Blueprint
from flask_jwt_extended import jwt_required

from extensions import db
from models import Notification, Message, Conversation
from utils.responses import ok, err
from utils.authz import current_user
from utils.serialize import safe_iso

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.get("/notifications")
@jwt_required()
def list_notifications():
    items = Notification.query.filter_by(user_id=current_user().id).order_by(Notification.created_at.desc()).all()
    return ok(
        [
            {
                "id": item.id,
                "title": item.title,
                "message": item.message,
                "kind": item.kind,
                "is_read": item.is_read,
                "date": safe_iso(item.created_at),
            }
            for item in items
        ]
    )


@notifications_bp.put("/notifications/<int:nid>/read")
@jwt_required()
def mark_read(nid):
    notification = db.session.get(Notification, nid)
    if not notification:
        return err("Notification not found", 404)
    if notification.user_id != current_user().id:
        return err("Access denied", 403)
    notification.is_read = True
    db.session.commit()
    return ok({}, "Marked read")


@notifications_bp.put("/notifications/read-all")
@jwt_required()
def read_all():
    Notification.query.filter_by(user_id=current_user().id, is_read=False).update({"is_read": True})
    db.session.commit()
    return ok({}, "All notifications marked read")


@notifications_bp.get("/notifications/unread-count")
@jwt_required()
def unread_count():
    """Returns unread notification count and unread message count in one call."""
    user = current_user()
    notif_count = Notification.query.filter_by(user_id=user.id, is_read=False).count()

    # Count conversations this user is part of that have unread messages
    convs = Conversation.query.filter(
        (Conversation.worker_id == user.id) | (Conversation.employer_id == user.id)
    ).all()
    msg_count = 0
    for conv in convs:
        msg_count += Message.query.filter_by(
            conversation_id=conv.id, is_read=False
        ).filter(Message.sender_id != user.id).count()

    return ok({"notifications": notif_count, "messages": msg_count})
