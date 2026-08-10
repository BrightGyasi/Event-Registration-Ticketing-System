"""
Shared helpers for the Event Registration & Ticketing System.

Kept dependency-free (stdlib only) so every Lambda can import it without
needing a Lambda Layer, and so unit tests don't need extra packaging steps.
"""
import json
import re
import decimal

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "OPTIONS,POST,GET,DELETE",
    "Content-Type": "application/json",
}


class DecimalEncoder(json.JSONEncoder):
    """DynamoDB returns Decimal for numbers; make them JSON-serialisable."""

    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return int(o) if o % 1 == 0 else float(o)
        return super().default(o)


def response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body, cls=DecimalEncoder),
    }


def error_response(status_code: int, message: str, details=None) -> dict:
    body = {"error": message}
    if details:
        body["details"] = details
    return response(status_code, body)


def is_valid_email(value: str) -> bool:
    return isinstance(value, str) and bool(EMAIL_RE.match(value.strip())) and len(value) <= 254


def sanitize_str(value, max_len: int = 200) -> str:
    """Basic input sanitisation: type-check, trim, cap length, strip control chars."""
    if not isinstance(value, str):
        raise ValueError("expected a string")
    cleaned = "".join(ch for ch in value.strip() if ch.isprintable())
    if not cleaned:
        raise ValueError("value cannot be empty")
    if len(cleaned) > max_len:
        raise ValueError(f"value exceeds max length of {max_len}")
    return cleaned


def validate_register_payload(payload: dict) -> list:
    """Returns a list of human-readable validation error strings (empty = valid)."""
    errors = []
    if not isinstance(payload, dict):
        return ["request body must be a JSON object"]

    event_id = payload.get("eventId")
    if not event_id or not isinstance(event_id, str):
        errors.append("eventId is required and must be a string")

    name = payload.get("name")
    if not name or not isinstance(name, str) or not name.strip():
        errors.append("name is required and must be a non-empty string")
    elif len(name.strip()) > 100:
        errors.append("name must be 100 characters or fewer")

    email = payload.get("email")
    if not email or not is_valid_email(email):
        errors.append("email is required and must be a valid email address")

    return errors


def parse_json_body(event: dict):
    """Returns (payload, error_response_or_None)."""
    raw = event.get("body") or "{}"
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None, error_response(400, "Request body must be valid JSON")
    return payload, None
