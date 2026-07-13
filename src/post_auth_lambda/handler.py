import json
import logging
import os

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sns = boto3.client("sns")
SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]


def _is_already_subscribed(email: str) -> bool:
    paginator = sns.get_paginator("list_subscriptions_by_topic")
    for page in paginator.paginate(TopicArn=SNS_TOPIC_ARN):
        for sub in page["Subscriptions"]:
            if sub["Protocol"] == "email" and sub["Endpoint"] == email:
                return True
    return False


def lambda_handler(event, context):
    attrs = event["request"]["userAttributes"]
    user_sub = attrs["sub"]
    email = attrs["email"]

    logger.info("PostAuthentication for user sub=%s email=%s", user_sub, email)

    if _is_already_subscribed(email):
        logger.info("Email %s already subscribed, skipping", email)
        return event

    sns.subscribe(
        TopicArn=SNS_TOPIC_ARN,
        Protocol="email",
        Endpoint=email,
        Attributes={
            "FilterPolicy": json.dumps({"userId": [user_sub]}),
            "FilterPolicyScope": "MessageAttributes",
        },
    )
    logger.info("Subscribed %s to SNS topic with filter userId=%s", email, user_sub)
    return event
