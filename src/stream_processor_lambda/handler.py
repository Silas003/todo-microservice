import json
import logging
import os

import boto3

try:
    from utils import deserialize_dynamodb_item
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../layers/common/python'))
    from utils import deserialize_dynamodb_item

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sqs = boto3.client("sqs")
SQS_QUEUE_URL = os.environ["SQS_QUEUE_URL"]


def _should_cancel(record: dict) -> tuple[bool, str | None]:
    event_name = record["eventName"]
    dynamodb_data = record["dynamodb"]

    if event_name == "REMOVE":
        old_image = dynamodb_data.get("OldImage", {})
        old_item = deserialize_dynamodb_item(old_image)
        if old_item.get("Status") == "Pending":
            return True, old_item.get("TaskId")

    elif event_name == "MODIFY":
        new_image = dynamodb_data.get("NewImage", {})
        old_image = dynamodb_data.get("OldImage", {})
        new_item = deserialize_dynamodb_item(new_image)
        old_item = deserialize_dynamodb_item(old_image)
        if new_item.get("Status") == "Completed" and old_item.get("Status") != "Completed":
            return True, new_item.get("TaskId")

    return False, None


def lambda_handler(event, context):
    for record in event["Records"]:
        sequence_number = record["dynamodb"]["SequenceNumber"]
        should_cancel, task_id = _should_cancel(record)

        if not should_cancel or not task_id:
            continue

        logger.info("Sending cancellation for task %s (seq=%s)", task_id, sequence_number)
        sqs.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps({"taskId": task_id}),
            MessageGroupId=task_id,
            MessageDeduplicationId=sequence_number,
        )
