"""
POST /register

Registers an attendee for an event.
- Validates and sanitises input
- Confirms the event exists and has capacity (atomic conditional update, no race condition)
- Writes the registration record
- Optionally publishes an SNS notification for a confirmation email
"""
import os
import uuid
import logging
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError
from validation import (
    response,
    error_response,
    validate_register_payload,
    sanitize_str,
    parse_json_body,
)

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")

EVENTS_TABLE = os.environ["EVENTS_TABLE"]
REGISTRATIONS_TABLE = os.environ["REGISTRATIONS_TABLE"]
TOPIC_ARN = os.environ.get("CONFIRMATION_TOPIC_ARN", "")

events_table = dynamodb.Table(EVENTS_TABLE)
registrations_table = dynamodb.Table(REGISTRATIONS_TABLE)


def handler(event, context):
    payload, err = parse_json_body(event)
    if err:
        return err

    validation_errors = validate_register_payload(payload)
    if validation_errors:
        return error_response(400, "Validation failed", validation_errors)

    try:
        event_id = sanitize_str(payload["eventId"], max_len=64)
        name = sanitize_str(payload["name"], max_len=100)
        email = payload["email"].strip().lower()
    except ValueError as exc:
        return error_response(400, "Validation failed", [str(exc)])

    # 1. Confirm the event exists
    try:
        event_item = events_table.get_item(Key={"eventId": event_id}).get("Item")
    except ClientError as exc:
        logger.error("DynamoDB get_item failed: %s", exc)
        return error_response(500, "Could not read event")

    if not event_item:
        return error_response(404, f"Event '{event_id}' not found")

    capacity = int(event_item.get("capacity", 0))
    registration_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # 2. Atomically reserve a seat: only succeeds if registeredCount < capacity.
    #    This avoids a check-then-act race condition between concurrent requests.
    try:
        events_table.update_item(
            Key={"eventId": event_id},
            UpdateExpression="SET registeredCount = if_not_exists(registeredCount, :zero) + :one",
            ConditionExpression="attribute_not_exists(registeredCount) OR registeredCount < :capacity",
            ExpressionAttributeValues={":one": 1, ":zero": 0, ":capacity": capacity},
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return error_response(409, f"Event '{event_id}' is fully booked")
        logger.error("DynamoDB update_item failed: %s", exc)
        return error_response(500, "Could not reserve a seat")

    # 3. Write the registration record
    try:
        registrations_table.put_item(
            Item={
                "registrationId": registration_id,
                "eventId": event_id,
                "email": email,
                "name": name,
                "status": "CONFIRMED",
                "createdAt": now,
            },
            ConditionExpression="attribute_not_exists(registrationId)",
        )
    except ClientError as exc:
        # Roll back the seat reservation if we failed to persist the registration
        logger.error("Failed to write registration, rolling back seat: %s", exc)
        try:
            events_table.update_item(
                Key={"eventId": event_id},
                UpdateExpression="SET registeredCount = registeredCount - :one",
                ExpressionAttributeValues={":one": 1},
            )
        except ClientError:
            logger.error("Rollback of seat reservation also failed for event %s", event_id)
        return error_response(500, "Could not create registration")

    # 4. Best-effort confirmation notification (never fails the request)
    if TOPIC_ARN:
        try:
            sns.publish(
                TopicArn=TOPIC_ARN,
                Subject=f"Registration confirmed: {event_item.get('eventName', event_id)}",
                Message=(
                    f"Hi {name},\n\nYou're registered for "
                    f"{event_item.get('eventName', event_id)} on {event_item.get('eventDate', 'TBD')}.\n"
                    f"Registration ID: {registration_id}\n"
                ),
                MessageAttributes={"email": {"DataType": "String", "StringValue": email}},
            )
        except ClientError as exc:
            logger.warning("SNS publish failed (non-fatal): %s", exc)

    return response(
        201,
        {
            "registrationId": registration_id,
            "eventId": event_id,
            "email": email,
            "name": name,
            "status": "CONFIRMED",
            "createdAt": now,
        },
    )
