import argparse
import asyncio
import json
import os
from typing import Any

from google.cloud import pubsub_v1
from datetime import timedelta

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from event_handler.event_handler import FileInput, ingestion_handler


def _env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None or value == "":
        raise SystemExit(f"Missing required env var: {name}")
    return value


async def _handle_message(
    *,
    message: pubsub_v1.subscriber.message.Message,
    client: Client,
) -> None:
    try:
        data = message.data.decode("utf-8")
        payload: Any = json.loads(data)
        print(json.dumps(payload, indent=2, ensure_ascii=False))

        await client.execute_activity(
            ingestion_handler,
            args=[
                FileInput(
                    provider=payload["provider"],
                    path=payload["path"],
                    event_type=payload["eventType"],
                )
            ],
            id="ingestion_handler_stand_alone_activity",
            task_queue="INGESTION_QUEUE",
            start_to_close_timeout=timedelta(seconds=100),
        )

        message.ack()
    except Exception as e:
        print(f"handler error: {e}")
        # For local dev, prefer nack to allow redelivery. If you want "at-most-once",
        # replace with message.ack().
        message.nack()


async def main() -> None:
    parser = argparse.ArgumentParser(description="Local Pub/Sub emulator subscriber (prints messages).")
    parser.add_argument("--project", default=os.environ.get("GOOGLE_CLOUD_PROJECT", "local"))
    parser.add_argument("--subscription", default="object-created-sub")
    args = parser.parse_args()

    _env("PUBSUB_EMULATOR_HOST")

    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(args.project, args.subscription)

    loop = asyncio.get_running_loop()
    stop = loop.create_future()

    # client connection
    connect_config = ClientConfig.load_client_connect_config()
    connect_config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**connect_config)

    def callback(message: pubsub_v1.subscriber.message.Message) -> None:
        asyncio.run_coroutine_threadsafe(_handle_message(message=message, client=client), loop)

    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    print(f"subscribed to {subscription_path} (ctrl+c to stop)")

    try:
        await stop
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        streaming_pull_future.cancel()
        subscriber.close()


if __name__ == "__main__":
    asyncio.run(main())
