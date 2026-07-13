import json
from datetime import datetime, timezone
from boto3.dynamodb.types import TypeDeserializer

_deserializer = TypeDeserializer()


def response(status_code: int, body=None) -> dict:
    resp = {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
    }
    if status_code != 204:
        resp["body"] = json.dumps(body, default=str)
    return resp


def get_user_id(event: dict) -> str:
    return event["requestContext"]["authorizer"]["claims"]["sub"]


def iso8601_from_epoch(epoch_seconds: int) -> str:
    dt = datetime.fromtimestamp(epoch_seconds, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def deserialize_dynamodb_item(item: dict) -> dict:
    return {k: _deserializer.deserialize(v) for k, v in item.items()}
