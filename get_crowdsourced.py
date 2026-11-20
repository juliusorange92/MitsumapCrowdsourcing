import decimal
import json
import os

import boto3

TABLE_NAME = os.environ["TABLE_NAME"]

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "https://mitsumap.com",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
}


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            f = float(obj)
            return int(f) if f == int(f) else f
        return super().default(obj)


def lambda_handler(event, context):
    table = boto3.resource("dynamodb").Table(TABLE_NAME)
    items = []
    response = table.scan()
    items.extend(response.get("Items", []))
    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))
    return {
        "statusCode": 200,
        "headers": CORS_HEADERS,
        "body": json.dumps(items, cls=DecimalEncoder),
    }
