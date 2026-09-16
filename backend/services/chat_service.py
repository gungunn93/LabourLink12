from extensions import db
from models import Conversation


def get_or_create_conversation(job_id, worker_id, employer_id):
    conversation = Conversation.query.filter_by(
        job_id=job_id, worker_id=worker_id, employer_id=employer_id
    ).first()
    if conversation:
        return conversation, False
    conversation = Conversation(job_id=job_id, worker_id=worker_id, employer_id=employer_id)
    db.session.add(conversation)
    db.session.flush()
    return conversation, True
