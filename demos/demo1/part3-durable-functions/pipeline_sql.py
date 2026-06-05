"""
Identical transformation SQL to Part 2 — only the orchestration differs.
Kept as a copy so each part folder is a self-contained, deployable function app.
"""

# --- CLEAN -----------------------------------------------------------------
CLEAN_CUSTOMERS = """
TRUNCATE TABLE staging.customers_clean;
INSERT INTO staging.customers_clean (customer_id, name, email, city)
SELECT customer_id,
       LTRIM(RTRIM(name)),
       LOWER(LTRIM(RTRIM(email))),
       NULLIF(LTRIM(RTRIM(city)), '')
FROM   staging.customers
WHERE  name IS NOT NULL
  AND  email IS NOT NULL
  AND  LTRIM(RTRIM(email)) <> '';
"""

CLEAN_ORDERS = """
TRUNCATE TABLE staging.orders_clean;
INSERT INTO staging.orders_clean (order_id, customer_id, amount, order_date, status)
SELECT order_id, customer_id, amount, order_date, status
FROM   staging.orders
WHERE  customer_id IS NOT NULL
  AND  amount IS NOT NULL
  AND  amount >= 0
  AND  order_date IS NOT NULL
  AND  LOWER(status) <> 'cancelled';
"""

# --- JOIN ------------------------------------------------------------------
JOIN_TABLES = """
TRUNCATE TABLE staging.customer_orders_joined;
INSERT INTO staging.customer_orders_joined
        (customer_id, customer_name, city, order_id, amount, order_date)
SELECT  c.customer_id, c.name, c.city, o.order_id, o.amount, o.order_date
FROM    staging.customers_clean c
JOIN    staging.orders_clean    o ON o.customer_id = c.customer_id;
"""

# --- LOAD (gold) -----------------------------------------------------------
LOAD_GOLD = """
TRUNCATE TABLE gold.customer_sales_summary;
INSERT INTO gold.customer_sales_summary
        (customer_id, customer_name, city, total_orders, total_amount,
         last_order_date, processed_at)
SELECT  customer_id, customer_name, MAX(city),
        COUNT(*), SUM(amount), MAX(order_date), SYSUTCDATETIME()
FROM    staging.customer_orders_joined
GROUP BY customer_id, customer_name;
"""
