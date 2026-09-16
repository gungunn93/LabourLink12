from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


class User(db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(30), unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class WorkerProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, index=True)
    skills = db.Column(db.String(500), default="")
    experience = db.Column(db.Integer, default=0)
    location = db.Column(db.String(200))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    availability = db.Column(db.String(100), default="Available")
    preferred_area = db.Column(db.String(200))
    languages = db.Column(db.String(300))
    photo = db.Column(db.String(300))
    document = db.Column(db.String(300))
    rating = db.Column(db.Float, default=0)
    completed_jobs = db.Column(db.Integer, default=0)


class EmployerProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, index=True)
    company_name = db.Column(db.String(160))
    location = db.Column(db.String(200))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    about = db.Column(db.Text)
    employer_type = db.Column(db.String(100))
    logo = db.Column(db.String(300))
    rating = db.Column(db.Float, default=0)
    jobs_posted = db.Column(db.Integer, default=0)
    workers_hired = db.Column(db.Integer, default=0)


class JobCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)


class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("job_category.id"))
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text)
    image = db.Column(db.String(300))
    location = db.Column(db.String(200))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    wage = db.Column(db.Float, nullable=False)
    agreed_wage = db.Column(db.Float)
    extra_amount = db.Column(db.Float, default=0)
    payment_type = db.Column(db.String(30), default="daily")
    required_workers = db.Column(db.Integer, default=1)
    job_date = db.Column(db.String(30))
    start_time = db.Column(db.String(20))
    duration = db.Column(db.String(100))
    deadline = db.Column(db.String(30))
    required_skills = db.Column(db.String(500))
    experience_required = db.Column(db.Integer, default=0)
    tools = db.Column(db.Text)
    is_negotiable = db.Column(db.Boolean, default=True)
    priority = db.Column(db.String(30), default="Normal")
    status = db.Column(db.String(30), default="Open", index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class Application(db.Model):
    __table_args__ = (db.UniqueConstraint("job_id", "worker_id", name="uq_application_job_worker"),)
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), index=True)
    worker_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    status = db.Column(db.String(30), default="Pending", index=True)
    agreed_wage = db.Column(db.Float)
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    note = db.Column(db.Text)


class Negotiation(db.Model):
    __table_args__ = (db.UniqueConstraint("job_id", "worker_id", name="uq_negotiation_job_worker"),)
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), index=True)
    employer_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    worker_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    original_price = db.Column(db.Float)
    current_offer = db.Column(db.Float)
    previous_offer = db.Column(db.Float)
    last_offer_by = db.Column(db.Integer)
    suggested_wage = db.Column(db.Float)
    status = db.Column(db.String(30), default="Pending", index=True)
    expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NegotiationMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    negotiation_id = db.Column(db.Integer, db.ForeignKey("negotiation.id"), index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    offer = db.Column(db.Float)
    message = db.Column(db.Text)
    action = db.Column(db.String(30), default="offer")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Conversation(db.Model):
    __table_args__ = (db.UniqueConstraint("job_id", "worker_id", "employer_id", name="uq_conversation_job_users"),)
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), index=True)
    worker_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    employer_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversation.id"), index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    text = db.Column(db.Text)
    attachment = db.Column(db.String(300))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class Wallet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True)
    balance = db.Column(db.Float, default=0)
    total_earnings = db.Column(db.Float, default=0)
    pending = db.Column(db.Float, default=0)


class WalletTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    wallet_id = db.Column(db.Integer, db.ForeignKey("wallet.id"), index=True)
    amount = db.Column(db.Float)
    kind = db.Column(db.String(30))
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Payment(db.Model):
    __table_args__ = (db.UniqueConstraint("reference_id", name="uq_payment_reference"),)
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), index=True)
    employer_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    worker_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    amount = db.Column(db.Float)
    platform_fee = db.Column(db.Float)
    total_amount = db.Column(db.Float)
    status = db.Column(db.String(30), default="Initiated", index=True)
    reference_id = db.Column(db.String(100), unique=True)
    gateway = db.Column(db.String(40), default="razorpay")
    gateway_order_id = db.Column(db.String(120))
    gateway_payment_id = db.Column(db.String(120))
    failure_reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    title = db.Column(db.String(160))
    message = db.Column(db.Text)
    kind = db.Column(db.String(50), index=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class RatingReview(db.Model):
    __table_args__ = (db.UniqueConstraint("job_id", "reviewer_id", "reviewee_id", name="uq_rating_once"),)
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"))
    reviewer_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    reviewee_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    rating = db.Column(db.Integer)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SavedJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class WorkerAvailability(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    day = db.Column(db.String(30))
    available = db.Column(db.Boolean, default=True)


class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    label = db.Column(db.String(100))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)


class LocationShare(db.Model):
    __table_args__ = (db.UniqueConstraint("job_id", "worker_id", name="uq_location_job_worker"),)
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), index=True)
    worker_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    is_active = db.Column(db.Boolean, default=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    accuracy = db.Column(db.Float)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)


class ExtraWorkRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), index=True)
    worker_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    amount = db.Column(db.Float, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default="Pending", index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    target_type = db.Column(db.String(30))
    target_id = db.Column(db.Integer)
    reason = db.Column(db.Text)
    status = db.Column(db.String(30), default="Open")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AdminLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    action = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class WorkerPortfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True, nullable=False)
    image_url = db.Column(db.String(300), nullable=False)
    caption = db.Column(db.String(200), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

