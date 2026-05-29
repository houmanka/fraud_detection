# Complaint Ingestion Pipeline

A bank drops 50,000 customer complaint reports into a cloud bucket every night.
This project processes them durably, safely, and with an AI pipeline — using Temporal.

---

## What it does

1. Listens for a Pub/Sub event when a new CSV file lands in the bucket
2. Triggers a Temporal workflow to process the file
3. Streams the file line-by-line (no full load into memory)
4. Scans each complaint for PII using an MCP tool, then redacts it
5. Classifies each complaint using a trained ML model
6. Persists each complaint and its classification to Postgres
7. Vectorises each complaint and pushes it to a Vector DB (Pinecone)
8. Archives the source file after processing

---

## Functional Requirements

| # | Requirement |
|---|---|
| FR1 | System gets notified when a new file is available (Pub/Sub) |
| FR2 | System starts a Temporal workflow to process the file |
| FR3 | System archives the source file after streaming it (moves to a separate bucket/folder) |
| FR4 | No PII leaks — each row is scanned and redacted before storage |
| FR5 | Each complaint is classified (e.g. billing, service, account) |
| FR6 | Each complaint is stored in Postgres with its classification |
| FR7 | A redacted, vectorised version of each complaint is pushed to a Vector DB |
| FR8 | System can query the Vector DB and return the top-5 similar complaints |

---

## Non-Functional Requirements

| # | Requirement |
|---|---|
| NFR1 | **Consistency** — vectors must always be generated with the same embedding model |
| NFR2 | **Resilience** — if one row fails, only that row retries; the entire batch is not re-processed |
| NFR3 | **Backpressure** — row processing runs with a configurable concurrency limit; Temporal limits are respected |
| NFR4 | **At-least-once delivery** — if the system is down when the file lands, Pub/Sub will redeliver the event |

---

## Data Model

```text
files
  id          PK
  file_name
  archived_at

complaints
  id                    PK
  case_id               PK (idempotency key — from the source CSV, unique per complaint)
  text_redacted         PII has been removed before storage
  embedded              bool — true once pushed to Pinecone; prevents re-embedding on retry
  classification_id     FK → classifications
  file_id               FK → files

classifications
  id          PK
  name                  e.g. "billing", "service", "account"
```

> Raw complaint text is never stored. Only the redacted version is persisted.

---

## Architecture

```
Cloud bucket (CSV dropped)
        ↓  ObjectCreated event
Google Pub/Sub
        ↓
subscriber.py           listens to Pub/Sub
        ↓
[Standalone Activity]   ingestion_handler — starts IngestionWorkflow via Temporal client
        ↓
[Workflow]              IngestionWorkflow
        ├─ Activity: ingest_complaints   streams CSV line-by-line; per row:
        │                                  1. skip if case_id already in Postgres (idempotency)
        │                                  2. PII scan via MCP tool, redact in memory
        │                                  3. classify via ML model
        │                                  4. write redacted complaint + classification to Postgres
        │                                heartbeats row offset — on retry, resumes from last row
        │
        ├─ Activity: vectorise_and_push  reads rows where vectorised = false from Postgres,
        │                                embeds redacted text, pushes to Pinecone,
        │                                marks vectorised = true
        │
        └─ Activity: archive_file        moves source file to archive location
```

`ingest_complaints` handles streaming, PII, classification, and persistence in a single activity
so that raw complaint text never leaves memory and is never written anywhere before redaction.

---

## Local Development

### Prerequisites

- Docker
- [uv](https://docs.astral.sh/uv/)
- Temporal dev server (`temporal server start-dev`)

### Start the Pub/Sub emulator

```bash
docker compose up -d pubsub
```

### One-time Pub/Sub setup

```bash
export PUBSUB_EMULATOR_HOST=localhost:8085
export GOOGLE_CLOUD_PROJECT=local

uv run python ./localdev/pubsub_emulator_tools.py create-topic --topic object-created
uv run python ./localdev/pubsub_emulator_tools.py create-sub --topic object-created --subscription object-created-sub
```

### Publish a test event

Copy a CSV file into `data/inbox/`, then:

```bash
export PUBSUB_EMULATOR_HOST=localhost:8085
export GOOGLE_CLOUD_PROJECT=local

uv run python ./localdev/pubsub_emulator_tools.py publish \
  --topic object-created \
  --json '{"provider":"local","path":"data/inbox/users.csv","eventType":"ObjectCreated"}'
```

### Verify the event was published

```bash
export PUBSUB_EMULATOR_HOST=localhost:8085
export GOOGLE_CLOUD_PROJECT=local

uv run python ./localdev/pubsub_subscriber.py --subscription object-created-sub
```

### Start the MCP PII server

```bash
cd ./localdev/mcp/mcp_pii_server
source .venv/bin/activate
fastmcp run pii_classify.py:mcp --transport http --host 127.0.0.1 --port 8090
```
