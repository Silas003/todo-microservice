import json
import logging
import os

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])
sns = boto3.client("sns")
SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]


def lambda_handler(event, context):
    task_id = event["taskId"]
    user_id = event["userId"]
    pk = f"USER#{user_id}"
    sk = f"TASK#{task_id}"

    logger.info("Processing expiry for task %s user %s", task_id, user_id)

    try:
        result = table.update_item(
            Key={"PK": pk, "SK": sk},
            UpdateExpression="SET #s = :expired",
            ConditionExpression="#s = :pending",
            ExpressionAttributeNames={"#s": "Status"},
            ExpressionAttributeValues={":expired": "Expired", ":pending": "Pending"},
            ReturnValues="ALL_NEW",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            logger.info("Task %s is not Pending (already Completed/Expired/Deleted), skipping SNS", task_id)
            return
        raise

    item = result.get("Attributes", {})
    description = item.get("Description", "")

    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject="Task Expired",
        Message=json.dumps({
            "message": f"Your task has expired: {description}",
            "taskId": task_id,
            "description": description,
        }),
        MessageAttributes={
            "userId": {
                "DataType": "String",
                "StringValue": user_id,
            }
        },
    )
    logger.info("Published expiry notification for task %s to user %s", task_id, user_id)
