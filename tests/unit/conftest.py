import os
import sys
import importlib.util

import boto3
import pytest
from moto import mock_aws

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVENTS_TABLE = "Events-test"
REGISTRATIONS_TABLE = "Registrations-test"


def load_lambda(function_dir: str, module_name: str):
    """Load a Lambda's app.py as a uniquely-named module so the four
    functions (each literally named app.py, as SAM expects) don't clobber
    each other in sys.modules."""
    path = os.path.join(ROOT, "src", function_dir, "app.py")
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def aws_env(monkeypatch):
    monkeypatch.setenv("EVENTS_TABLE", EVENTS_TABLE)
    monkeypatch.setenv("REGISTRATIONS_TABLE", REGISTRATIONS_TABLE)
    monkeypatch.setenv("EMAIL_INDEX_NAME", "EmailIndex")
    monkeypatch.setenv("CONFIRMATION_TOPIC_ARN", "")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    with mock_aws():
        yield


@pytest.fixture
def dynamodb_tables(aws_env):
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    events = ddb.create_table(
        TableName=EVENTS_TABLE,
        KeySchema=[{"AttributeName": "eventId", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "eventId", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    registrations = ddb.create_table(
        TableName=REGISTRATIONS_TABLE,
        KeySchema=[{"AttributeName": "registrationId", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "registrationId", "AttributeType": "S"},
            {"AttributeName": "email", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "EmailIndex",
                "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    events.wait_until_exists()
    registrations.wait_until_exists()
    return {"events": events, "registrations": registrations}
