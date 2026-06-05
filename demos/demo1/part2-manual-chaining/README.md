# Part 2 — Manual function chaining (Storage Queues)

The extract → clean → join → load pipeline, built as **five separate functions**
wired together with Storage Queue triggers. This is the "do it by hand" approach.

```
POST /api/start ─► [pipeline-extract] ─► Extract
                                          └─► [pipeline-clean] ─► Clean
                                                                  └─► [pipeline-join] ─► Join
                                                                                         └─► [pipeline-load] ─► Load ─► gold
```

## Run

You need the **Azurite** storage emulator running (the queues live there):

```bash
azurite          # in a separate terminal

cp local.settings.json.example local.settings.json   # fill in SqlOdbcConnectionString
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
func start
```

## Try it

```bash
curl -X POST http://localhost:7071/api/start
# -> {"status": "started", "run_id": "..."}
```

Watch the `func start` console: you'll see `Extract`, `Clean`, `Join`, `Load`
fire one after another as each message lands on the next queue. Then verify:

```bash
sqlcmd -S <server> -d <db> -U <user> -P <pwd> -i ../sql/03_verify.sql
```

## What to point out in the demo

- **Each step hard-codes the next queue name** (`queue_name="pipeline-clean"`,
  etc.). The flow is defined by *convention spread across functions*, not in one
  place. Reordering or inserting a step means editing several files.
- **State is invisible.** To know where a run is, you inspect queues and logs.
  There's no "get me the status of run X" call.
- **Failures are messy.** If `Join` throws, its message goes back on the queue
  and eventually to a poison queue — but `Extract`/`Clean` already ran. You own
  the retry/restart story.
- The transformation SQL lives in [pipeline_sql.py](pipeline_sql.py), shared
  verbatim with Part 3 — only the *orchestration* differs between the two parts.
