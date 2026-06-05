/* =====================================================================
   Demo 1 — Verification queries
   Run any time to inspect the state of the pipeline.
   ===================================================================== */

PRINT '--- RAW (staging) ---';
SELECT 'customers' AS [table], COUNT(*) AS rows FROM staging.customers
UNION ALL
SELECT 'orders', COUNT(*) FROM staging.orders;

SELECT * FROM staging.customers ORDER BY customer_id;
SELECT * FROM staging.orders    ORDER BY order_id;

PRINT '--- CLEANED (staging) ---';
SELECT * FROM staging.customers_clean ORDER BY customer_id;
SELECT * FROM staging.orders_clean    ORDER BY order_id;

PRINT '--- JOINED (staging) ---';
SELECT * FROM staging.customer_orders_joined ORDER BY customer_id, order_id;

PRINT '--- GOLD (final result) ---';
SELECT * FROM gold.customer_sales_summary ORDER BY total_amount DESC;

/* Expected gold after a successful pipeline run:
     customer 1 (Ada)       -> 2 orders, 200.50
     customer 2 (Alan)      -> 1 order,  200.00   (negative order dropped)
     customer 3 (Grace)     -> 1 order,   55.25   (NULL-amount order dropped)
     customer 4 (Katherine) -> 1 order,   45.00   (cancelled order dropped)
     customer 5 (Linus)     -> absent            (NULL email dropped in clean)
     customer 999 order     -> absent            (orphan dropped by join)
*/
