"""
Part 5 — Durable Functions error handling.

Same pipeline as Part 3, but showing how Durable handles failure. Compare with
Part 4: here retries, run state, and status tracking are provided by the
framework — the orchestrator just expresses the *policy*.

  * RETRIES        — call_activity_with_retry + RetryOptions (declarative backoff).
  * RUN STATE      — the runtime persists every step; no home-made table needed.
  * COMPENSATION   — a try/except in the orchestrator runs a compensating
                     activity (saga pattern) when retries are exhausted.
  * OBSERVABILITY  — set_custom_status() + the built-in status query endpoints.

Inject a failure to see it:
    POST /api/start?fail_at=join     (extract | clean | join | load)
"""

import logging

import azure.functions as func
import azure.durable_functions as df

from db import get_connection
from pipeline_sql import (
    CLEAN_CUSTOMERS,
    CLEAN_ORDERS,
    COMPENSATE,
    JOIN_TABLES,
    LOAD_GOLD,
)

app = df.DFApp(http_auth_level=func.AuthLevel.ANONYMOUS)


def _run_sql(*statements: str) -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        for sql in statements:
            cur.execute(sql)
        conn.commit()


def _maybe_fail(payload, step: str) -> None:
    """Demo hook: blow up at the requested step so we can watch error handling."""
    if (payload or {}).get("fail_at") == step:
        raise RuntimeError(f"Injected failure at step '{step}' (fail_at={step})")


# ===========================================================================
# HTTP starter — passes the optional fail_at into the orchestration input
# ===========================================================================
@app.route(route="start", methods=["POST"])
@app.durable_client_input(client_name="client")
async def start_pipeline(req: func.HttpRequest, client) -> func.HttpResponse:
    fail_at = req.params.get("fail_at")            # optional: extract|clean|join|load
    instance_id = await client.start_new("run_pipeline", client_input={"fail_at": fail_at})
    logging.info("Started orchestration %s (fail_at=%s)", instance_id, fail_at)
    return client.create_check_status_response(req, instance_id)


# ===========================================================================
# Orchestrator — retry policy + try/except compensation, all in one place
# ===========================================================================
@app.orchestration_trigger(context_name="context")
def run_pipeline(context: df.DurableOrchestrationContext):
    payload = context.get_input() or {}
    retry = df.RetryOptions(first_retry_interval_in_milliseconds=5000, max_number_of_attempts=3)

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
        # Retries are exhausted -> run compensation, then report a clean failure.
        context.set_custom_status("compensating")
        yield context.call_activity("compensate_activity", str(exc))
        context.set_custom_status("failed")
        return {"status": "failed", "error": str(exc)}


# ===========================================================================
# Activities
# ===========================================================================
@app.activity_trigger(input_name="payload")
def extract_activity(payload):
    _maybe_fail(payload, "extract")
    with get_connection() as conn:
        cur = conn.cursor()
        customers = cur.execute("SELECT COUNT(*) FROM staging.customers").fetchval()
        orders = cur.execute("SELECT COUNT(*) FROM staging.orders").fetchval()
    logging.info("extract: customers=%s orders=%s", customers, orders)
    return {"customers": customers, "orders": orders}


@app.activity_trigger(input_name="payload")
def clean_activity(payload):
    _maybe_fail(payload, "clean")
    _run_sql(CLEAN_CUSTOMERS, CLEAN_ORDERS)
    logging.info("clean: customers & orders cleaned")
    return "cleaned"


@app.activity_trigger(input_name="payload")
def join_activity(payload):
    _maybe_fail(payload, "join")
    _run_sql(JOIN_TABLES)
    logging.info("join: tables joined")
    return "joined"


@app.activity_trigger(input_name="payload")
def load_activity(payload):
    _maybe_fail(payload, "load")
    _run_sql(LOAD_GOLD)
    with get_connection() as conn:
        rows = conn.cursor().execute(
            "SELECT COUNT(*) FROM gold.customer_sales_summary"
        ).fetchval()
    logging.info("load: gold refreshed with %s row(s)", rows)
    return rows


@app.activity_trigger(input_name="reason")
def compensate_activity(reason):
    """Saga compensation: undo partial work left by the failed run."""
    _run_sql(COMPENSATE)
    logging.warning("compensation ran — partial intermediates cleared. reason: %s", reason)
    return "compensated"
