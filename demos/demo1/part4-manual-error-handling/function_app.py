"""
Part 4 — Manual chaining WITH error handling.

This is Part 2's queue-chained pipeline, hardened by hand. Everything you have
to build yourself when there's no orchestrator is on display here:

  1. RETRIES        — host.json sets maxDequeueCount; a thrown step is retried.
  2. DEAD-LETTERING — after the retries are used up the runtime moves the message
                      to "<queue>-poison"; we add a handler per queue to react.
  3. RUN STATE      — we hand-record progress/errors in staging.pipeline_runs
                      (see runstate.py) so we can answer "what failed?".
  4. COMPENSATION   — the poison handler is where you'd undo partial work.
  5. OBSERVABILITY  — GET /api/status/{run_id} reads our home-made state table.

Inject a failure to see it all fire:
    POST /api/start?fail_at=join     (extract | clean | join | load)

Contrast with Part 5, where Durable Functions provides 1–4 out of the box.
"""

import json
import logging
import uuid

import azure.functions as func

import runstate
from db import get_connection
from pipeline_sql import CLEAN_CUSTOMERS, CLEAN_ORDERS, JOIN_TABLES, LOAD_GOLD

app = func.FunctionApp()

STORAGE = "AzureWebJobsStorage"


def _run_sql(*statements: str) -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        for sql in statements:
            cur.execute(sql)
        conn.commit()


def _maybe_fail(payload: dict, step: str) -> None:
    """Demo hook: blow up at the requested step so we can watch error handling."""
    if payload.get("fail_at") == step:
        raise RuntimeError(f"Injected failure at step '{step}' (fail_at={step})")


def _handle_poison(msg: func.QueueMessage, step: str) -> None:
    """Shared dead-letter handler: mark the run failed and run compensation."""
    payload = json.loads(msg.get_body().decode())
    run_id = payload.get("run_id", "unknown")
    error = f"Dead-lettered at step '{step}' after exhausting retries."
    runstate.mark_failed(run_id, step, error)
    # --- compensation: undo partial work so we don't leave half-built data ---
    # gold is rewritten atomically by the load step, so the only partial state
    # is in the staging intermediates; clear them.
    try:
        _run_sql(
            "TRUNCATE TABLE staging.customer_orders_joined;",
        )
    except Exception:  # compensation must not itself crash the handler
        logging.exception("[%s] compensation failed", run_id)
    logging.error("[%s] DEAD-LETTER at '%s' — run marked failed, compensation done", run_id, step)


