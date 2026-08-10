"""
GET /registrations/{email}

Returns all registrations for a given email address, via the
EmailIndex GSI on the Registrations table (no table scan).
"""
import os
import urllib.parse
import logging

import boto3
from botocore.exceptions import ClientError
from validation import response, error_response, is_valid_email

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

dynamodb = boto3.resource("dynamodb")
registrations_table = dynamodb.Table(os.environ["REGISTRATIONS_TABLE"])
EMAIL_INDEX = os.environ.get("EMAIL_INDEX_NAME", "EmailIndex")


def handler(event, context):
    path_params = event.get("pathParameters") or {}
    raw_email = path_params.get("email", "")
    email = urllib.parse.unquote(raw_email).strip().lower()

    if not is_valid_email(email):
        return error_response(400, "Path parameter 'email' must be a valid email address")

    try:
        result = registrations_table.query(
            IndexName=EMAIL_INDEX,
            KeyConditionExpression="email = :e",
            ExpressionAttributeValues={":e": email},
        )
    except ClientError as exc:
        logger.error("DynamoDB query failed: %s", exc)
        return error_response(500, "Could not fetch registrations")

    return response(200, {"email": email, "registrations": result.get("Items", [])})
