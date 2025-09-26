"""
Functions for sending messages to Slack.
"""

import json
import logging

from slack_sdk.webhook import WebhookClient

from fraim.core.history import EventRecord, History
from fraim.core.utils.retry import with_retry

logger = logging.getLogger(__name__)


def send_message(history: History, webhook_url: str, message: str) -> None:
    """
    Sends a message to a Slack channel using a webhook URL.

    Args:
        webhook_url: The Slack webhook URL to send the message to
        message: The message content to send
        channel: Optional channel to send to (if webhook supports it)

    Raises:
        RuntimeError: If the webhook URL is invalid or the message fails to send
    """
    logger.info("Sending message to Slack webhook")
    history.append_record(EventRecord(description="Sending message to Slack"))

    if not webhook_url or not webhook_url.strip():
        logger.error("Slack webhook URL is required but not provided")
        raise RuntimeError("Slack webhook URL is required")

    if not message or not message.strip():
        logger.warning("Empty message provided, skipping Slack notification")
        return

    try:
        webhook = WebhookClient(webhook_url)

        # Send the message (message should already be formatted for Slack)
        response = with_retry(webhook.send)(**json.loads(message))

        if response.status_code == 200:
            logger.info("Successfully sent message to Slack")
        else:
            logger.error(f"Failed to send Slack message: {response.status_code} - {response.body}")
            raise RuntimeError(f"Slack API error: {response.status_code} - {response.body}")

    except Exception as e:
        logger.error(f"Failed to send message to Slack: {e!s}")
        raise RuntimeError(f"Failed to send message to Slack: {e!s}") from e
