import json
from .conftest import load_lambda


def test_get_registrations_by_email(dynamodb_tables):
    app = load_lambda("get_registrations", "get_registrations_app")
    dynamodb_tables["registrations"].put_item(
        Item={"registrationId": "r1", "eventId": "evt-1", "email": "ada@example.com", "name": "Ada"}
    )
    dynamodb_tables["registrations"].put_item(
        Item={"registrationId": "r2", "eventId": "evt-2", "email": "other@example.com", "name": "Bob"}
    )

    result = app.handler({"pathParameters": {"email": "ada@example.com"}}, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert len(body["registrations"]) == 1
    assert body["registrations"][0]["registrationId"] == "r1"


def test_get_registrations_invalid_email_returns_400(dynamodb_tables):
    app = load_lambda("get_registrations", "get_registrations_app_2")
    result = app.handler({"pathParameters": {"email": "not-an-email"}}, None)
    assert result["statusCode"] == 400


def test_get_registrations_no_matches_returns_empty_list(dynamodb_tables):
    app = load_lambda("get_registrations", "get_registrations_app_3")
    result = app.handler({"pathParameters": {"email": "nobody@example.com"}}, None)
    assert result["statusCode"] == 200
    assert json.loads(result["body"])["registrations"] == []
