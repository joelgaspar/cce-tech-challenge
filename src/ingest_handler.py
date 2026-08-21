"""Ingest Lambda: persists a JSON payload received via POST /items into DynamoDB."""
import json
import os
import uuid
from datetime import datetime, timezone

import boto3

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


def handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"message": "Request body must be valid JSON"})

    if not isinstance(body, dict):
        return _response(400, {"message": "Request body must be a JSON object"})

    item = {
        "id": str(uuid.uuid4()),
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "payload": body,
    }
    table.put_item(Item=item)

    return _response(201, {"id": item["id"]})


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
