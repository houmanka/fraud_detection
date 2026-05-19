import argparse
import asyncio
import json
import os
from typing import Any

from google.cloud import pubsub_v1


def _env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None or value == "":
        raise SystemExit(f"Missing required env var: {name}")
    return value


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

    def callback(message: pubsub_v1.subscriber.message.Message) -> None:
        try:
            data = message.data.decode("utf-8")
            payload: Any = json.loads(data)
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        except Exception:
            print(message.data)
        finally:
            message.ack()

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

