import json
import os
from datetime import datetime, timezone, timedelta

import boto3

from colors import ALLOWED_COLORS
from locations import ALL_LOCATIONS, VALID_LOCATION_IDS
from vehicles import is_valid_vehicle

TABLE_NAME = os.environ["TABLE_NAME"]
SIGHTING_CAP = 3

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "https://mitsumap.com",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
}


def _error(code, message, extra=None):
    body = {"error": message}
    if extra:
        body.update(extra)
    return {"statusCode": code, "headers": CORS_HEADERS, "body": json.dumps(body)}


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
    color = str(body.get("color", "")).upper()

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

    if color not in ALLOWED_COLORS:
        return _error(400, f"Invalid color — must be one of: {', '.join(sorted(ALLOWED_COLORS))}")

    location = next(loc for loc in ALL_LOCATIONS[chain] if loc["id"] == location_id)

    now = datetime.now(timezone.utc)
    ttl = int((now + timedelta(days=90)).timestamp())

    pk = f"{chain}#{location_id}"
    sk = f"SUBMISSION#{make}#{model}#{year}#{color}"

    table = boto3.resource("dynamodb").Table(TABLE_NAME)
    try:
        response = table.update_item(
            Key={"pk": pk, "sk": sk},
            UpdateExpression=(
                "SET chain = if_not_exists(chain, :chain),"
                " location_id = if_not_exists(location_id, :loc_id),"
                " location_name = if_not_exists(location_name, :loc_name),"
                " address = if_not_exists(address, :address),"
                " #mk = if_not_exists(#mk, :make),"
                " #mo = if_not_exists(#mo, :model),"
                " #yr = if_not_exists(#yr, :year),"
                " color = if_not_exists(color, :color),"
                " submitted_at = :submitted_at,"
                " #t = :ttl"
                " ADD sighting_count :one"
            ),
            ConditionExpression="attribute_not_exists(sighting_count) OR sighting_count < :cap",
            ExpressionAttributeNames={
                "#mk": "make",
                "#mo": "model",
                "#yr": "year",
                "#t": "ttl",
            },
            ExpressionAttributeValues={
                ":chain": chain,
                ":loc_id": location_id,
                ":loc_name": location["name"],
                ":address": location["address"],
                ":make": make,
                ":model": model,
                ":year": year,
                ":color": color,
                ":submitted_at": now.isoformat(),
                ":ttl": ttl,
                ":one": 1,
                ":cap": SIGHTING_CAP,
            },
            ReturnValues="UPDATED_NEW",
        )
    except table.meta.client.exceptions.ConditionalCheckFailedException:
        return _error(
            409,
            f"This vehicle has already been reported {SIGHTING_CAP} times at this location. "
            "Use the Still There or It's Gone buttons to update its status.",
            {"capped": True},
        )

    sighting_count = int(response["Attributes"].get("sighting_count", 1))

    item = {
        "pk": pk,
        "sk": sk,
        "chain": chain,
        "location_id": location_id,
        "location_name": location["name"],
        "address": location["address"],
        "make": make,
        "model": model,
        "year": year,
        "color": color,
        "submitted_at": now.isoformat(),
        "sighting_count": sighting_count,
        "ttl": ttl,
    }

    return {
        "statusCode": 201,
        "headers": CORS_HEADERS,
        "body": json.dumps(item),
    }
