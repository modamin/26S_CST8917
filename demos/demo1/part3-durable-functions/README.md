# Part 3 — Durable Functions orchestration

The **same** extract → clean → join → load pipeline as Part 2, but coordinated by
a single Durable Functions **orchestrator** instead of a web of queue triggers.

```
POST /api/start ─► run_pipeline (orchestrator)
                       ├─ extract_activity
                       ├─ clean_activity   (with retry)
                       ├─ join_activity    (with retry)
                       └─ load_activity    (with retry) ─► gold.customer_sales_summary
```

## Run

Durable Functions uses Azure Storage for its state, so **Azurite** must be running:

```bash
azurite          # in a separate terminal

cp local.settings.json.example local.settings.json   # fill in SqlOdbcConnectionString
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
func start
```

## Try it

```bash
curl -X POST http://localhost:7071/api/start
```

The response is a set of **management URLs**. Poll `statusQueryGetUri` to watch
the orchestration progress and see the final output:

```bash
curl "<statusQueryGetUri from the response>"
# runtimeStatus moves Running -> Completed, with the orchestrator's return value
```

Then verify the gold table:

```bash
sqlcmd -S <server> -d <db> -U <user> -P <pwd> -i ../sql/03_verify.sql
```

## What to point out in the demo

- **The whole flow is one function.** `run_pipeline` reads top to bottom; to
  reorder or insert a step you edit one place — contrast with Part 2's
  queue-name-per-function wiring.
- **Data flows as return values.** `extract_activity`'s result is passed straight
  into `clean_activity` — no queue messages, no payload threading.
- **Retries are declarative.** `RetryOptions(... max_number_of_attempts=3)` plus
  `call_activity_with_retry` — the runtime handles backoff and replay.
- **State is first-class.** One `instance_id`, queryable status endpoints. You can
  see exactly where a run is without spelunking through queues.
- The transformation SQL ([pipeline_sql.py](pipeline_sql.py)) is byte-for-byte the
  same as Part 2 — **only the orchestration changed.** That's the whole point.
