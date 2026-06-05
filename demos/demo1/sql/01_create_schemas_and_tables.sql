/* =====================================================================
   Demo 1 — Schema & table setup
   Run this FIRST. Safe to re-run (drops and recreates objects).

   Layout:
     staging  (bronze) : raw landing tables + cleaned intermediates
     gold              : final, query-ready results
   ===================================================================== */

-------------------------------------------------------------------------
-- Schemas
-------------------------------------------------------------------------
IF SCHEMA_ID('staging') IS NULL EXEC('CREATE SCHEMA staging');
IF SCHEMA_ID('gold')    IS NULL EXEC('CREATE SCHEMA gold');
GO

-------------------------------------------------------------------------
-- Drop existing tables (children/intermediates first)
-------------------------------------------------------------------------
DROP TABLE IF EXISTS gold.customer_sales_summary;
DROP TABLE IF EXISTS staging.customer_orders_joined;
DROP TABLE IF EXISTS staging.orders_clean;
DROP TABLE IF EXISTS staging.customers_clean;
DROP TABLE IF EXISTS staging.orders;
DROP TABLE IF EXISTS staging.customers;
GO

-------------------------------------------------------------------------
-- Raw landing tables (bronze)
--   customer_id / order_id are PKs so Part 1's SQL output binding
--   can perform an UPSERT keyed on the primary key.
-------------------------------------------------------------------------
CREATE TABLE staging.customers (
    customer_id  INT            NOT NULL PRIMARY KEY,
    name         NVARCHAR(200)  NULL,
    email        NVARCHAR(256)  NULL,
    city         NVARCHAR(100)  NULL,
    created_at   DATETIME2(0)   NOT NULL CONSTRAINT DF_customers_created DEFAULT SYSUTCDATETIME()
);

CREATE TABLE staging.orders (
    order_id     INT            NOT NULL PRIMARY KEY,
    customer_id  INT            NULL,
    amount       DECIMAL(10, 2) NULL,
    order_date   DATE           NULL,
    status       NVARCHAR(20)   NULL
);
GO

-------------------------------------------------------------------------
-- Cleaned intermediates (written by the "clean" step)
-------------------------------------------------------------------------
CREATE TABLE staging.customers_clean (
    customer_id  INT            NOT NULL PRIMARY KEY,
    name         NVARCHAR(200)  NOT NULL,
    email        NVARCHAR(256)  NOT NULL,
    city         NVARCHAR(100)  NULL
);

CREATE TABLE staging.orders_clean (
    order_id     INT            NOT NULL PRIMARY KEY,
    customer_id  INT            NOT NULL,
    amount       DECIMAL(10, 2) NOT NULL,
    order_date   DATE           NOT NULL,
    status       NVARCHAR(20)   NOT NULL
);
GO

-------------------------------------------------------------------------
-- Joined intermediate (written by the "join" step)
-------------------------------------------------------------------------
CREATE TABLE staging.customer_orders_joined (
    id            INT IDENTITY(1, 1) NOT NULL PRIMARY KEY,
    customer_id   INT            NOT NULL,
    customer_name NVARCHAR(200)  NOT NULL,
    city          NVARCHAR(100)  NULL,
    order_id      INT            NOT NULL,
    amount        DECIMAL(10, 2) NOT NULL,
    order_date    DATE           NOT NULL
);
GO

-------------------------------------------------------------------------
-- Final result (gold)
-------------------------------------------------------------------------
CREATE TABLE gold.customer_sales_summary (
    customer_id      INT            NOT NULL PRIMARY KEY,
    customer_name    NVARCHAR(200)  NOT NULL,
    city             NVARCHAR(100)  NULL,
    total_orders     INT            NOT NULL,
    total_amount     DECIMAL(12, 2) NOT NULL,
    last_order_date  DATE           NOT NULL,
    processed_at     DATETIME2(0)   NOT NULL
);
GO

PRINT 'Schemas and tables created.';
