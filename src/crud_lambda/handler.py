import json
import logging
import os
import time
import uuid

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

try:
    from utils import get_user_id, iso8601_from_epoch, response
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../layers/common/python'))
    from utils import get_user_id, iso8601_from_epoch, response

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_REQUIRED_ENV = ["TABLE_NAME", "SCHEDULER_GROUP", "SCHEDULER_ROLE_ARN", "EXPIRY_LAMBDA_ARN"]
_missing = [v for v in _REQUIRED_ENV if not os.environ.get(v)]
if _missing:
    raise RuntimeError(f"Missing required environment variables: {_missing}")

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])

scheduler = boto3.client("scheduler")
SCHEDULER_GROUP = os.environ["SCHEDULER_GROUP"]
SCHEDULER_ROLE_ARN = os.environ["SCHEDULER_ROLE_ARN"]
EXPIRY_LAMBDA_ARN = os.environ["EXPIRY_LAMBDA_ARN"]

DEFAULT_DEADLINE_OFFSET = 300  # 5 minutes


def _build_pk(user_id: str) -> str:
    return f"USER#{user_id}"


def _build_sk(task_id: str) -> str:
    return f"TASK#{task_id}"


def _create_expiry_schedule(task_id: str, user_id: str, deadline: int) -> str:
    schedule_name = f"expiry-{task_id}"
    scheduler.create_schedule(
        Name=schedule_name,
        GroupName=SCHEDULER_GROUP,
        ScheduleExpression=f"at({iso8601_from_epoch(deadline)})",
        FlexibleTimeWindow={"Mode": "OFF"},
        Target={
            "Arn": EXPIRY_LAMBDA_ARN,
            "RoleArn": SCHEDULER_ROLE_ARN,
            "Input": json.dumps({"taskId": task_id, "userId": user_id}),
        },
        ActionAfterCompletion="DELETE",
    )
    return schedule_name


def list_tasks(event):
    user_id = get_user_id(event)
    result = table.query(
        KeyConditionExpression=Key("PK").eq(_build_pk(user_id)) & Key("SK").begins_with("TASK#")
    )
    return response(200, result["Items"])


def create_task(event):
    user_id = get_user_id(event)
    body = json.loads(event.get("body") or "{}")

    task_id = str(uuid.uuid4())
    now = int(time.time())
    deadline = int(body.get("Deadline", now + DEFAULT_DEADLINE_OFFSET))

    schedule_name = _create_expiry_schedule(task_id, user_id, deadline)

    item = {
        "PK": _build_pk(user_id),
        "SK": _build_sk(task_id),
        "TaskId": task_id,
        "UserId": user_id,
        "Description": body.get("Description", ""),
        "Date": body.get("Date", ""),
        "Status": "Pending",
        "Deadline": deadline,
        "ScheduleName": schedule_name,
        "CreatedAt": now,
    }
    table.put_item(Item=item)
    logger.info("Created task %s for user %s with deadline %s", task_id, user_id, deadline)
    return response(201, item)


def get_task(event):
    user_id = get_user_id(event)
    task_id = event["pathParameters"]["taskId"]
    result = table.get_item(Key={"PK": _build_pk(user_id), "SK": _build_sk(task_id)})
    item = result.get("Item")
    if not item:
        return response(404, {"message": "Task not found"})
    return response(200, item)


def update_task(event):
    user_id = get_user_id(event)
    task_id = event["pathParameters"]["taskId"]
    body = json.loads(event.get("body") or "{}")

    allowed_fields = ["Description", "Date", "Status"]
    updates = {k: v for k, v in body.items() if k in allowed_fields}
    if not updates:
        return response(400, {"message": "No updatable fields provided"})

    update_parts = []
    expr_names = {}
    expr_values = {}
    for i, (field, value) in enumerate(updates.items()):
        placeholder = f"#f{i}"
        value_placeholder = f":v{i}"
        update_parts.append(f"{placeholder} = {value_placeholder}")
        expr_names[placeholder] = field
        expr_values[value_placeholder] = value

    expr_values[":updatedAt"] = int(time.time())
    update_parts.append("#updatedAt = :updatedAt")
    expr_names["#updatedAt"] = "UpdatedAt"

    try:
        result = table.update_item(
            Key={"PK": _build_pk(user_id), "SK": _build_sk(task_id)},
            UpdateExpression="SET " + ", ".join(update_parts),
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
            ReturnValues="ALL_NEW",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return response(404, {"message": "Task not found"})
        raise
    return response(200, result["Attributes"])


def delete_task(event):
    user_id = get_user_id(event)
    task_id = event["pathParameters"]["taskId"]
    table.delete_item(Key={"PK": _build_pk(user_id), "SK": _build_sk(task_id)})
    logger.info("Deleted task %s for user %s", task_id, user_id)
    return response(204, {})


ROUTES = {
    ("GET", "/tasks"): list_tasks,
    ("POST", "/tasks"): create_task,
    ("GET", "/tasks/{taskId}"): get_task,
    ("PUT", "/tasks/{taskId}"): update_task,
    ("DELETE", "/tasks/{taskId}"): delete_task,
}


def lambda_handler(event, context):
    method = event["httpMethod"]
    resource = event["resource"]
    logger.info("%s %s", method, resource)
    handler_fn = ROUTES.get((method, resource))
    if not handler_fn:
        return response(405, {"message": "Method not allowed"})
    try:
        return handler_fn(event)
    except Exception as e:
        logger.exception("Unhandled error in %s %s", method, resource)
        return response(500, {"message": "Internal server error"})
