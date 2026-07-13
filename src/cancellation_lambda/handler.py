import json
import logging
import os

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

scheduler = boto3.client("scheduler")
SCHEDULER_GROUP = os.environ["SCHEDULER_GROUP"]


def _cancel_schedule(task_id: str):
    schedule_name = f"expiry-{task_id}"
    try:
        scheduler.delete_schedule(Name=schedule_name, GroupName=SCHEDULER_GROUP)
        logger.info("Deleted schedule %s", schedule_name)
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            logger.info("Schedule %s already deleted or never existed, treating as success", schedule_name)
            return
        raise


def lambda_handler(event, context):
    batch_item_failures = []

    for record in event["Records"]:
        message_id = record["messageId"]
        try:
            body = json.loads(record["body"])
            task_id = body["taskId"]
            logger.info("Processing cancellation for task %s", task_id)
            _cancel_schedule(task_id)
        except Exception:
            logger.exception("Failed to process cancellation for message %s", message_id)
            batch_item_failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": batch_item_failures}
