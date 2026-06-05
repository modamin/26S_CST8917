/* =====================================================================
   Demo 1 — Run-state table for Part 4 (manual error handling)
   Run this before using Part 4.

   Durable Functions (Parts 3 & 5) track run state for you. With manual
   chaining you have to build it yourself — this table is that homemade
   "where is my run / what failed" store.
   ===================================================================== */

DROP TABLE IF EXISTS staging.pipeline_runs;
GO

CREATE TABLE staging.pipeline_runs (
    run_id        UNIQUEIDENTIFIER NOT NULL PRIMARY KEY,
    status        NVARCHAR(20)     NOT NULL,                    -- running | completed | failed
    current_step  NVARCHAR(20)     NULL,                        -- start | extract | clean | join | load
    attempts      INT              NOT NULL CONSTRAINT DF_runs_attempts DEFAULT 0,
    last_error    NVARCHAR(MAX)    NULL,
    started_at    DATETIME2(0)     NOT NULL CONSTRAINT DF_runs_started DEFAULT SYSUTCDATETIME(),
    updated_at    DATETIME2(0)     NOT NULL CONSTRAINT DF_runs_updated DEFAULT SYSUTCDATETIME(),
    completed_at  DATETIME2(0)     NULL
);
GO

PRINT 'staging.pipeline_runs created.';
