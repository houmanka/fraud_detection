Batch Ingestion Scope:
1. we have an event handler which listening to a Pub/Sub event 
2. This event would be coming from a GCS bucket when a CSV file gets dropped in there
3. Event handler would trigger the BatchIngestion workflow
4. BatchIngestion workflow would get input argument (I assumed the path to the file as the input argument)
5. then workflow would have activity `download_file` as stream which it would read the content of the file
6. another activity it will go through each line of the CSV file and extract get the user id, and user email from the csv
7. another activity add the user id and email to the user tables (postgres in docker)
8. another activity would call an endpoint to notify a user id been imported
9. file data must be processed in parallel
10. Workflow exposes signals (e.g. pause, resume, cancel, set_parallelism) so an external caller (the event handler / an operator CLI) 
can control a running import; the workflow waits on internal state (pause flag, concurrency level) and reacts to incoming signals while continuing progress.


Yes, this pattern is doable and aligns well with how Standalone Activities are designed to work.

Here's how it would fit together:

1. **Your event handler is a Standalone Activity** — it receives an event, processes it (e.g., validates, transforms, enriches the data), and then uses the Temporal Client to start a Workflow.
2. **The Workflow is triggered from within the Activity** using the Temporal Client directly (not child workflow APIs). [[Starting Workflow from Activity](https://temporalio.slack.com/archives/CTT84RS0P/p1685120544066909?thread_ts=1685120544.066909&cid=CTT84RS0P)]

This is a natural fit for Standalone Activities, which are explicitly designed for **durable job processing use cases** like processing a webhook or executing a single function reliably — which is essentially what an event handler does. [[Standalone Activity](https://docs.temporal.io/standalone-activity)]

Project subject:

Customer support / fraud reports (best for embeddings + RAG)
Columns:
    case_id, user_id, created_at, channel, subject, description, category (optional), email
AI uses:
    embed subject+description into a vector DB (Pinecone) for similarity search (“find similar cases”)
    classify category/priority
    extract entities (merchant names, phone numbers, addresses) + PII scan
    RAG: retrieve policy docs + similar past cases to draft an explanation/recommendation









A rough sketch in Python:

```python
from temporalio import activity
from temporalio.client import Client

@activity.defn
async def handle_event(event: MyEvent) -> None:
    # 1. Process the event
    processed_data = do_something_with(event)

    # 2. Trigger a Temporal Workflow using the client
    client = await Client.connect("localhost:7233")
    await client.start_workflow(
        MyWorkflow.run,
        processed_data,
        id=f"workflow-for-{event.id}",
        task_queue="my-workflow-task-queue",
    )
```

A few things to keep in mind:

- **Use the Temporal Client** inside the Activity to start the Workflow — do not use `execute_child_workflow()`, which is only valid inside a Workflow Definition. [[Child Workflow from Activity](https://temporalio.slack.com/archives/CTT84RS0P/p1685120544066909?thread_ts=1685120544.066909&cid=CTT84RS0P)]
- The Workflow started this way will be an **independent top-level Workflow Execution**, not a child workflow.
- If the Activity does non-trivial work before starting the Workflow, make sure to **heartbeat** so Temporal knows it's still alive. [[Standalone Activity](https://docs.temporal.io/standalone-activity)]
- The same Activity function can also be reused inside a Workflow later if your needs evolve — no Worker code changes required. [[Standalone Activity](https://docs.temporal.io/standalone-activity)]

So yes — event handler as a Standalone Activity → process event → trigger Workflow is a clean and well-supported pattern in Temporal.


---------- 
## Pub sub event simulation:
    docker compose up -d pubsub

One time setup:
```commandline
export PUBSUB_EMULATOR_HOST=localhost:8085
export GOOGLE_CLOUD_PROJECT=local

uv run python ./localdev/pubsub_emulator_tools.py create-topic --topic object-created
uv run python ./localdev/pubsub_emulator_tools.py create-sub --topic object-created --subscription object-created-sub
```

How to publish an event:
First copy and paste `sample.csv` into a folder i.e: `data/inbox`
```commandline
export PUBSUB_EMULATOR_HOST=localhost:8085
export GOOGLE_CLOUD_PROJECT=local

uv run python ./localdev/pubsub_emulator_tools.py publish \
  --topic object-created \
  --json '{"provider":"local","path":"data/inbox/users.csv","eventType":"ObjectCreated"}'
```

How to listen to an event: (just to make sure you get what you sent)
```commandline
export PUBSUB_EMULATOR_HOST=localhost:8085
export GOOGLE_CLOUD_PROJECT=local

uv run python ./localdev/pubsub_subscriber.py --subscription object-created-sub
```

How to run the MCP
pii_classify: 
location: `cd ./localdev/mcp/mcp_pii_server`
```commandline
source .venv/bin/activate
fastmcp run pii_classify.py:mcp --transport http --host 127.0.0.1 --port 8090
```

