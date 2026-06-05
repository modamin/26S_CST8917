# Demo 1 — Concepts Explained

This document explains, in depth, every concept that Demo 1 teaches and walks
through *how the code is written* in each part. It is meant to be read alongside
the code: [part1](part1-http-sql-binding/), [part2](part2-manual-chaining/),
[part3](part3-durable-functions/), [part4](part4-manual-error-handling/),
[part5](part5-durable-error-handling/), and the [sql/](sql/) scripts.

The big idea of the whole demo: **take one small data pipeline and build it four
different ways**, so you can feel the difference between doing coordination and
error-handling *by hand* (manual chaining) versus *letting a framework do it*
(Durable Functions).

---

## Table of contents

1. [The scenario: a tiny medallion pipeline](#1-the-scenario-a-tiny-medallion-pipeline)
2. [Foundational concepts](#2-foundational-concepts)
3. [The database layer (`sql/`)](#3-the-database-layer-sql)
4. [Part 1 — HTTP trigger + Azure SQL bindings](#4-part-1--http-trigger--azure-sql-bindings)
5. [Part 2 — Manual function chaining with queues](#5-part-2--manual-function-chaining-with-queues)
6. [Part 3 — Durable Functions orchestration](#6-part-3--durable-functions-orchestration)
7. [Part 4 — Manual error handling](#7-part-4--manual-error-handling)
8. [Part 5 — Durable error handling](#8-part-5--durable-error-handling)
9. [Cross-cutting code patterns](#9-cross-cutting-code-patterns)
10. [Side-by-side summary](#10-side-by-side-summary)

---

## 1. The scenario: a tiny medallion pipeline

Every part transforms the same data using the same logical steps. The data flows
through a simplified **medallion architecture** — a common data-engineering
layering convention:

```
  staging (bronze)            cleaning              gold
  ----------------            --------              ----
  staging.customers   ─┐
                        ├─►  trim / lower / filter ─►  join  ─►  gold.customer_sales_summary
  staging.orders      ─┘
```

- **Bronze / staging** — raw data exactly as it landed, "dirty" (whitespace,
  mixed case, NULLs, bad rows).
- **Silver / cleaned intermediates** — normalized and filtered rows
  (`staging.customers_clean`, `staging.orders_clean`, `staging.customer_orders_joined`).
- **Gold** — the final, query-ready aggregate (`gold.customer_sales_summary`):
  one row per customer with order counts and totals.

The four pipeline steps, identical in every part, are:

| Step | What it does |
|------|--------------|
| **extract** | Reads the raw tables (here it just counts rows to prove connectivity). |
| **clean** | Trims/normalizes text, drops invalid rows → `*_clean` tables. |
| **join** | Inner-joins cleaned customers and orders → `customer_orders_joined`. |
| **load** | Aggregates the joined data → `gold.customer_sales_summary`. |

Because the *business logic* (the SQL) is identical across parts, the demo
isolates the one thing that actually changes: **how the steps are coordinated and
how failures are handled.**

---

## 2. Foundational concepts

### Azure Functions

A **serverless** compute service: you write individual functions, each set off by
a **trigger** (an HTTP request, a queue message, a timer, an orchestration event,
etc.). Azure manages the servers, scaling, and execution. You are billed per
execution rather than for an always-on server.

### The Python v2 programming model

This demo uses the **v2 programming model**, where everything is declared with
**decorators in `function_app.py`** instead of per-function `function.json`
files. You see this in every part:

```python
app = func.FunctionApp()

@app.route(route="start", methods=["POST"])
def start_pipeline(req): ...
```

The `app` object is the function app. Decorators like `@app.route`,
`@app.queue_trigger`, `@app.sql_input`, and `@app.orchestration_trigger` attach
triggers and bindings to plain Python functions.

### Triggers vs. bindings

- A **trigger** is *what causes a function to run* (an HTTP call, a new queue
  message). Each function has exactly one trigger.
- A **binding** is a *declarative connection to data*, so you don't write the
  plumbing yourself:
  - an **input binding** fetches data and hands it to the function,
  - an **output binding** takes a value the function produces and writes it out.

The point of bindings is to remove boilerplate: no connection strings opened by
hand, no SQL driver, no queue client — you declare *what* you want and the
runtime does *how*.

### `host.json`, `local.settings.json`, and the extension bundle

- **`host.json`** — runtime-wide configuration shared by all functions in the app
  (logging, queue retry counts, etc.).
- **`local.settings.json`** — local-only secrets and connection strings
  (git-ignored). Each part ships a `.example` you copy and fill in. In Azure these
  become **application settings**.
- **Extension bundle** — declared in `host.json`; it pulls in the binding
  extensions (SQL, Durable, Storage Queues) without you managing NuGet/packages
  directly:
  ```json
  "extensionBundle": {
    "id": "Microsoft.Azure.Functions.ExtensionBundle",
    "version": "[4.*, 5.0.0)"
  }
  ```

### Two connection-string formats

The demo deliberately uses two different formats because two different mechanisms
talk to SQL:

- **`SqlConnectionString`** (ADO.NET format) — consumed by the **SQL bindings** in
  Part 1. The binding extension is .NET-based, so it wants the ADO.NET shape.
- **`SqlOdbcConnectionString`** (ODBC format) — consumed by **`pyodbc`** in
  Parts 2–5, where the Python code opens the connection itself.

### Azurite

The **local Azure Storage emulator**. Parts 2–5 need it because:
- Storage Queues (Parts 2 & 4) live in Storage.
- Durable Functions (Parts 3 & 5) persist their orchestration state in Storage.

`AzureWebJobsStorage` is set to `UseDevelopmentStorage=true`, which points the
runtime at Azurite.

---

## 3. The database layer (`sql/`)

Run these scripts **in order** against your database. They define the playing
field for all five parts.

### `01_create_schemas_and_tables.sql`

Creates two schemas (`staging`, `gold`) and all the tables. Key design choices:

- **`customer_id` and `order_id` are PRIMARY KEYs** on the raw tables. This matters
  for Part 1: the SQL **output binding** performs an *upsert* keyed on the primary
  key, so POSTing an existing id updates rather than duplicates.
- The script is **idempotent** — it `DROP ... IF EXISTS` first, so you can re-run
  it safely. Tables are dropped children-first to respect dependencies.
- `customer_orders_joined` uses an `IDENTITY` surrogate key because a customer can
  have many orders (the natural key isn't unique per row).
- `gold.customer_sales_summary` carries `processed_at` so you can see when the
  pipeline last ran.

### `02_seed_sample_data.sql`

Inserts **intentionally dirty** data so the clean step has real work:

| Dirt | Example row | Fate |
|------|-------------|------|
| Whitespace in name | `'  Ada Lovelace  '` | trimmed |
| Mixed-case / padded email | `'ADA@EXAMPLE.COM '` | lowercased + trimmed |
| Empty / NULL city | `''`, `NULL` | converted to NULL |
| NULL email | customer 5 (Linus) | **dropped** in clean |
| Negative amount | order 1004 (-15.00) | **dropped** in clean |
| NULL amount | order 1006 | **dropped** in clean |
| Cancelled order | order 1007 | **dropped** in clean |
| Orphan order | order 1009, customer 999 | **dropped** by the join |

The expected gold result is documented at the bottom of `03_verify.sql`.

### `03_verify.sql`

Read-only inspection queries: counts and full dumps of every layer (raw →
cleaned → joined → gold). Run any time to see where the pipeline got to. The
trailing comment block states the **expected** gold output, which is your test
oracle.

### `04_pipeline_runs.sql`

Creates `staging.pipeline_runs` — **only used by Part 4**. It's the home-made
"where is my run / what failed" table that you must build when you don't have an
orchestrator. Columns: `run_id`, `status` (running/completed/failed),
`current_step`, `attempts`, `last_error`, and timestamps. Parts 3 and 5 get this
bookkeeping for free from the Durable runtime, so they don't need this script.

---

## 4. Part 1 — HTTP trigger + Azure SQL bindings

**Concept taught:** declarative SQL **input and output bindings** — reading from
and writing to a database *without any driver code*.

**File:** [part1-http-sql-binding/function_app.py](part1-http-sql-binding/function_app.py)

### What it does

One function app, one route, two methods:

| Method | Route | Binding | Effect |
|--------|-------|---------|--------|
| `GET`  | `/api/customers` | SQL **input** | Returns up to 100 customer rows. |
| `POST` | `/api/customers` | SQL **output** | Upserts a customer (the "change to a table"). |

### How the code is written

The app is created with anonymous auth so you can curl it without keys:

```python
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
```

**The read — SQL input binding.** The `@app.sql_input` decorator runs a query and
materializes the rows *before* the function body runs, handing them in as the
`customers` parameter:

```python
@app.route(route="customers", methods=["GET"])
@app.sql_input(
    arg_name="customers",
    command_text="SELECT TOP 100 customer_id, name, email, city "
                 "FROM staging.customers ORDER BY customer_id",
    command_type="Text",
    connection_string_setting="SqlConnectionString",
)
def get_customers(req, customers: func.SqlRowList) -> func.HttpResponse:
    rows = [dict(r) for r in customers]   # each row behaves like a dict
    return func.HttpResponse(json.dumps(rows, default=str), mimetype="application/json")
```

Notice: **no connection is opened, no cursor, no driver.** The function only
turns the rows into JSON. `connection_string_setting` names the *app setting*
(`SqlConnectionString`) — the secret never appears in code.

**The write — SQL output binding (upsert).** The `@app.sql_output` decorator
points at a **table name** rather than a query. The function receives an
`Out[SqlRow]` handle; whatever you `.set()` on it is written when the function
returns:

```python
@app.route(route="customers", methods=["POST"])
@app.sql_output(
    arg_name="customer",
    command_text="staging.customers",      # <-- just the target table
    connection_string_setting="SqlConnectionString",
)
def upsert_customer(req, customer: func.Out[func.SqlRow]) -> func.HttpResponse:
    body = req.get_json()                  # validated below
    row = func.SqlRow.from_dict({
        "customer_id": body["customer_id"],
        "name": body["name"],
        "email": body["email"],
        "city": body.get("city"),
    })
    customer.set(row)                      # binding writes the row on return
    ...
```

Because `customer_id` is the table's primary key, the binding emits a SQL
`MERGE` — **insert if new, update if the id exists**. POST the same id twice and
the second call updates the first.

**Input validation** is done by hand before touching the binding: the body must
be valid JSON (`400` otherwise) and must contain `customer_id`, `name`, `email`.
This is normal function-body responsibility; the binding only handles persistence.

### Why it matters

This part isolates the *binding* concept with zero coordination logic. It's the
baseline: "look how little code reads/writes a table." Parts 2–5 then move to
`pyodbc` (explicit connections) because they need transactional, multi-statement
SQL that the simple bindings don't express.

---

## 5. Part 2 — Manual function chaining with queues

**Concept taught:** building a multi-step pipeline as **separate functions wired
together with Storage Queue triggers**, and feeling the *cost* of coordinating it
by hand.

**Files:** [part2-manual-chaining/function_app.py](part2-manual-chaining/function_app.py),
[pipeline_sql.py](part2-manual-chaining/pipeline_sql.py),
[db.py](part2-manual-chaining/db.py)

### The chaining pattern

Five functions: one HTTP starter + four queue-triggered steps. **Each step does
one job and enqueues a message onto the *next* queue:**

```
POST /api/start
      │ (enqueue on pipeline-extract)
      ▼
  Extract ─► pipeline-clean ─► Clean ─► pipeline-join ─► Join ─► pipeline-load ─► Load ─► gold
```

This is the **fan-of-queues** approach: the "flow" exists only as a *convention
spread across functions* — each one hard-codes the name of the queue it reads and
the queue it writes.

### How the code is written

**Shared helpers.** Two pieces are factored out and reused by Parts 2–5:

- [db.py](part2-manual-chaining/db.py) — opens a `pyodbc` connection from the
  `SqlOdbcConnectionString` setting:
  ```python
  def get_connection() -> pyodbc.Connection:
      return pyodbc.connect(os.environ["SqlOdbcConnectionString"])
  ```
- [pipeline_sql.py](part2-manual-chaining/pipeline_sql.py) — the transformation
  SQL as string constants (`CLEAN_CUSTOMERS`, `CLEAN_ORDERS`, `JOIN_TABLES`,
  `LOAD_GOLD`). This file is **byte-for-byte identical** in Parts 2 and 3 — that's
  the demo's control variable.

A local `_run_sql` helper runs one-or-more SQL batches in a **single committed
transaction**:

```python
def _run_sql(*statements: str) -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        for sql in statements:
            cur.execute(sql)
        conn.commit()
```

**The starter** generates a `run_id` (a UUID used only to correlate log lines —
there's no run table here) and drops the first message via a **queue output
binding**, returning `202 Accepted`:

```python
@app.route(route="start", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
@app.queue_output(arg_name="msg", queue_name="pipeline-extract", connection=STORAGE)
def start_pipeline(req, msg: func.Out[str]) -> func.HttpResponse:
    run_id = str(uuid.uuid4())
    msg.set(json.dumps({"run_id": run_id, "step": "extract"}))
    return func.HttpResponse(..., status_code=202)
```

**Each step** has a `@app.queue_trigger` (the input) *and* a `@app.queue_output`
(the next queue). The body decodes the JSON payload, does its work, then re-emits
the payload onto the next queue:

```python
@app.queue_trigger(arg_name="msg", queue_name="pipeline-clean", connection=STORAGE)
@app.queue_output(arg_name="out", queue_name="pipeline-join", connection=STORAGE)
def clean(msg: func.QueueMessage, out: func.Out[str]) -> None:
    payload = json.loads(msg.get_body().decode())
    _run_sql(CLEAN_CUSTOMERS, CLEAN_ORDERS)
    out.set(json.dumps(payload))           # hand the run to the next step
```

The final `load` step has **no** output binding — the chain ends there, writing
the gold table.

### The pain points (the whole reason this part exists)

- **Wiring is hard-coded.** Each function literally names the next queue
  (`queue_name="pipeline-join"`). Reordering or inserting a step means editing
  multiple functions.
- **No central view of state.** To answer "where is run X?" you inspect queues
  and logs. The `run_id` is just threaded through messages for log correlation.
- **Data passes through messages.** The payload rides in the queue message (which
  has size limits) or via shared tables.
- **Failures are messy.** If `Join` throws, its message returns to the queue and
  eventually a poison queue — but `Extract` and `Clean` already ran. You own the
  retry/restart story (this is exactly what Part 4 builds out).

---

## 6. Part 3 — Durable Functions orchestration

**Concept taught:** the **same pipeline** rebuilt with **Durable Functions** —
one orchestrator that calls activities in sequence, with state, retries, and
status tracking provided by the framework.

**File:** [part3-durable-functions/function_app.py](part3-durable-functions/function_app.py)

### The three Durable function types

Durable Functions has a specific role structure:

1. **Client / starter** — an ordinary trigger (here HTTP) that *starts* an
   orchestration and hands back status URLs.
2. **Orchestrator** — a special function that *defines the workflow*. It schedules
   activities and `yield`s on them. **It must be deterministic** (see below).
3. **Activity** — a normal function that does the actual I/O/work (the DB calls).
   Activities can be non-deterministic and have side effects.

The app object changes from `func.FunctionApp()` to `df.DFApp(...)`, which adds
the Durable decorators:

```python
import azure.durable_functions as df
app = df.DFApp(http_auth_level=func.AuthLevel.ANONYMOUS)
```

### How the code is written

**The starter** uses a **durable client input binding** and `start_new`, then
returns `create_check_status_response`, which gives the caller a JSON bundle of
management URLs (status, terminate, etc.):

```python
@app.route(route="start", methods=["POST"])
@app.durable_client_input(client_name="client")
async def start_pipeline(req, client) -> func.HttpResponse:
    instance_id = await client.start_new("run_pipeline")
    return client.create_check_status_response(req, instance_id)
```

**The orchestrator** *is* the whole flow, read top to bottom. Each
`yield context.call_activity(...)` schedules an activity and resumes with its
return value. Notice the data **flows as return values** — `extract`'s result
becomes `clean`'s input — with no queue names anywhere:

```python
@app.orchestration_trigger(context_name="context")
def run_pipeline(context: df.DurableOrchestrationContext):
    retry = df.RetryOptions(first_retry_interval_in_milliseconds=5000,
                            max_number_of_attempts=3)

    extracted = yield context.call_activity("extract_activity", None)
    yield context.call_activity_with_retry("clean_activity", retry, extracted)
    yield context.call_activity_with_retry("join_activity", retry, None)
    loaded = yield context.call_activity_with_retry("load_activity", retry, None)

    return {"status": "completed", "extracted": extracted, "gold_rows": loaded}
```

**The activities** are plain functions doing the SQL — the same `_run_sql` and the
same `pipeline_sql.py` constants as Part 2:

```python
@app.activity_trigger(input_name="payload")
def clean_activity(payload):
    _run_sql(CLEAN_CUSTOMERS, CLEAN_ORDERS)
    return "cleaned"
```

### Two concepts you must understand here

**1. The orchestrator must be deterministic / replay-safe.** Durable Functions
works by **event sourcing with replay**: every time an activity completes, the
orchestrator function is *re-run from the top*, replaying past results from a
history table instead of re-executing them. For replay to produce the same
decisions, the orchestrator must avoid non-determinism — **no direct DB calls,
no `datetime.now()`, no random, no I/O.** That's why all real work lives in
activities, and the orchestrator only schedules them. (This is the reason
`SYSUTCDATETIME()` is computed inside the SQL/activity, not in the orchestrator.)

**2. `yield` is how the orchestrator awaits.** Each `yield` returns control to the
runtime; when the activity finishes, the runtime replays and the `yield`
"returns" the activity's value. `RetryOptions` + `call_activity_with_retry`
declares automatic retry-with-backoff — the framework handles it.

### Why it matters (vs. Part 2)

| Concern | Part 2 (manual) | Part 3 (Durable) |
|---|---|---|
| Wiring | Each function names the next queue | Orchestrator read top-to-bottom |
| State / progress | Inspect queues + logs | One `instance_id`, status endpoints |
| Retries | Hand-rolled per queue | `call_activity_with_retry` + `RetryOptions` |
| Passing data | Queue messages / shared tables | Return values flow as locals |
| Fan-out/fan-in | Coordinate counts yourself | `context.task_all([...])` built in |

The SQL is identical to Part 2 — **only the coordination moved out of your code
and into the framework.**

---

## 7. Part 4 — Manual error handling

**Concept taught:** everything you must **hand-build** to make the manual
(queue-chained) pipeline resilient: retries, dead-lettering, run state,
compensation, and a status endpoint.

**Files:** [part4-manual-error-handling/function_app.py](part4-manual-error-handling/function_app.py),
[runstate.py](part4-manual-error-handling/runstate.py),
[host.json](part4-manual-error-handling/host.json)

### The five things you build by hand

| Concern | How Part 4 implements it |
|---|---|
| **Retries** | `host.json` → `maxDequeueCount: 3`. A step that throws is re-delivered and retried automatically. |
| **Dead-lettering** | After retries are exhausted the runtime moves the message to `<queue>-poison`; one `*Poison` handler per queue reacts. |
| **Run state** | A home-made `staging.pipeline_runs` table written via [runstate.py](part4-manual-error-handling/runstate.py). |
| **Compensation** | The poison handler clears partial intermediates (placeholder for real rollback). |
| **Observability** | `GET /api/status/{run_id}` reads the home-made state table. |

### How the code is written

**Retry configuration lives in `host.json`**, not in code:

```json
"extensions": {
  "queues": {
    "maxDequeueCount": 3,
    "visibilityTimeout": "00:00:05"
  }
}
```

`maxDequeueCount: 3` means a message is tried up to 3 times before the runtime
gives up and moves it to the poison queue. The short `visibilityTimeout` makes
the retries happen fast enough to watch in a demo.

**A failure-injection hook** lets you trigger errors on demand:

```python
def _maybe_fail(payload, step):
    if payload.get("fail_at") == step:
        raise RuntimeError(f"Injected failure at step '{step}'")
```

The starter reads `?fail_at=join` from the query string and threads it through the
message payload, and also creates the run-state row up front:

```python
fail_at = req.params.get("fail_at")
runstate.create_run(run_id)
msg.set(json.dumps({"run_id": run_id, "fail_at": fail_at}))
```

**Every step is wrapped in the same try/except/record/re-raise boilerplate.** It
records progress before working, optionally fails, does the work, enqueues the
next message *only on success*, and on any exception records the error and
**re-raises** so the runtime retries:

```python
def join(msg, out):
    payload = json.loads(msg.get_body().decode())
    run_id = payload["run_id"]
    try:
        runstate.update_step(run_id, "join")
        _maybe_fail(payload, "join")
        _run_sql(JOIN_TABLES)
        out.set(json.dumps(payload))                 # only enqueued on success
    except Exception as exc:
        runstate.record_error(run_id, "join", str(exc), msg.dequeue_count)
        raise                                        # -> runtime retry / poison
```

`msg.dequeue_count` is how many times this message has been delivered — i.e. the
attempt number, recorded into the state table.

**Poison handlers — one per queue.** When `maxDequeueCount` is exceeded the
runtime delivers the original message to `<queue>-poison`. There must be a handler
for each queue, and they all funnel into a shared routine that marks the run
failed and compensates:

```python
@app.queue_trigger(arg_name="msg", queue_name="pipeline-join-poison", connection=STORAGE)
def join_poison(msg):
    _handle_poison(msg, "join")

def _handle_poison(msg, step):
    payload = json.loads(msg.get_body().decode())
    run_id = payload.get("run_id", "unknown")
    runstate.mark_failed(run_id, step, f"Dead-lettered at '{step}' ...")
    try:
        _run_sql("TRUNCATE TABLE staging.customer_orders_joined;")   # compensation
    except Exception:
        logging.exception("[%s] compensation failed", run_id)        # must not crash
```

Note the defensive detail: **compensation is itself wrapped in try/except** so a
failing rollback doesn't crash the poison handler.

**The run-state store** ([runstate.py](part4-manual-error-handling/runstate.py))
is a set of small functions that UPDATE the `pipeline_runs` row:
`create_run`, `update_step`, `record_error` (transient — run stays *running*),
`mark_failed` (terminal), `mark_completed`, and `get_run` (read for the status
endpoint). This is hand-written bookkeeping that Durable gives you for free.

**The status endpoint** reads that table:

```python
@app.route(route="status/{run_id}", methods=["GET"], ...)
def get_status(req):
    run = runstate.get_run(req.route_params.get("run_id"))
    return func.HttpResponse(json.dumps(run, default=str), ...)  # 404 if missing
```

### The failure walk-through

`POST /api/start?fail_at=join`:

1. `Extract` and `Clean` succeed.
2. `Join` throws → **retried 3 times** (attempts 1, 2, 3 visible in logs).
3. Runtime moves the message to `pipeline-join-poison`.
4. `JoinPoison` runs → marks the run **failed** and compensates.
5. `GET /api/status/{id}` shows `status: failed, current_step: join, attempts: 3`.

### The lesson

**You wrote all of it.** A table, a status route, four poison handlers, and the
same try/except/record block in every step. More steps = more handlers. Nothing
rolls back automatically — compensation is your problem to reason through.

---

## 8. Part 5 — Durable error handling

**Concept taught:** the *same* failure scenario as Part 4, but with Durable
Functions supplying retries, state, status, and a clean failure path. You write
only the **policy**.

**Files:** [part5-durable-error-handling/function_app.py](part5-durable-error-handling/function_app.py),
[pipeline_sql.py](part5-durable-error-handling/pipeline_sql.py) (adds `COMPENSATE`)

### How the code is written

**The starter** passes `fail_at` into the orchestration as **input** rather than
threading it through queue messages:

```python
fail_at = req.params.get("fail_at")
instance_id = await client.start_new("run_pipeline", client_input={"fail_at": fail_at})
return client.create_check_status_response(req, instance_id)
```

**The orchestrator expresses retry + compensation declaratively** — the entire
error-handling story is one `try/except` wrapping `call_activity_with_retry`
calls, plus `set_custom_status` to publish progress:

```python
@app.orchestration_trigger(context_name="context")
def run_pipeline(context):
    payload = context.get_input() or {}
    retry = df.RetryOptions(first_retry_interval_in_milliseconds=5000,
                            max_number_of_attempts=3)
    try:
        context.set_custom_status("extracting")
        extracted = yield context.call_activity_with_retry("extract_activity", retry, payload)
        context.set_custom_status("cleaning")
        yield context.call_activity_with_retry("clean_activity", retry, payload)
        context.set_custom_status("joining")
        yield context.call_activity_with_retry("join_activity", retry, payload)
        context.set_custom_status("loading")
        gold_rows = yield context.call_activity_with_retry("load_activity", retry, payload)
        context.set_custom_status("completed")
        return {"status": "completed", "extracted": extracted, "gold_rows": gold_rows}
    except Exception as exc:
        # retries exhausted -> compensate, then report a clean failure
        context.set_custom_status("compensating")
        yield context.call_activity("compensate_activity", str(exc))
        context.set_custom_status("failed")
        return {"status": "failed", "error": str(exc)}
```

Two important behaviors:

- **`RetryOptions` replaces `maxDequeueCount` + per-step try/except.** One argument
  per call declares attempts and backoff; the runtime drives the retries.
- **A failing activity *raises into the orchestrator*** once retries are exhausted.
  That single `except` is the equivalent of all four poison handlers in Part 4.

**The saga / compensation pattern.** The `except` block calls a compensating
activity that undoes partial work. The compensation SQL is a new constant in
[pipeline_sql.py](part5-durable-error-handling/pipeline_sql.py):

```python
COMPENSATE = """
TRUNCATE TABLE staging.customer_orders_joined;
"""
```

```python
@app.activity_trigger(input_name="reason")
def compensate_activity(reason):
    _run_sql(COMPENSATE)
    return "compensated"
```

**`set_custom_status`** publishes a human-readable progress string
(`extracting` → `cleaning` → ... → `failed`) that shows up in the **same
`statusQueryGetUri`** the starter returned. No custom status table, no status
route.

### A subtle point worth calling out

Because the orchestrator **catches** the error and returns a structured result,
the orchestration ends with `runtimeStatus: Completed` and
`output: {"status": "failed", ...}`. If you instead let the exception propagate
(remove the `try/except`), `runtimeStatus` becomes `Failed` and Durable records
the exception and stack trace for you — no logging code required. Either way the
framework persists the outcome.

### Failure walk-through

`POST /api/start?fail_at=join`:

1. `extract`, `clean` succeed.
2. `join_activity` throws → retried 3× per `RetryOptions` (`customStatus: joining`).
3. Retries exhausted → error propagates into the orchestrator's `except`.
4. `customStatus → compensating`; `compensate_activity` clears partial work.
5. Orchestration ends `Completed`, output `{"status": "failed", "error": ...}`.

### The lesson

**Policy, not plumbing.** Retry counts, backoff, the failure path, status, and
state are expressed once in the orchestrator. There are no poison queues, no
bookkeeping table, no status route. Same resilience as Part 4 — far less code you
own.

---

## 9. Cross-cutting code patterns

These appear in multiple parts and are worth understanding once:

### `_run_sql(*statements)` — transactional batch helper

Parts 2–5 share this. It opens one connection, runs each statement on a cursor,
and commits once — so the multiple statements inside `CLEAN_CUSTOMERS`/etc. land
**atomically**. Each SQL constant typically `TRUNCATE`s its target then re-inserts,
which makes every run **idempotent** (re-running produces the same result, not
duplicates).

### Shared, duplicated `pipeline_sql.py`

The transformation SQL is intentionally copied into each part folder rather than
imported from a shared library. The trade-off is deliberate: each part folder is
a **self-contained, independently deployable function app**, and keeping the SQL
byte-for-byte identical makes the comparison honest — *only the orchestration and
error handling differ between parts.*

### `func.Out[T]` output bindings

Seen in Parts 1, 2, 4. The function receives a write-handle; you call `.set(value)`
and the binding performs the write (SQL row, or queue message) **when the function
returns successfully**. In Part 4 this is why `out.set(...)` sits at the end of the
`try` — the next step is only enqueued if the current step succeeded.

### Payload threading vs. return values

- **Manual (2 & 4):** state travels *inside the queue message* (`run_id`,
  `fail_at`, accumulated results) — you serialize/deserialize JSON at every hop.
- **Durable (3 & 5):** state travels as *orchestrator local variables and activity
  return values* — the framework persists them.

### Failure injection (`_maybe_fail`)

Parts 4 and 5 both expose `?fail_at=<step>` so the *same* failure scenario can be
run against both implementations and compared. It's a teaching hook, not
production code.

---

## 10. Side-by-side summary

### Coordination: Part 2 vs. Part 3

| Concern | Part 2 — Manual (queues) | Part 3 — Durable |
|---|---|---|
| Where the flow lives | Spread across functions (each names the next queue) | One orchestrator, top-to-bottom |
| Reordering a step | Edit several functions | Move a line |
| Progress / state | Inspect queues + logs | One `instance_id` + status endpoints |
| Passing data | Queue messages / shared tables | Return values as locals |
| Fan-out / fan-in | Coordinate counts by hand | `context.task_all([...])` |

### Error handling: Part 4 vs. Part 5

| Concern | Part 4 — Manual | Part 5 — Durable |
|---|---|---|
| Retries | `host.json` `maxDequeueCount` + try/except in every step | `call_activity_with_retry(..., RetryOptions)` |
| Dead-letter | runtime → `<queue>-poison`; one handler **per queue** | activity error propagates to orchestrator |
| Run state | home-made `staging.pipeline_runs` table | persisted by the runtime |
| Status query | custom `GET /api/status/{run_id}` | built-in `statusQueryGetUri` + `set_custom_status()` |
| Compensation | logic inside each poison handler | one `try/except` calling a compensating activity (saga) |
| Lines you own | a table, a status route, 4 poison handlers, per-step boilerplate | a `try/except` and a `RetryOptions` |

### The single takeaway

All four pipeline implementations produce the **identical**
`gold.customer_sales_summary`. What changes is **how much coordination and
error-handling code you have to write and own**. Durable Functions moves that
machinery out of your business logic and into the framework — the case the whole
demo is built to make concrete.
