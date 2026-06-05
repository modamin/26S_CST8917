# Demo 1 — Project Memory

Azure Functions teaching lab (CST8917). One small "medallion" data pipeline built
**four ways** to contrast *manual coordination/error-handling* vs. *Durable Functions*.

## Scenario
Dirty `staging.customers` + `staging.orders` → clean → join → aggregate into
`gold.customer_sales_summary`. Four logical steps everywhere: **extract → clean → join → load**.
The transformation SQL (`pipeline_sql.py`) is intentionally **byte-for-byte identical**
across parts 2–5 — only the *orchestration and error handling* differ. That is the
whole pedagogical point.

## Layout
- `sql/` — run in order: `01` schemas/tables (idempotent, PKs enable Part 1 upsert),
  `02` deliberately dirty seed data, `03` verify (has expected-output oracle in trailing comment),
  `04` `staging.pipeline_runs` table — **only Part 4 needs it**.
- `part1-http-sql-binding/` — single HTTP fn, SQL **input** binding (query→rows) +
  **output** binding (table name→MERGE upsert). No driver code. Uses `SqlConnectionString` (ADO.NET).
- `part2-manual-chaining/` — pipeline as 5 fns chained by Storage Queue triggers;
  each hard-codes the *next* queue. Shows the pain. Uses `pyodbc` + `SqlOdbcConnectionString`.
- `part3-durable-functions/` — same pipeline, one orchestrator + 4 activities. `DFApp`,
  `yield context.call_activity[_with_retry]`, data flows as return values.
- `part4-manual-error-handling/` — Part 2 hardened by hand: `host.json maxDequeueCount`,
  4 poison handlers, home-made `runstate.py`/`pipeline_runs` table, compensation, status route.
- `part5-durable-error-handling/` — Part 3 + errors the Durable way: `RetryOptions`,
  one `try/except` saga compensation (`COMPENSATE` SQL), `set_custom_status`.
- `concepts.md` — full written explanation of every concept + how each part's code works.

## Key facts to remember
- **Not a git repo.** Python v2 programming model (decorators in `function_app.py`).
- Two connection-string formats on purpose: **ADO.NET** (`SqlConnectionString`) for SQL bindings (Part 1);
  **ODBC** (`SqlOdbcConnectionString`) for `pyodbc` (Parts 2–5).
- Parts 2–5 need **Azurite** running (queues / Durable state).
- Orchestrators must be **deterministic** (replay/event-sourcing) → no DB/datetime/random in them;
  all I/O lives in activities. `SYSUTCDATETIME()` is computed in SQL, not Python.
- Failure injection: `POST /api/start?fail_at=<extract|clean|join|load>` (Parts 4 & 5) runs the
  same fault against both so they can be compared.
- `_run_sql(*statements)` = one connection, one commit (atomic). SQL constants `TRUNCATE`-then-`INSERT`
  → every run idempotent.
- `local.settings.json` is git-ignored; each part ships a `.example` to copy.

## Comparison takeaway
All four implementations produce the **same** gold table. Difference = how much
coordination + error-handling code *you own*. Durable moves it into the framework.
