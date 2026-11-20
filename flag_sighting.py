import json
import os
from datetime import datetime, timezone, timedelta

import boto3
from boto3.dynamodb.conditions import Attr

TABLE_NAME = os.environ["TABLE_NAME"]

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "https://mitsumap.com",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
}

VALID_FLAGS = {"still_there", "its_gone"}


def _error(code, message):
    return {"statusCode": code, "headers": CORS_HEADERS, "body": json.dumps({"error": message})}


def lambda_handler(event, context):
    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": ""}

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _error(400, "Invalid JSON")

    pk = body.get("pk")
    sk = body.get("sk")
    flag = body.get("flag")

    if not pk or not sk:
        return _error(400, "pk and sk are required")
    if flag not in VALID_FLAGS:
        return _error(400, f"flag must be one of: {sorted(VALID_FLAGS)}")

    now = datetime.now(timezone.utc)
    ttl = int((now + timedelta(days=90)).timestamp())
    flag_field = "still_there_at" if flag == "still_there" else "its_gone_at"
    count_field = "still_there_count" if flag == "still_there" else "its_gone_count"

    table = boto3.resource("dynamodb").Table(TABLE_NAME)
    try:
        response = table.update_item(
            Key={"pk": pk, "sk": sk},
            UpdateExpression=f"SET {flag_field} = :ts, #t = :ttl ADD {count_field} :one",
            ExpressionAttributeNames={"#t": "ttl"},
            ExpressionAttributeValues={":ts": now.isoformat(), ":ttl": ttl, ":one": 1},
            ConditionExpression=Attr("pk").exists(),
            ReturnValues="ALL_NEW",
        )
    except table.meta.client.exceptions.ConditionalCheckFailedException:
        return _error(404, "Submission not found")

    return {
        "statusCode": 200,
        "headers": CORS_HEADERS,
        "body": json.dumps({"message": "Flag updated", "item": response["Attributes"]}, default=str),
    }
