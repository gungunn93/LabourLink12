from flask import jsonify


def ok(data=None, message="Operation successful", status=200):
    return jsonify(success=True, message=message, data=data if data is not None else {}), status


def err(message, status=400, extra=None):
    payload = {"success": False, "message": message}
    if extra:
        payload["error"] = extra
    return jsonify(payload), status
