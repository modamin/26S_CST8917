"""
Part 3 — The SAME pipeline as Part 2, rebuilt with Durable Functions.

One HTTP starter, one orchestrator, four activities:

    POST /api/start
          │  start_new("run_pipeline")
          ▼
    run_pipeline (orchestrator)               <-- the WHOLE flow, read top-to-bottom
          ├─ call_activity("extract_activity")
          ├─ call_activity_with_retry("clean_activity", retry)
          ├─ call_activity_with_retry("join_activity",  retry)
          └─ call_activity_with_retry("load_activity",  retry)

Compared with Part 2:
  * the flow lives in ONE function and is read like normal code
  * results flow as return values between activities (no queue names to wire)
  * retries are declarative (RetryOptions), not hand-rolled per queue
  * the runtime tracks state — query progress via the status endpoints that
    create_check_status_response() returns
"""

import logging

import azure.functions as func
import azure.durable_functions as df

from db import get_connection
from pipeline_sql import CLEAN_CUSTOMERS, CLEAN_ORDERS, JOIN_TABLES, LOAD_GOLD

app = df.DFApp(http_auth_level=func.AuthLevel.ANONYMOUS)


def _run_sql(*statements: str) -> None:
    """Execute one or more SQL batches in a single committed transaction."""
    with get_connection() as conn:
        cur = conn.cursor()
        for sql in statements:
            cur.execute(sql)
        conn.commit()


# ---------------------------------------------------------------------------
# HTTP starter — starts an orchestration and returns the status URLs
# ---------------------------------------------------------------------------
@app.route(route="start", methods=["POST"])
@app.durable_client_input(client_name="client")
async def start_pipeline(req: func.HttpRequest, client) -> func.HttpResponse:
    instance_id = await client.start_new("run_pipeline")
    logging.info("Started orchestration with id = %s", instance_id)
    return client.create_check_status_response(req, instance_id)


# ---------------------------------------------------------------------------
# Orchestrator — defines the chain. No I/O happens here; it only schedules
# activities. (Must be deterministic, hence no DB calls / no datetime / etc.)
# ---------------------------------------------------------------------------
@app.orchestration_trigger(context_name="context")
def run_pipeline(context: df.DurableOrchestrationContext):
    retry = df.RetryOptions(first_retry_interval_in_milliseconds=5000, max_number_of_attempts=3)

    extracted = yield context.call_activity("extract_activity", None)
    yield context.call_activity_with_retry("clean_activity", retry, extracted)
    yield context.call_activity_with_retry("join_activity", retry, None)
    loaded = yield context.call_activity_with_retry("load_activity", retry, None)

    return {"status": "completed", "extracted": extracted, "gold_rows": loaded}


# ---------------------------------------------------------------------------
# Activities — each one does the real work for a single step
# ---------------------------------------------------------------------------
@app.activity_trigger(input_name="payload")
def extract_activity(payload):
    with get_connection() as conn:
        cur = conn.cursor()
        customers = cur.execute("SELECT COUNT(*) FROM staging.customers").fetchval()
        orders = cur.execute("SELECT COUNT(*) FROM staging.orders").fetchval()
    logging.info("extract: customers=%s orders=%s", customers, orders)
    return {"customers": customers, "orders": orders}


@app.activity_trigger(input_name="payload")
def clean_activity(payload):
    _run_sql(CLEAN_CUSTOMERS, CLEAN_ORDERS)
    logging.info("clean: customers & orders cleaned")
    return "cleaned"


@app.activity_trigger(input_name="payload")
def join_activity(payload):
    _run_sql(JOIN_TABLES)
    logging.info("join: tables joined")
    return "joined"


@app.activity_trigger(input_name="payload")
def load_activity(payload):
    _run_sql(LOAD_GOLD)
    with get_connection() as conn:
        rows = conn.cursor().execute(
            "SELECT COUNT(*) FROM gold.customer_sales_summary"
        ).fetchval()
    logging.info("load: gold refreshed with %s row(s)", rows)
    return rows
