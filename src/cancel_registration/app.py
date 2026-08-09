"""
DELETE /registration/{id}

Cancels a registration and releases the seat back to the event's capacity.
"""
import os
import logging

import boto3
from botocore.exceptions import ClientError
from common.validation import response, error_response, sanitize_str

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

dynamodb = boto3.resource("dynamodb")
registrations_table = dynamodb.Table(os.environ["REGISTRATIONS_TABLE"])
events_table = dynamodb.Table(os.environ["EVENTS_TABLE"])


def handler(event, context):
    path_params = event.get("pathParameters") or {}
    raw_id = path_params.get("id", "")

    try:
        registration_id = sanitize_str(raw_id, max_len=64)
    except ValueError:
        return error_response(400, "Path parameter 'id' is required")

    # Delete only if it exists, and get back the deleted item so we know which
    # event to release a seat on.
    try:
        result = registrations_table.delete_item(
            Key={"registrationId": registration_id},
            ConditionExpression="attribute_exists(registrationId)",
            ReturnValues="ALL_OLD",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return error_response(404, f"Registration '{registration_id}' not found")
        logger.error("DynamoDB delete_item failed: %s", exc)
        return error_response(500, "Could not cancel registration")

    deleted = result.get("Attributes", {})
    event_id = deleted.get("eventId")

    if event_id:
        try:
            events_table.update_item(
                Key={"eventId": event_id},
                UpdateExpression="SET registeredCount = registeredCount - :one",
                ConditionExpression="attribute_exists(registeredCount) AND registeredCount > :zero",
                ExpressionAttributeValues={":one": 1, ":zero": 0},
            )
        except ClientError as exc:
            # Registration is already cancelled; log but don't fail the request
            # over an inconsistent counter (self-heals via reconciliation/alerting).
            logger.warning("Could not decrement registeredCount for %s: %s", event_id, exc)

    return response(200, {"registrationId": registration_id, "status": "CANCELLED"})
