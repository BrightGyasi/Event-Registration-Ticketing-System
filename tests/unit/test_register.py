import json
from .conftest import load_lambda


def make_event(body):
    return {"body": json.dumps(body)}


def test_register_success(dynamodb_tables):
    app = load_lambda("register", "register_app")
    dynamodb_tables["events"].put_item(
        Item={"eventId": "evt-1", "eventName": "Career Fair", "eventDate": "2026-09-01", "capacity": 2}
    )

    result = app.handler(make_event({"eventId": "evt-1", "name": "Ada Lovelace", "email": "ada@example.com"}), None)

    assert result["statusCode"] == 201
    body = json.loads(result["body"])
    assert body["eventId"] == "evt-1"
    assert body["email"] == "ada@example.com"
    assert body["status"] == "CONFIRMED"

    event_after = dynamodb_tables["events"].get_item(Key={"eventId": "evt-1"})["Item"]
    assert event_after["registeredCount"] == 1


def test_register_missing_fields_returns_400(dynamodb_tables):
    app = load_lambda("register", "register_app_2")
    result = app.handler(make_event({"eventId": "evt-1"}), None)
    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "name" in str(body["details"])
    assert "email" in str(body["details"])


def test_register_invalid_email_returns_400(dynamodb_tables):
    app = load_lambda("register", "register_app_3")
    result = app.handler(
        make_event({"eventId": "evt-1", "name": "Ada", "email": "not-an-email"}), None
    )
    assert result["statusCode"] == 400


def test_register_unknown_event_returns_404(dynamodb_tables):
    app = load_lambda("register", "register_app_4")
    result = app.handler(
        make_event({"eventId": "does-not-exist", "name": "Ada", "email": "ada@example.com"}), None
    )
    assert result["statusCode"] == 404


def test_register_full_event_returns_409(dynamodb_tables):
    app = load_lambda("register", "register_app_5")
    dynamodb_tables["events"].put_item(
        Item={"eventId": "evt-full", "eventName": "Full Event", "capacity": 1, "registeredCount": 1}
    )
    result = app.handler(
        make_event({"eventId": "evt-full", "name": "Bob", "email": "bob@example.com"}), None
    )
    assert result["statusCode"] == 409


def test_register_malformed_json_returns_400(dynamodb_tables):
    app = load_lambda("register", "register_app_6")
    result = app.handler({"body": "{not-json"}, None)
    assert result["statusCode"] == 400
