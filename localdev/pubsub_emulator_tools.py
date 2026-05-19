import argparse
import json
import os
from typing import Any

from google.api_core.exceptions import AlreadyExists
from google.cloud import pubsub_v1


def _env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None or value == "":
        raise SystemExit(f"Missing required env var: {name}")
    return value


def _publisher(project: str) -> tuple[pubsub_v1.PublisherClient, str]:
    client = pubsub_v1.PublisherClient()
    return client, project


def _subscriber(project: str) -> tuple[pubsub_v1.SubscriberClient, str]:
    client = pubsub_v1.SubscriberClient()
    return client, project


def cmd_create_topic(args: argparse.Namespace) -> None:
    publisher, project = _publisher(args.project)
    topic_path = publisher.topic_path(project, args.topic)
    try:
        publisher.create_topic(request={"name": topic_path})
        print(f"created topic: {topic_path}")
    except AlreadyExists:
        print(f"topic exists: {topic_path}")


def cmd_create_subscription(args: argparse.Namespace) -> None:
    subscriber, project = _subscriber(args.project)
    topic_path = subscriber.topic_path(project, args.topic)
    sub_path = subscriber.subscription_path(project, args.subscription)
    try:
        subscriber.create_subscription(request={"name": sub_path, "topic": topic_path})
        print(f"created subscription: {sub_path}")
    except AlreadyExists:
        print(f"subscription exists: {sub_path}")


def cmd_publish(args: argparse.Namespace) -> None:
    publisher, project = _publisher(args.project)
    topic_path = publisher.topic_path(project, args.topic)

    message: Any
    if args.json:
        message = json.loads(args.json)
    else:
        message = {}

    payload = json.dumps(message, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    publisher.publish(topic_path, payload).result(timeout=5)
    print("published")


def cmd_pull(args: argparse.Namespace) -> None:
    subscriber, project = _subscriber(args.project)
    sub_path = subscriber.subscription_path(project, args.subscription)

    response = subscriber.pull(request={"subscription": sub_path, "max_messages": args.limit}, timeout=5)
    if not response.received_messages:
        print("no messages")
        return

    ack_ids: list[str] = []
    for rm in response.received_messages:
        ack_ids.append(rm.ack_id)
        try:
            print(rm.message.data.decode("utf-8"))
        except Exception:
            print(rm.message.data)

    if args.ack:
        subscriber.acknowledge(request={"subscription": sub_path, "ack_ids": ack_ids})
        print(f"acked {len(ack_ids)}")


def main() -> None:
    default_project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("PUBSUB_PROJECT_ID") or "local"

    parser = argparse.ArgumentParser(description="Pub/Sub emulator helper tools (no gcloud required).")
    parser.add_argument("--project", default=default_project)

    subparsers = parser.add_subparsers(required=True)

    p = subparsers.add_parser("create-topic")
    p.add_argument("--topic", required=True)
    p.set_defaults(func=cmd_create_topic)

    p = subparsers.add_parser("create-sub")
    p.add_argument("--topic", required=True)
    p.add_argument("--subscription", required=True)
    p.set_defaults(func=cmd_create_subscription)

    p = subparsers.add_parser("publish")
    p.add_argument("--topic", required=True)
    p.add_argument("--json", required=False, help="JSON string payload to publish as message data")
    p.set_defaults(func=cmd_publish)

    p = subparsers.add_parser("pull")
    p.add_argument("--subscription", required=True)
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--ack", action="store_true")
    p.set_defaults(func=cmd_pull)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    # Requires: PUBSUB_EMULATOR_HOST (e.g. localhost:8085)
    # Optional: GOOGLE_CLOUD_PROJECT / PUBSUB_PROJECT_ID
    _env("PUBSUB_EMULATOR_HOST")
    main()