# ===========================================================================
# HTTP starter
# ===========================================================================
@app.function_name(name="StartPipeline")
@app.route(route="start", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
@app.queue_output(arg_name="msg", queue_name="pipeline-extract", connection=STORAGE)
def start_pipeline(req: func.HttpRequest, msg: func.Out[str]) -> func.HttpResponse:
    run_id = str(uuid.uuid4())
    fail_at = req.params.get("fail_at")            # optional: extract|clean|join|load
    runstate.create_run(run_id)
    msg.set(json.dumps({"run_id": run_id, "fail_at": fail_at}))
    logging.info("[%s] pipeline started (fail_at=%s)", run_id, fail_at)
    return func.HttpResponse(
        json.dumps(
            {
                "status": "started",
                "run_id": run_id,
                "status_url": f"/api/status/{run_id}",
            }
        ),
        status_code=202,
        mimetype="application/json",
    )


# ===========================================================================
# HTTP status — reads our home-made run-state table
# ===========================================================================
@app.function_name(name="GetStatus")
@app.route(route="status/{run_id}", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def get_status(req: func.HttpRequest) -> func.HttpResponse:
    run = runstate.get_run(req.route_params.get("run_id"))
    if run is None:
        return func.HttpResponse("Run not found.", status_code=404)
    return func.HttpResponse(json.dumps(run, default=str), mimetype="application/json")


# ===========================================================================
# Pipeline steps — each wrapped in try/except: record + re-raise so the
# runtime retries, eventually dead-lettering to the *-poison queue.
# ===========================================================================
@app.function_name(name="Extract")
@app.queue_trigger(arg_name="msg", queue_name="pipeline-extract", connection=STORAGE)
@app.queue_output(arg_name="out", queue_name="pipeline-clean", connection=STORAGE)
def extract(msg: func.QueueMessage, out: func.Out[str]) -> None:
    payload = json.loads(msg.get_body().decode())
    run_id = payload["run_id"]
    try:
        runstate.update_step(run_id, "extract")
        _maybe_fail(payload, "extract")
        with get_connection() as conn:
            cur = conn.cursor()
            customers = cur.execute("SELECT COUNT(*) FROM staging.customers").fetchval()
            orders = cur.execute("SELECT COUNT(*) FROM staging.orders").fetchval()
        payload["extracted"] = {"customers": customers, "orders": orders}
        logging.info("[%s] extract ok: %s", run_id, payload["extracted"])
        out.set(json.dumps(payload))                # only enqueued on success
    except Exception as exc:
        runstate.record_error(run_id, "extract", str(exc), msg.dequeue_count)
        logging.error("[%s] extract failed (attempt %s): %s", run_id, msg.dequeue_count, exc)
        raise                                       # -> runtime retry / poison


@app.function_name(name="Clean")
@app.queue_trigger(arg_name="msg", queue_name="pipeline-clean", connection=STORAGE)
@app.queue_output(arg_name="out", queue_name="pipeline-join", connection=STORAGE)
def clean(msg: func.QueueMessage, out: func.Out[str]) -> None:
    payload = json.loads(msg.get_body().decode())
    run_id = payload["run_id"]
    try:
        runstate.update_step(run_id, "clean")
        _maybe_fail(payload, "clean")
        _run_sql(CLEAN_CUSTOMERS, CLEAN_ORDERS)
        logging.info("[%s] clean ok", run_id)
        out.set(json.dumps(payload))
    except Exception as exc:
        runstate.record_error(run_id, "clean", str(exc), msg.dequeue_count)
        logging.error("[%s] clean failed (attempt %s): %s", run_id, msg.dequeue_count, exc)
        raise


@app.function_name(name="Join")
@app.queue_trigger(arg_name="msg", queue_name="pipeline-join", connection=STORAGE)
@app.queue_output(arg_name="out", queue_name="pipeline-load", connection=STORAGE)
def join(msg: func.QueueMessage, out: func.Out[str]) -> None:
    payload = json.loads(msg.get_body().decode())
    run_id = payload["run_id"]
    try:
        runstate.update_step(run_id, "join")
        _maybe_fail(payload, "join")
        _run_sql(JOIN_TABLES)
        logging.info("[%s] join ok", run_id)
        out.set(json.dumps(payload))
    except Exception as exc:
        runstate.record_error(run_id, "join", str(exc), msg.dequeue_count)
        logging.error("[%s] join failed (attempt %s): %s", run_id, msg.dequeue_count, exc)
        raise


@app.function_name(name="Load")
@app.queue_trigger(arg_name="msg", queue_name="pipeline-load", connection=STORAGE)
def load(msg: func.QueueMessage) -> None:
    payload = json.loads(msg.get_body().decode())
    run_id = payload["run_id"]
    try:
        runstate.update_step(run_id, "load")
        _maybe_fail(payload, "load")
        _run_sql(LOAD_GOLD)
        runstate.mark_completed(run_id)
        logging.info("[%s] load ok — pipeline COMPLETED", run_id)
    except Exception as exc:
        runstate.record_error(run_id, "load", str(exc), msg.dequeue_count)
        logging.error("[%s] load failed (attempt %s): %s", run_id, msg.dequeue_count, exc)
        raise


# ===========================================================================
# Poison-queue handlers — one per step queue. The runtime delivers the original
# message here once maxDequeueCount is exceeded.
# ===========================================================================
@app.function_name(name="ExtractPoison")
@app.queue_trigger(arg_name="msg", queue_name="pipeline-extract-poison", connection=STORAGE)
def extract_poison(msg: func.QueueMessage) -> None:
    _handle_poison(msg, "extract")


@app.function_name(name="CleanPoison")
@app.queue_trigger(arg_name="msg", queue_name="pipeline-clean-poison", connection=STORAGE)
def clean_poison(msg: func.QueueMessage) -> None:
    _handle_poison(msg, "clean")


@app.function_name(name="JoinPoison")
@app.queue_trigger(arg_name="msg", queue_name="pipeline-join-poison", connection=STORAGE)
def join_poison(msg: func.QueueMessage) -> None:
    _handle_poison(msg, "join")


@app.function_name(name="LoadPoison")
@app.queue_trigger(arg_name="msg", queue_name="pipeline-load-poison", connection=STORAGE)
def load_poison(msg: func.QueueMessage) -> None:
    _handle_poison(msg, "load")
