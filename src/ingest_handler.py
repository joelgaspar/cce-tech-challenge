import json
import os
import uuid
from datetime import datetime, timezone

import boto3

table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])


def handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return response(400, {"message": "Invalid JSON"})

    item_id = str(uuid.uuid4())
    table.put_item(Item={
        "id": item_id,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "payload": body,
    })
    return response(201, {"id": item_id})


def response(status_code, body):
    return {"statusCode": status_code, "body": json.dumps(body)}
