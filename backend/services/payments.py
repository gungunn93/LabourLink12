import uuid
from flask import current_app


def calculate(amount):
    fee_percent = float(current_app.config.get("PLATFORM_FEE_PERCENT", 5))
    fee = round(float(amount) * fee_percent / 100, 2)
    total = round(float(amount) + fee, 2)
    reference = f"LL-{uuid.uuid4().hex[:12].upper()}"
    return fee, total, reference


def gateway_mode():
    key = current_app.config.get("RAZORPAY_KEY_ID")
    secret = current_app.config.get("RAZORPAY_KEY_SECRET")
    configured = (current_app.config.get("PAYMENT_GATEWAY") or "razorpay").lower()
    if configured == "razorpay" and key and secret:
        return "razorpay"
    if configured == "cashfree" and current_app.config.get("CASHFREE_APP_ID") and current_app.config.get("CASHFREE_SECRET_KEY"):
        return "cashfree"
    return "unconfigured"


def create_razorpay_order(total, reference):
    import razorpay

    client = razorpay.Client(
        auth=(current_app.config["RAZORPAY_KEY_ID"], current_app.config["RAZORPAY_KEY_SECRET"])
    )
    order = client.order.create(
        {
            "amount": int(round(float(total) * 100)),
            "currency": "INR",
            "receipt": reference[:40],
            "payment_capture": 1,
        }
    )
    return order


def verify_razorpay_signature(order_id, payment_id, signature):
    import razorpay

    client = razorpay.Client(
        auth=(current_app.config["RAZORPAY_KEY_ID"], current_app.config["RAZORPAY_KEY_SECRET"])
    )
    client.utility.verify_payment_signature(
        {
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        }
    )
    return True
