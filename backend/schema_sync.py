from flask import current_app
from sqlalchemy import inspect, text
from extensions import db


NEW_COLUMNS = {
    "user": {},
    "job": {
        "image": "VARCHAR(300)",
        "agreed_wage": "FLOAT",
        "extra_amount": "FLOAT DEFAULT 0",
    },
    "application": {
        "agreed_wage": "FLOAT",
    },
    "negotiation": {
        "original_price": "FLOAT",
        "last_offer_by": "INTEGER",
        "expires_at": "TIMESTAMP",
    },
    "negotiation_message": {
        "action": "VARCHAR(30)",
    },
    "payment": {
        "gateway": "VARCHAR(40)",
        "gateway_order_id": "VARCHAR(120)",
        "gateway_payment_id": "VARCHAR(120)",
        "failure_reason": "TEXT",
        "updated_at": "TIMESTAMP",
    },
}


def sync_schema():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    for table, columns in NEW_COLUMNS.items():
        if table not in tables:
            continue
        existing = {col["name"] for col in inspector.get_columns(table)}
        for name, ddl in columns.items():
            if name in existing:
                continue
            db.session.execute(text(f'ALTER TABLE "{table}" ADD COLUMN {name} {ddl}'))
    db.session.commit()
    current_app.logger.info("Schema sync complete")
