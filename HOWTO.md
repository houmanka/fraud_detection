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

