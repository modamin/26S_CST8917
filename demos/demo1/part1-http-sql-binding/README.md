# Part 1 — HTTP trigger + Azure SQL bindings

A single function app with one HTTP route that demonstrates the **Azure SQL
input and output bindings**. Notice there is *no* database driver, no connection
handling, and no SQL `INSERT` in the code — the bindings do it.

## Endpoints

| Method | Route | Binding | What it does |
|--------|-------|---------|--------------|
| `GET`  | `/api/customers` | SQL **input** | Returns up to 100 rows from `staging.customers`. |
| `POST` | `/api/customers` | SQL **output** | **Upserts** a customer row (the "change to a table"). |

## Run

```bash
cp local.settings.json.example local.settings.json   # then fill in SqlConnectionString
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
func start
```

## Try it

```bash
# Read current customers
curl http://localhost:7071/api/customers

# Insert a new customer
curl -X POST http://localhost:7071/api/customers \
  -H "Content-Type: application/json" \
  -d '{"customer_id": 6, "name": "Margaret Hamilton", "email": "margaret@example.com", "city": "Boston"}'

# Update the same customer (same id -> UPSERT)
curl -X POST http://localhost:7071/api/customers \
  -H "Content-Type: application/json" \
  -d '{"customer_id": 6, "name": "Margaret Hamilton", "email": "mh@example.com", "city": "Cambridge"}'

# Confirm the change
curl http://localhost:7071/api/customers
```

## Key points for the demo

- The **output binding** target `staging.customers` is just a table name. Because
  `customer_id` is the table's primary key, the binding generates a MERGE
  (insert-or-update) automatically.
- The **input binding** runs the `command_text` query and hands the function an
  already-materialized `SqlRowList` — each item behaves like a dict.
- Connection string lives in `SqlConnectionString` (app setting), never in code.
