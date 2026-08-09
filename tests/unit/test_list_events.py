import json
from .conftest import load_lambda


def test_list_events_returns_all(dynamodb_tables):
    app = load_lambda("list_events", "list_events_app")
    dynamodb_tables["events"].put_item(Item={"eventId": "evt-1", "eventName": "A"})
    dynamodb_tables["events"].put_item(Item={"eventId": "evt-2", "eventName": "B"})

    result = app.handler({"queryStringParameters": None}, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert len(body["events"]) == 2


def test_list_events_invalid_limit_returns_400(dynamodb_tables):
    app = load_lambda("list_events", "list_events_app_2")
    result = app.handler({"queryStringParameters": {"limit": "0"}}, None)
    assert result["statusCode"] == 400

    result = app.handler({"queryStringParameters": {"limit": "abc"}}, None)
    assert result["statusCode"] == 400
