#!/usr/bin/env python3
"""
Seed a few sample events into the Events table.

Usage:
    python scripts/seed_events.py --table Events-dev --region us-east-1
"""
import argparse
import boto3

SAMPLE_EVENTS = [
    {"eventId": "career-fair-2026", "eventName": "Career Fair 2026", "eventDate": "2026-09-15",
     "location": "Main Auditorium", "capacity": 150, "registeredCount": 0},
    {"eventId": "hackathon-fall", "eventName": "Fall Hackathon", "eventDate": "2026-10-03",
     "location": "Innovation Lab", "capacity": 80, "registeredCount": 0},
    {"eventId": "alumni-mixer", "eventName": "Alumni Networking Mixer", "eventDate": "2026-11-20",
     "location": "Grand Hall", "capacity": 60, "registeredCount": 0},
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", required=True, help="DynamoDB Events table name")
    parser.add_argument("--region", default="us-east-1")
    args = parser.parse_args()

    ddb = boto3.resource("dynamodb", region_name=args.region)
    table = ddb.Table(args.table)

    with table.batch_writer() as batch:
        for item in SAMPLE_EVENTS:
            batch.put_item(Item=item)

    print(f"Seeded {len(SAMPLE_EVENTS)} events into {args.table}")


if __name__ == "__main__":
    main()
