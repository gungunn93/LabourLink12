from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import Payment, Wallet, WalletTransaction, Job, Application
from services.payments import calculate, gateway_mode, create_razorpay_order, verify_razorpay_signature
from services.notifications import notify
from utils.responses import ok, err
from utils.authz import current_user, role_required
from utils.serialize import safe_iso

payments_bp = Blueprint("payments", __name__)


def _serialize(payment):
    return {
        "id": payment.id,
        "job_id": payment.job_id,
        "employer_id": payment.employer_id,
        "worker_id": payment.worker_id,
        "amount": payment.amount,
        "fee": payment.platform_fee,
        "total": payment.total_amount,
        "status": payment.status,
        "reference_id": payment.reference_id,
        "gateway": payment.gateway,
        "gateway_order_id": payment.gateway_order_id,
        "created_at": safe_iso(payment.created_at),
        "failure_reason": payment.failure_reason,
    }


def _credit_worker(payment):
    wallet = Wallet.query.filter_by(worker_id=payment.worker_id).first()
    if not wallet:
        wallet = Wallet(worker_id=payment.worker_id, balance=0, total_earnings=0, pending=0)
        db.session.add(wallet)
        db.session.flush()
    wallet.balance = (wallet.balance or 0) + payment.amount
    wallet.total_earnings = (wallet.total_earnings or 0) + payment.amount
    db.session.add(
        WalletTransaction(
            wallet_id=wallet.id,
            amount=payment.amount,
            kind="credit",
            description=f"Payment {payment.reference_id} for job #{payment.job_id}",
        )
    )


@payments_bp.get("/payments/config")
@jwt_required()
def config():
    mode = gateway_mode()
    if mode != "razorpay":
        return err("Razorpay is not configured. Add RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET on the server.", 503)
    from flask import current_app

    return ok(
        {
            "mode": mode,
            "key_id": current_app.config.get("RAZORPAY_KEY_ID") if mode == "razorpay" else None,
            "currency": "INR",
        }
    )


@payments_bp.post("/payments/create")
@role_required("employer")
def create_payment():
    data = request.get_json(silent=True) or {}
    job_id = data.get("job_id")
    worker_id = data.get("worker_id")
    job = db.session.get(Job, job_id)
    if not job:
        return err("Job not found", 404)
    if job.employer_id != current_user().id:
        return err("Forbidden", 403)
    application = Application.query.filter_by(job_id=job_id, worker_id=worker_id).first()
    if not application or application.status not in ("Accepted", "Assigned", "Ongoing", "Completed"):
        return err("Payment is only allowed for an assigned worker")
    existing = Payment.query.filter(
        Payment.job_id == job_id,
        Payment.worker_id == worker_id,
        Payment.status.in_(["Paid", "Initiated", "Pending"]),
    ).first()
    if existing and existing.status == "Paid":
        return err("This job has already been paid")
    if existing and existing.status in ("Initiated", "Pending"):
        return ok(_serialize(existing), "Existing payment resumed")

    payable = float(application.agreed_wage or job.agreed_wage or job.wage or 0) + float(job.extra_amount or 0)
    try:
        amount = float(data.get("amount", payable))
    except (TypeError, ValueError):
        return err("Invalid payment amount")
    if abs(amount - payable) > 0.01:
        return err(f"Payment amount must equal the payable amount ₹{payable:.2f}")
    if amount <= 0:
        return err("Payment amount must be greater than zero")

    fee, total, reference = calculate(amount)
    mode = gateway_mode()
    payment = Payment(
        job_id=job_id,
        employer_id=current_user().id,
        worker_id=worker_id,
        amount=amount,
        platform_fee=fee,
        total_amount=total,
        reference_id=reference,
        status="Initiated",
        gateway=mode,
    )
    db.session.add(payment)
    db.session.flush()
    extra = {}
    if mode == "razorpay":
        try:
            order = create_razorpay_order(total, reference)
            payment.gateway_order_id = order.get("id")
            extra = {"order_id": order.get("id"), "razorpay_amount": order.get("amount")}
        except Exception as exc:
            db.session.rollback()
            return err(f"Razorpay order failed: {exc}", 502)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return err("Duplicate payment reference. Please retry.")
    payload = _serialize(payment)
    payload.update(extra)
    return ok(payload, "Payment initiated")


