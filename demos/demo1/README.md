# Demo 1 — Azure Functions: Bindings, Manual Chaining, and Durable Functions

This lab is a five-part demo that builds up from a single Azure Function to a
full data pipeline, contrasts **manual function chaining** (functions wired
together with triggers/queues) against **Durable Functions** orchestration, and
then contrasts how each approach handles **errors**.

The scenario is a tiny "medallion" data pipeline over a sales database:

```
  staging (bronze)            cleaning              gold
  ----------------            --------              ----
  staging.customers   ─┐
                        ├─►  trim / lower / filter ─►  join  ─►  gold.customer_sales_summary
  staging.orders      ─┘
```

## The three parts

| Part | Folder | What it shows |
|------|--------|---------------|
| **1** | [part1-http-sql-binding/](part1-http-sql-binding/) | A single HTTP-triggered function that **reads from** and **writes to** Azure SQL using the native **SQL input/output bindings** — no SQL driver code. It makes a change to the `staging.customers` table. |
| **2** | [part2-manual-chaining/](part2-manual-chaining/) | The pipeline (extract → clean → join → load) built as **separate functions chained by Storage Queue triggers**. Each function does one step and enqueues the next. Shows the *manual* approach and its pain points. |
| **3** | [part3-durable-functions/](part3-durable-functions/) | The **same pipeline** rebuilt with **Durable Functions**: one orchestrator calls four activity functions in sequence, with built-in state, retries, and status tracking. |
| **4** | [part4-manual-error-handling/](part4-manual-error-handling/) | Part 2 **hardened by hand**: retries (`maxDequeueCount`), poison-queue handlers, a home-made run-state table, compensation, and a status endpoint. |
| **5** | [part5-durable-error-handling/](part5-durable-error-handling/) | Part 3 with **error handling the Durable way**: declarative retries, try/except compensation (saga), and built-in state/status. |

After running Parts 2 and 3 you can compare them side-by-side — see
[Comparing Part 2 and Part 3](#comparing-part-2-and-part-3). Parts 4 and 5 do the
same for error handling — see [Error handling: Part 4 vs Part 5](#error-handling-part-4-vs-part-5).

## Prerequisites

- **Python 3.11** (3.10–3.11 supported by the v2 programming model)
- **Azure Functions Core Tools v4** — `func --version` should print `4.x`
- **Azurite** (local Storage emulator) for the queue triggers in Parts 2 & 3
  - `npm install -g azurite` then run `azurite` in a spare terminal
- **Microsoft ODBC Driver 18 for SQL Server** (Parts 2 & 3 use `pyodbc`)
  - Linux install: see https://learn.microsoft.com/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server
- An **Azure SQL Database** (or local SQL Server / SQL Edge container). A free
  serverless Azure SQL DB is plenty.

## Setup

### 1. Create the database objects

Run the scripts in [sql/](sql/) **in order** against your database
(Azure Data Studio, `sqlcmd`, or the Azure portal query editor):

```bash
sqlcmd -S <server>.database.windows.net -d <database> -U <user> -P <password> -i sql/01_create_schemas_and_tables.sql
sqlcmd -S <server>.database.windows.net -d <database> -U <user> -P <password> -i sql/02_seed_sample_data.sql
sqlcmd -S <server>.database.windows.net -d <database> -U <user> -P <password> -i sql/04_pipeline_runs.sql   # only needed for Part 4
sqlcmd -S <server>.database.windows.net -d <database> -U <user> -P <password> -i sql/03_verify.sql
```

The seed data is intentionally **dirty** (whitespace, mixed-case emails, NULLs,
negative/cancelled orders, orphan orders) so the cleaning step has something to do.

### 2. Configure connection strings

Each part has a `local.settings.json.example`. Copy it to `local.settings.json`
(which is git-ignored) and fill in your values:

```bash
cp local.settings.json.example local.settings.json
```

Two connection-string formats are used:

- **`SqlConnectionString`** — *ADO.NET* format, used by the **SQL bindings** (Part 1).
  ```
  Server=tcp:<server>.database.windows.net,1433;Database=<db>;User ID=<user>;Password=<pwd>;Encrypt=true;TrustServerCertificate=false;
  ```
- **`SqlOdbcConnectionString`** — *ODBC* format, used by **pyodbc** (Parts 2 & 3).
  ```
  Driver={ODBC Driver 18 for SQL Server};Server=tcp:<server>.database.windows.net,1433;Database=<db>;Uid=<user>;Pwd=<pwd>;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;
  ```

> ⚠️ If you use Azure SQL, add your client IP to the server firewall, or run
> from within Azure.

### 3. Run a part

```bash
cd part1-http-sql-binding      # or part2 / part3
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
func start
```

See each part's own `README.md` for the exact endpoints and sample requests.

## Comparing Part 2 and Part 3

| Concern | Part 2 — Manual chaining (queues) | Part 3 — Durable Functions |
|---|---|---|
| **Wiring** | Each function must know the *next* queue name. Adding/reordering a step means editing multiple functions. | The orchestrator reads top-to-bottom; reorder by moving a line. |
| **State / progress** | No single place to see "where is run X?". You inspect queues and logs. | One instance id; query status with `create_check_status_response`. |
| **Error handling & retries** | Hand-rolled per function (poison queues, manual re-enqueue). | `call_activity_with_retry` with declarative `RetryOptions`. |
| **Passing data** | Via queue messages (size limits) or shared tables. | Returned values flow between activities as the orchestrator's locals. |
| **Fan-out / fan-in** | Hard — you coordinate counts yourself. | `yield context.task_all([...])` built in. |
| **Testing the whole flow** | Trigger step 1, then watch queues drain. | Start one orchestration, await the result. |

The takeaway for students: both produce the same `gold.customer_sales_summary`,
but Durable Functions moves the *coordination* out of your business logic and
into the framework.

## Error handling: Part 4 vs Part 5

Both parts run the same failure scenario — inject a fault with
`POST /api/start?fail_at=<step>` (`extract` | `clean` | `join` | `load`) — and
both recover. The difference is how much *you* have to build.

| Concern | Part 4 — Manual | Part 5 — Durable |
|---|---|---|
| **Retries** | `host.json` `maxDequeueCount` + try/except in every step | `call_activity_with_retry(..., RetryOptions)` — one arg per call |
| **Dead-letter** | runtime → `<queue>-poison`; one handler **per queue** | n/a — the activity error propagates to the orchestrator |
| **Run state** | home-made `staging.pipeline_runs` table | persisted by the runtime automatically |
| **Status query** | custom `GET /api/status/{run_id}` | built-in `statusQueryGetUri` + `set_custom_status()` |
| **Compensation** | logic inside each poison handler | one `try/except` around the flow calling a compensating activity (saga) |
| **Lines you own** | a table, a status route, 4 poison handlers, per-step boilerplate | a `try/except` and a `RetryOptions` |

Same resilience, far less code to own — that's the case for Durable Functions.
