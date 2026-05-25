import asyncio
from concurrent.futures import ThreadPoolExecutor

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from cloud_storage import local_cloud
from cloud_storage.registry import build_cloud_storage, CloudStorageKind
from config import Config
from event_handler.event_handler import ingestion_handler
from workflow.activities.download import DownloadActivities
from workflow.ingestion import IngestionWorkflow


async def main():
    connect_config = ClientConfig.load_client_connect_config()
    connect_config.setdefault("target_host", "localhost:7233")

    conf = Config()

    # create cloud storage client
    cloud_storage = build_cloud_storage(kind=CloudStorageKind.LocalCloud ,config=conf)
    download_activities = DownloadActivities(cloud_storage=cloud_storage)


    client = await Client.connect(**connect_config)
    worker = Worker(
        client,
        task_queue="INGESTION_QUEUE",
        activities=[ingestion_handler, download_activities.download_activity],
        workflows=[IngestionWorkflow],
        activity_executor=ThreadPoolExecutor(5),
    )
    print("worker running...", end="", flush=True)
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())