@payments_bp.post("/payments/confirm")
@jwt_required()
def confirm_payment():
    data = request.get_json(silent=True) or {}
    payment = db.session.get(Payment, data.get("payment_id"))
    if not payment:
        return err("Payment not found", 404)
    user = current_user()
    if user.id != payment.employer_id and user.role != "admin":
        return err("Access denied", 403)
    if payment.status == "Paid":
        return err("Payment already completed")
    if payment.status in ("Cancelled", "Failed"):
        return err(f"Payment is {payment.status}")

    if payment.gateway == "razorpay":
        try:
            verify_razorpay_signature(
                data.get("razorpay_order_id") or payment.gateway_order_id,
                data.get("razorpay_payment_id"),
                data.get("razorpay_signature"),
            )
            payment.gateway_payment_id = data.get("razorpay_payment_id")
        except Exception:
            payment.status = "Failed"
            payment.failure_reason = "Signature verification failed"
            db.session.commit()
            notify(payment.employer_id, "Payment failed", "Razorpay signature check failed", "payment")
            return err("Payment verification failed", 400)
    else:
        return err("Unsupported payment gateway", 503)

    payment.status = "Paid"
    _credit_worker(payment)
    job = db.session.get(Job, payment.job_id)
    if job:
        job.status = "Completed"
    application = Application.query.filter_by(job_id=payment.job_id, worker_id=payment.worker_id).first()
    if application:
        application.status = "Completed"
    notify(payment.worker_id, "Payment successful", f"₹{payment.amount} credited to your wallet", "payment")
    notify(payment.employer_id, "Payment successful", f"Payment {payment.reference_id} completed", "payment")
    db.session.commit()
    return ok(_serialize(payment), "Payment successful")


@payments_bp.post("/payments/cancel")
@jwt_required()
def cancel_payment():
    data = request.get_json(silent=True) or {}
    payment = db.session.get(Payment, data.get("payment_id"))
    if not payment:
        return err("Payment not found", 404)
    if current_user().id != payment.employer_id:
        return err("Access denied", 403)
    if payment.status == "Paid":
        return err("Paid transactions cannot be cancelled")
    payment.status = "Cancelled"
    payment.failure_reason = data.get("reason") or "Cancelled by employer"
    notify(payment.worker_id, "Payment cancelled", f"Payment {payment.reference_id} was cancelled", "payment")
    db.session.commit()
    return ok(_serialize(payment), "Payment cancelled")


@payments_bp.post("/payments/fail")
@jwt_required()
def fail_payment():
    data = request.get_json(silent=True) or {}
    payment = db.session.get(Payment, data.get("payment_id"))
    if not payment:
        return err("Payment not found", 404)
    if current_user().id != payment.employer_id:
        return err("Access denied", 403)
    if payment.status == "Paid":
        return err("Paid transactions cannot be marked failed")
    payment.status = "Failed"
    payment.failure_reason = data.get("reason") or "Gateway reported failure"
    notify(payment.employer_id, "Payment failed", payment.failure_reason, "payment")
    notify(payment.worker_id, "Payment failed", f"Payment {payment.reference_id} failed", "payment")
    db.session.commit()
    return ok(_serialize(payment), "Payment marked failed")


@payments_bp.get("/payments/history")
@jwt_required()
def history():
    user = current_user()
    q = Payment.query
    if user.role == "admin":
        payments = q.order_by(Payment.created_at.desc()).all()
    else:
        payments = q.filter((Payment.worker_id == user.id) | (Payment.employer_id == user.id)).order_by(Payment.created_at.desc()).all()
    return ok([_serialize(p) for p in payments])
