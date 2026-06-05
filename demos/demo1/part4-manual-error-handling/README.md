# Part 4 — Manual chaining **with error handling**

Part 2 showed the happy path. Real pipelines fail mid-flight, so this part adds
everything you must hand-build when there is no orchestrator:

| Concern | How it's done here |
|---|---|
| **Retries** | `host.json` → `maxDequeueCount: 3`. A step that throws is retried automatically. |
| **Dead-lettering** | After retries are exhausted the runtime moves the message to `<queue>-poison`; a `*Poison` handler reacts. |
| **Run state** | We record progress/errors ourselves in `staging.pipeline_runs` (see [runstate.py](runstate.py)). |
| **Compensation** | The poison handler clears partial intermediates (placeholder for real rollback). |
| **Observability** | `GET /api/status/{run_id}` reads the home-made state table. |

## Prerequisites

Run the SQL scripts including the run-state table:

```bash
sqlcmd ... -i ../sql/01_create_schemas_and_tables.sql
sqlcmd ... -i ../sql/02_seed_sample_data.sql
sqlcmd ... -i ../sql/04_pipeline_runs.sql      # <-- needed by this part
```

## Run

```bash
azurite          # separate terminal — queues + poison queues live here

cp local.settings.json.example local.settings.json   # fill in SqlOdbcConnectionString
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
func start
```

## Try it — happy path

```bash
curl -X POST http://localhost:7071/api/start
# -> {"status":"started","run_id":"<id>","status_url":"/api/status/<id>"}

curl http://localhost:7071/api/status/<id>
# -> status: completed, current_step: load
```

## Try it — inject a failure

```bash
curl -X POST "http://localhost:7071/api/start?fail_at=join"
```

Watch the `func start` console:

1. `Extract` and `Clean` succeed.
2. `Join` throws → **retried 3 times** (you'll see attempts 1, 2, 3).
3. The runtime moves the message to `pipeline-join-poison`.
4. `JoinPoison` runs → marks the run **failed** and compensates.

Then check the state table:

```bash
curl http://localhost:7071/api/status/<id>
# -> status: failed, current_step: join, attempts: 3, last_error: "Injected failure ..."
```

## What to point out in the demo

- **You wrote all of it.** Retry count, poison handlers, a state table, a status
  endpoint, compensation — none of it is free. Every step needs the same
  try/except/record boilerplate.
- **Four poison handlers** — one per queue — because each queue dead-letters
  independently. More steps = more handlers.
- **Compensation is your problem.** Nothing automatically rolls back the work the
  earlier steps already committed; you reason about it by hand.

Part 5 does the same scenario with Durable Functions, where retries, state,
status, and a clean failure path are built in.
