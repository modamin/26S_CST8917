"""
Part 1 — A single HTTP-triggered function that talks to Azure SQL using the
native SQL bindings (no database driver code).

  GET  /api/customers          -> reads rows via a SQL *input* binding
  POST /api/customers          -> upserts a row via a SQL *output* binding
                                  (this is the "change to a table")

The bindings handle the connection and the SQL; the function body only deals
with HTTP. The output binding performs an UPSERT keyed on the table's primary
key (customer_id), so POSTing an existing id updates it.
"""

import json
import logging

import azure.functions as func

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


# ---------------------------------------------------------------------------
# READ — SQL input binding
# ---------------------------------------------------------------------------
@app.function_name(name="GetCustomers")
@app.route(route="customers", methods=["GET"])
@app.sql_input(
    arg_name="customers",
    command_text=(
        "SELECT TOP 100 customer_id, name, email, city "
        "FROM staging.customers ORDER BY customer_id"
    ),
    command_type="Text",
    connection_string_setting="SqlConnectionString",
)
def get_customers(req: func.HttpRequest, customers: func.SqlRowList) -> func.HttpResponse:
    rows = [dict(r) for r in customers]
    logging.info("GetCustomers returned %d row(s).", len(rows))
    return func.HttpResponse(
        json.dumps(rows, default=str),
        mimetype="application/json",
    )


# ---------------------------------------------------------------------------
# WRITE — SQL output binding (UPSERT on primary key)
# ---------------------------------------------------------------------------
@app.function_name(name="UpsertCustomer")
@app.route(route="customers", methods=["POST"])
@app.sql_output(
    arg_name="customer",
    command_text="staging.customers",            # target table
    connection_string_setting="SqlConnectionString",
)
def upsert_customer(
    req: func.HttpRequest,
    customer: func.Out[func.SqlRow],
) -> func.HttpResponse:
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse("Request body must be valid JSON.", status_code=400)

    missing = [f for f in ("customer_id", "name", "email") if f not in body]
    if missing:
        return func.HttpResponse(
            f"Missing required field(s): {', '.join(missing)}",
            status_code=400,
        )

    row = func.SqlRow.from_dict(
        {
            "customer_id": body["customer_id"],
            "name": body["name"],
            "email": body["email"],
            "city": body.get("city"),
        }
    )
    customer.set(row)                            # binding writes the row on return

    logging.info("Upserted customer_id=%s", body["customer_id"])
    return func.HttpResponse(
        json.dumps({"status": "upserted", "customer_id": body["customer_id"]}),
        status_code=200,
        mimetype="application/json",
    )
