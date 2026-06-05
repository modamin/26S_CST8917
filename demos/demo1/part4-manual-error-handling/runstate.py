"""
Home-made run-state store for the manual pipeline.

Because manual chaining has no built-in notion of "a run", we record progress
and errors ourselves in staging.pipeline_runs. This is exactly the bookkeeping
Durable Functions gives you for free (Part 5).
"""

from db import get_connection


def create_run(run_id: str) -> None:
    with get_connection() as conn:
        conn.cursor().execute(
            "INSERT INTO staging.pipeline_runs (run_id, status, current_step) "
            "VALUES (?, 'running', 'start')",
            run_id,
        )
        conn.commit()


def update_step(run_id: str, step: str) -> None:
    with get_connection() as conn:
        conn.cursor().execute(
            "UPDATE staging.pipeline_runs "
            "SET current_step = ?, status = 'running', updated_at = SYSUTCDATETIME() "
            "WHERE run_id = ?",
            step,
            run_id,
        )
        conn.commit()


def record_error(run_id: str, step: str, error: str, attempt: int) -> None:
    """Record a (possibly transient) failure for one attempt — run stays 'running'."""
    with get_connection() as conn:
        conn.cursor().execute(
            "UPDATE staging.pipeline_runs "
            "SET current_step = ?, attempts = ?, last_error = ?, updated_at = SYSUTCDATETIME() "
            "WHERE run_id = ?",
            step,
            attempt,
            error,
            run_id,
        )
        conn.commit()


def mark_failed(run_id: str, step: str, error: str) -> None:
    """Terminal failure — the message was dead-lettered after exhausting retries."""
    with get_connection() as conn:
        conn.cursor().execute(
            "UPDATE staging.pipeline_runs "
            "SET status = 'failed', current_step = ?, last_error = ?, "
            "    updated_at = SYSUTCDATETIME(), completed_at = SYSUTCDATETIME() "
            "WHERE run_id = ?",
            step,
            error,
            run_id,
        )
        conn.commit()


def mark_completed(run_id: str) -> None:
    with get_connection() as conn:
        conn.cursor().execute(
            "UPDATE staging.pipeline_runs "
            "SET status = 'completed', current_step = 'load', "
            "    updated_at = SYSUTCDATETIME(), completed_at = SYSUTCDATETIME() "
            "WHERE run_id = ?",
            run_id,
        )
        conn.commit()


def get_run(run_id: str):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT run_id, status, current_step, attempts, last_error, "
            "       started_at, completed_at "
            "FROM staging.pipeline_runs WHERE run_id = ?",
            run_id,
        )
        row = cur.fetchone()
        if row is None:
            return None
        columns = [c[0] for c in cur.description]
        return dict(zip(columns, row))
