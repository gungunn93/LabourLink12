"""
Cashfree Payments integration — free alternative to Razorpay.

Setup:
1. Sign up at https://www.cashfree.com (free, no monthly fee)
2. Get your App ID and Secret Key from the dashboard
3. Add to your .env / Render environment:
      PAYMENT_GATEWAY=cashfree
      CASHFREE_APP_ID=your_app_id
      CASHFREE_SECRET_KEY=your_secret_key
      CASHFREE_ENV=sandbox          # use 'production' when going live

Cashfree supports: UPI, cards, net banking, wallets — all free to accept.
Settlement is directly to your bank account (T+2 days).
"""
import hashlib
import hmac
import os
import requests


CASHFREE_ENV = os.getenv("CASHFREE_ENV", "sandbox")
BASE_URL = (
    "https://api.cashfree.com/pg"
    if CASHFREE_ENV == "production"
    else "https://sandbox.cashfree.com/pg"
)
APP_ID = os.getenv("CASHFREE_APP_ID", "")
SECRET_KEY = os.getenv("CASHFREE_SECRET_KEY", "")


def _headers():
    return {
        "x-api-version": "2023-08-01",
        "x-client-id": APP_ID,
        "x-client-secret": SECRET_KEY,
        "Content-Type": "application/json",
    }


def is_configured():
    return bool(APP_ID and SECRET_KEY)


def create_cashfree_order(amount_inr: float, order_id: str, customer_name: str, customer_email: str, customer_phone: str = "9999999999"):
    """
    Create a Cashfree payment order.
    Returns order details including payment_session_id for frontend checkout.
    """
    if not is_configured():
        raise ValueError("Cashfree is not configured. Set CASHFREE_APP_ID and CASHFREE_SECRET_KEY.")
    payload = {
        "order_id": order_id[:50],
        "order_amount": round(float(amount_inr), 2),
        "order_currency": "INR",
        "customer_details": {
            "customer_id": order_id[:50],
            "customer_name": customer_name[:50],
            "customer_email": customer_email,
            "customer_phone": str(customer_phone)[-10:] or "9999999999",
        },
        "order_meta": {
            "notify_url": os.getenv("CASHFREE_WEBHOOK_URL", ""),
        },
    }
    resp = requests.post(f"{BASE_URL}/orders", json=payload, headers=_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


def verify_cashfree_signature(order_id: str, order_amount: str, reference_id: str, tx_status: str, tx_msg: str, tx_time: str, signature: str) -> bool:
    """
    Verify Cashfree webhook/response signature.
    """
    if not SECRET_KEY:
        raise ValueError("Cashfree secret key not configured")
    message = f"{order_id}{order_amount}{reference_id}{tx_status}{tx_msg}{tx_time}"
    computed = hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).digest()
    import base64
    computed_b64 = base64.b64encode(computed).decode()
    return hmac.compare_digest(computed_b64, signature)


def get_order_status(order_id: str) -> dict:
    """Fetch order status from Cashfree."""
    if not is_configured():
        raise ValueError("Cashfree is not configured.")
    resp = requests.get(f"{BASE_URL}/orders/{order_id}", headers=_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()
