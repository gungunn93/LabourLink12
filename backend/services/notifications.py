from datetime import datetime
from flask import current_app
from extensions import db, socketio
from models import Notification


def notify(user_id, title, message, kind="general"):
    item = Notification(user_id=user_id, title=title, message=message, kind=kind)
    db.session.add(item)
    db.session.flush()
    try:
        socketio.emit(
            "notification:new",
            {
                "id": item.id,
                "title": title,
                "message": message,
                "kind": kind,
                "is_read": False,
                "date": datetime.utcnow().isoformat(),
            },
            to=f"user_{user_id}",
        )
    except Exception:
        current_app.logger.warning("Socket notification emit failed", exc_info=True)
    return item
