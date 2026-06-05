# Part 5 — Durable Functions **error handling**

The same failure scenario as Part 4, but with Durable Functions. The orchestrator
declares the *policy*; the framework supplies the machinery.

| Concern | Part 4 (manual) | Part 5 (Durable) |
|---|---|---|
| **Retries** | `maxDequeueCount` + try/except in every function | `call_activity_with_retry(..., RetryOptions)` — one line per call |
| **Run state** | home-made `staging.pipeline_runs` table | persisted by the runtime automatically |
| **Status** | custom `GET /api/status/{id}` route | built-in `statusQueryGetUri` |
| **Compensation** | poison-queue handler per queue | one `try/except` around the whole flow |
| **Failure model** | message bounces to `*-poison` | activity error propagates to the orchestrator |

## Run

```bash
azurite          # separate terminal — Durable state lives here

cp local.settings.json.example local.settings.json   # fill in SqlOdbcConnectionString
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
func start
```

(No extra SQL script needed — Durable doesn't use the `pipeline_runs` table.)

## Try it — happy path

```bash
curl -X POST http://localhost:7071/api/start
# follow the statusQueryGetUri from the response
curl "<statusQueryGetUri>"
# runtimeStatus: Completed, output: {"status":"completed", ...}
```

## Try it — inject a failure

```bash
curl -X POST "http://localhost:7071/api/start?fail_at=join"
curl "<statusQueryGetUri>"
```

What you'll observe in the console and status payload:

1. `extract` and `clean` succeed.
2. `join_activity` throws → **retried 3 times** per `RetryOptions`
   (`customStatus` shows `joining` throughout).
3. Retries exhausted → the error propagates into the orchestrator's `except`.
4. `customStatus` → `compensating`; `compensate_activity` clears partial work.
5. Orchestration ends with `runtimeStatus: Completed` and
   `output: {"status": "failed", "error": "Injected failure ..."}`.

> The orchestration completes *successfully* because we **caught** the error and
> returned a structured failure. If you instead let it propagate (remove the
> `try/except`), `runtimeStatus` becomes `Failed` and Durable records the
> exception and stack for you — no logging code required.

## What to point out in the demo

- **Policy, not plumbing.** Retry counts, backoff, and the failure path are
  expressed once in the orchestrator. There are no poison queues and no
  bookkeeping table.
- **State is automatic.** The same `statusQueryGetUri` that shows progress also
  shows the final outcome and the `customStatus` you set along the way.
- **Compensation is just code in the orchestrator** — a `try/except` that calls a
  compensating activity. Compare with Part 4's four separate poison handlers.

Put this side-by-side with [Part 4](../part4-manual-error-handling/) to make the
trade-off concrete: same resilience, far less code you have to own.
