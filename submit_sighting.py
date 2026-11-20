import json
import os
from datetime import datetime, timezone, timedelta

import boto3

from locations import ALL_LOCATIONS, VALID_LOCATION_IDS
from vehicles import is_valid_vehicle

TABLE_NAME = os.environ["TABLE_NAME"]

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "https://mitsumap.com",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
}


def _error(code, message):
    return {"statusCode": code, "headers": CORS_HEADERS, "body": json.dumps({"error": message})}


def lambda_handler(event, context):
    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": ""}

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _error(400, "Invalid JSON")

    chain = str(body.get("chain", "")).upper()
    location_id = str(body.get("location_id", ""))
    make = str(body.get("make", "")).upper()
    model = str(body.get("model", "")).upper()
    year_raw = body.get("year")

    if chain not in VALID_LOCATION_IDS:
        return _error(400, "Invalid chain — must be LKQ or PICKNPULL")
    if location_id not in VALID_LOCATION_IDS[chain]:
        return _error(400, f"Unknown location '{location_id}' for chain {chain}")

    try:
        year = int(year_raw)
    except (TypeError, ValueError):
        return _error(400, "year must be an integer")

    if not is_valid_vehicle(make, model, year):
        return _error(400, f"Invalid vehicle: {year} {make} {model}")

    location = next(loc for loc in ALL_LOCATIONS[chain] if loc["id"] == location_id)

    now = datetime.now(timezone.utc)
    ttl = int((now + timedelta(days=90)).timestamp())

    item = {
        "pk": f"{chain}#{location_id}",
        "sk": f"SUBMISSION#{make}#{model}#{year}",
        "chain": chain,
        "location_id": location_id,
        "location_name": location["name"],
        "address": location["address"],
        "make": make,
        "model": model,
        "year": year,
        "submitted_at": now.isoformat(),
        "ttl": ttl,
    }

    boto3.resource("dynamodb").Table(TABLE_NAME).put_item(Item=item)

    return {
        "statusCode": 201,
        "headers": CORS_HEADERS,
        "body": json.dumps(item),
    }
