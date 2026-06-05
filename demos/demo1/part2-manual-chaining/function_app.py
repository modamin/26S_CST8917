"""
Part 2 — Manual function chaining with Storage Queue triggers.

The pipeline is split into one HTTP starter + four queue-triggered functions.
Each function does ONE step and then enqueues a message onto the NEXT queue:

    POST /api/start
          │  (enqueue)
          ▼
    pipeline-extract ─► extract ─► pipeline-clean ─► clean
                                                       │
            ┌──────────────────────────────────────────┘
            ▼
    pipeline-join ─► join ─► pipeline-load ─► load ─► gold.customer_sales_summary

Notice the cost of doing this by hand:
  * every function hard-codes the name of the *next* queue
  * the run_id is threaded through the message payload so we can correlate logs
  * there is no single place that knows the whole flow or its current progress
  * retries / poison handling would have to be wired per-queue

Part 3 replaces all of this with one Durable orchestrator.
"""

import json
import logging
import uuid

import azure.functions as func

from db import get_connection
from pipeline_sql import CLEAN_CUSTOMERS, CLEAN_ORDERS, JOIN_TABLES, LOAD_GOLD

app = func.FunctionApp()

STORAGE = "AzureWebJobsStorage"


def _run_sql(*statements: str) -> None:
    """Execute one or more SQL batches in a single committed transaction."""
    with get_connection() as conn:
        cur = conn.cursor()
        for sql in statements:
            cur.execute(sql)
        conn.commit()


# ---------------------------------------------------------------------------
# 0. HTTP starter — kicks off the chain by enqueuing the first message
# ---------------------------------------------------------------------------
@app.function_name(name="StartPipeline")
@app.route(route="start", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
@app.queue_output(arg_name="msg", queue_name="pipeline-extract", connection=STORAGE)
def start_pipeline(req: func.HttpRequest, msg: func.Out[str]) -> func.HttpResponse:
    run_id = str(uuid.uuid4())
    msg.set(json.dumps({"run_id": run_id, "step": "extract"}))
    logging.info("[%s] pipeline started", run_id)
    return func.HttpResponse(
        json.dumps({"status": "started", "run_id": run_id}),
        status_code=202,
        mimetype="application/json",
    )


# ---------------------------------------------------------------------------
# 1. EXTRACT — read the raw tables (here: count them) and pass the run along
# ---------------------------------------------------------------------------
@app.function_name(name="Extract")
@app.queue_trigger(arg_name="msg", queue_name="pipeline-extract", connection=STORAGE)
@app.queue_output(arg_name="out", queue_name="pipeline-clean", connection=STORAGE)
def extract(msg: func.QueueMessage, out: func.Out[str]) -> None:
    payload = json.loads(msg.get_body().decode())
    with get_connection() as conn:
        cur = conn.cursor()
        customers = cur.execute("SELECT COUNT(*) FROM staging.customers").fetchval()
        orders = cur.execute("SELECT COUNT(*) FROM staging.orders").fetchval()
    payload["extracted"] = {"customers": customers, "orders": orders}
    logging.info("[%s] extract: %s", payload["run_id"], payload["extracted"])
    out.set(json.dumps(payload))


# ---------------------------------------------------------------------------
# 2. CLEAN — normalise + filter both raw tables into the *_clean tables
# ---------------------------------------------------------------------------
@app.function_name(name="Clean")
@app.queue_trigger(arg_name="msg", queue_name="pipeline-clean", connection=STORAGE)
@app.queue_output(arg_name="out", queue_name="pipeline-join", connection=STORAGE)
def clean(msg: func.QueueMessage, out: func.Out[str]) -> None:
    payload = json.loads(msg.get_body().decode())
    _run_sql(CLEAN_CUSTOMERS, CLEAN_ORDERS)
    logging.info("[%s] clean: customers & orders cleaned", payload["run_id"])
    out.set(json.dumps(payload))


# ---------------------------------------------------------------------------
# 3. JOIN — join the cleaned tables into the joined intermediate
# ---------------------------------------------------------------------------
@app.function_name(name="Join")
@app.queue_trigger(arg_name="msg", queue_name="pipeline-join", connection=STORAGE)
@app.queue_output(arg_name="out", queue_name="pipeline-load", connection=STORAGE)
def join(msg: func.QueueMessage, out: func.Out[str]) -> None:
    payload = json.loads(msg.get_body().decode())
    _run_sql(JOIN_TABLES)
    logging.info("[%s] join: tables joined", payload["run_id"])
    out.set(json.dumps(payload))


# ---------------------------------------------------------------------------
# 4. LOAD — aggregate the joined data into the gold table (end of chain)
# ---------------------------------------------------------------------------
@app.function_name(name="Load")
@app.queue_trigger(arg_name="msg", queue_name="pipeline-load", connection=STORAGE)
def load(msg: func.QueueMessage) -> None:
    payload = json.loads(msg.get_body().decode())
    _run_sql(LOAD_GOLD)
    logging.info("[%s] load: gold.customer_sales_summary refreshed — DONE", payload["run_id"])
