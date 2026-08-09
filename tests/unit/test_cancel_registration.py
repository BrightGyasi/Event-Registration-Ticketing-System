import json
from .conftest import load_lambda


def test_cancel_registration_success_releases_seat(dynamodb_tables):
    app = load_lambda("cancel_registration", "cancel_app")
    dynamodb_tables["events"].put_item(Item={"eventId": "evt-1", "capacity": 5, "registeredCount": 1})
    dynamodb_tables["registrations"].put_item(
        Item={"registrationId": "r1", "eventId": "evt-1", "email": "ada@example.com", "name": "Ada"}
    )

    result = app.handler({"pathParameters": {"id": "r1"}}, None)

    assert result["statusCode"] == 200
    assert json.loads(result["body"])["status"] == "CANCELLED"

    event_after = dynamodb_tables["events"].get_item(Key={"eventId": "evt-1"})["Item"]
    assert event_after["registeredCount"] == 0

    assert "Item" not in dynamodb_tables["registrations"].get_item(Key={"registrationId": "r1"})


def test_cancel_unknown_registration_returns_404(dynamodb_tables):
    app = load_lambda("cancel_registration", "cancel_app_2")
    result = app.handler({"pathParameters": {"id": "does-not-exist"}}, None)
    assert result["statusCode"] == 404


def test_cancel_missing_id_returns_400(dynamodb_tables):
    app = load_lambda("cancel_registration", "cancel_app_3")
    result = app.handler({"pathParameters": {}}, None)
    assert result["statusCode"] == 400
