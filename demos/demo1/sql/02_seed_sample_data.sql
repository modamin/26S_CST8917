/* =====================================================================
   Demo 1 — Sample data (intentionally DIRTY)
   Run this SECOND. Safe to re-run (clears raw tables first).

   The "dirt" gives the cleaning step real work to do:
     - leading/trailing whitespace in names
     - mixed-case / padded emails
     - NULL or empty city
     - a customer with a NULL email (should be dropped)
     - orders with NULL/negative amount         (should be dropped)
     - a 'cancelled' order                       (should be dropped)
     - an order for a non-existent customer (999) (dropped by the JOIN)
   ===================================================================== */

DELETE FROM staging.orders;
DELETE FROM staging.customers;
GO

-------------------------------------------------------------------------
-- Customers
-------------------------------------------------------------------------
INSERT INTO staging.customers (customer_id, name, email, city) VALUES
    (1, '  Ada Lovelace  ', 'ADA@EXAMPLE.COM ',      'London'),
    (2, 'Alan Turing',      ' alan@example.com',     'Manchester'),
    (3, 'Grace Hopper',     'grace@example.com',      NULL),
    (4, 'Katherine Johnson','Katherine@Example.com',  ''),
    (5, 'Linus Torvalds',   NULL,                     'Helsinki');  -- NULL email -> dropped by clean
GO

-------------------------------------------------------------------------
-- Orders
-------------------------------------------------------------------------
INSERT INTO staging.orders (order_id, customer_id, amount, order_date, status) VALUES
    (1001, 1,  120.00, '2026-01-05', 'completed'),
    (1002, 1,   80.50, '2026-02-11', 'completed'),
    (1003, 2,  200.00, '2026-01-20', 'completed'),
    (1004, 2,  -15.00, '2026-03-01', 'completed'),   -- negative amount  -> dropped
    (1005, 3,   55.25, '2026-02-28', 'completed'),
    (1006, 3,    NULL, '2026-03-10', 'completed'),    -- NULL amount      -> dropped
    (1007, 4,  300.00, '2026-01-15', 'cancelled'),    -- cancelled        -> dropped
    (1008, 4,   45.00, '2026-04-02', 'completed'),
    (1009, 999, 99.00, '2026-04-05', 'completed');    -- orphan customer  -> dropped by JOIN
GO

PRINT 'Sample data loaded.';
