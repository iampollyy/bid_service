import json
import logging
from datetime import datetime, timezone
from azure.servicebus import ServiceBusClient, ServiceBusMessage

from config import SERVICE_BUS_SEND_CONNECTION_STRING, QUEUE_NAME

logger = logging.getLogger(__name__)


class MessageSender:

    def __init__(self):
        self.connection_string = SERVICE_BUS_SEND_CONNECTION_STRING
        self.queue_name = QUEUE_NAME

    def send_message(self, event_type: str, data: dict) -> bool:
        message_body = {
            "eventType": event_type,
            "eventDateUTC": datetime.now(timezone.utc).isoformat(),
            "auctionId": data.get("auction_id"),
            "artworkId": data.get("artwork_id"),
            "bidId": data.get("bid_id"),
            "userId": data.get("user_id"),
            "amount": data.get("amount")
        }

        try:
            with ServiceBusClient.from_connection_string(
                self.connection_string
            ) as client:
                with client.get_queue_sender(
                    queue_name=self.queue_name
                ) as sender:
                    message = ServiceBusMessage(
                        body=json.dumps(message_body),
                        content_type="application/json",
                        subject=event_type
                    )
                    sender.send_messages(message)

            logger.info(f"Message sent: {event_type} | {message_body}")
            return True

        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False


message_sender = MessageSender()