from flask import jsonify


def api_response(success, code, message, data=None, http_status=None, extra=None):
    payload = {
        "success": bool(success),
        "code": code,
        "message": message,
        "data": data or {},
    }
    if extra:
        payload.update(extra)

    if http_status is None:
        http_status = 200 if success else 400
    return jsonify(payload), http_status
