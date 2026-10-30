"""Consistent JSON response envelope used by every endpoint.

Success: {"success": true, "data": ...}
Error:   {"success": false, "error": {"code": "...", "message": "...", "details": {...}}}
"""

from flask import jsonify


def ok(data=None, status: int = 200):
    return jsonify({"success": True, "data": data}), status


def error(code: str, message: str, status: int, details=None):
    body = {"success": False, "error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return jsonify(body), status


class ApiError(Exception):
    """Raise anywhere in a request to return a structured error."""

    def __init__(self, code: str, message: str, status: int = 400, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.details = details
