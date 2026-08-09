"""
GET /events

Lists all events. Supports simple pagination via ?limit and ?nextToken
so the API doesn't fall over once the table grows past a single Scan page.
"""
import os
import json
import base64
import logging

import boto3
from botocore.exceptions import ClientError
from common.validation import response, error_response

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

dynamodb = boto3.resource("dynamodb")
events_table = dynamodb.Table(os.environ["EVENTS_TABLE"])

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


def _encode_token(key: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(key).encode()).decode()


def _decode_token(token: str) -> dict:
    return json.loads(base64.urlsafe_b64decode(token.encode()).decode())


def handler(event, context):
    params = (event.get("queryStringParameters") or {}) or {}

    try:
        limit = int(params.get("limit", DEFAULT_LIMIT))
    except (TypeError, ValueError):
        return error_response(400, "limit must be an integer")
    if limit < 1 or limit > MAX_LIMIT:
        return error_response(400, f"limit must be between 1 and {MAX_LIMIT}")

    scan_kwargs = {"Limit": limit}
    next_token = params.get("nextToken")
    if next_token:
        try:
            scan_kwargs["ExclusiveStartKey"] = _decode_token(next_token)
        except Exception:
            return error_response(400, "Invalid nextToken")

    try:
        result = events_table.scan(**scan_kwargs)
    except ClientError as exc:
        logger.error("DynamoDB scan failed: %s", exc)
        return error_response(500, "Could not list events")

    body = {"events": result.get("Items", [])}
    if "LastEvaluatedKey" in result:
        body["nextToken"] = _encode_token(result["LastEvaluatedKey"])

    return response(200, body)
