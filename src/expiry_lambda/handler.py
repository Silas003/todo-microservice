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

    subject = f'Task Expired — "{description}"' if description else "Task Expired"
    message = (
        f"Hello,\n\n"
        f"Your task has expired:\n\n"
        f"  Task:     {description or '(no description)'}\n"
        f"  Task ID:  {task_id}\n"
        f"  Status:   Expired\n\n"
        f"This is an automated notification.\n"
        f"Do not reply to this email."
    )

    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject=subject,
        Message=message,
        MessageAttributes={
            "userId": {
                "DataType": "String",
                "StringValue": user_id,
            }
        },
    )
    logger.info("Published expiry notification for task %s to user %s", task_id, user_id)
