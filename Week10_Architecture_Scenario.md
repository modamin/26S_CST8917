# Serverless Architecture — Scenario Design Exercises

## Assignment Overview

You'll be given a real-world business problem and asked to **design a serverless solution** for it. There is no single correct answer. Each scenario can be solved in several defensible ways — with Durable Functions, with Logic Apps, with plain Azure Functions plus messaging, or with some combination of these. Your job is to choose an approach, design it, and **justify why** it fits the requirements and constraints better than the alternatives.

The work you've done so far — Azure Functions, Durable Functions, Logic Apps, and messaging (queues, topics, events) — gives you everything you need. The challenge is not knowing the services; it's deciding *which* to reach for and *why*.

### Assessment

There are no grades for this exercies, it'll be a group assessment and we will be looking for:

- **Fit** — does the design actually satisfy every requirement and constraint?
- **Justification** — can you explain why you chose this approach over the alternatives?
- **Tradeoff awareness** — do you know what your design gives up, and when you'd choose differently?
- You might not get a chance to present!
 
## NO AI USE do it from memory!

### Deliverables

You will be divided into 4 groups. Each group should pick a scenario and deliver the follownig:

1. **An architecture diagram** — the services in your solution, how data and control flow between them, and where state lives. Use any tool you like (draw.io, Visio, PowerPoint shapes, hand-drawn and photographed — all fine).
2. **A verbal presentation** (~5–7 minutes) walking us through your design and answering the questions listed under your scenario.


### Time & format

- **45 minutes** to design and prepare. Budget roughly 10 minutes to digest the scenario, 20 to decide and diagram, and 15 to prepare your talk.
- Work in your assigned group.
- You will not have time to build anything — this is a **design** exercise. Don't write code; make and defend decisions.

### A note on "solvable multiple ways"

Each scenario is deliberately under-specified in places. Where the requirements leave room, that room is intentional — it's where the interesting design decisions live. If two approaches both seem valid, that's expected. Pick one, and be ready to say what would make you switch to the other.

---

## Scenario 1 — Supplier Invoice Approval Pipeline

### Context

A company receives supplier invoices as PDFs (uploaded to a portal or arriving by email). Each invoice must be checked, possibly approved by a human, and the submitter notified of the outcome. Approvals can sit for days, and the system must never lose an in-flight invoice if a host restarts.

### Functional requirements

- Ingest an invoice and extract/validate the required fields; reject and notify the submitter if it's malformed.
- Auto-approve invoices under $1,000. Route anything above to a manager for a decision.
- If the manager doesn't respond within 48 hours, escalate to a director.
- Notify the submitter of the final outcome and persist an auditable record of every step.

### Constraints

- The workflow is long-running (hours to days) and must survive process/host restarts without losing state.
- Every step must be traceable for audit.
- A single stuck approval must not block other invoices.

### Your presentation should address

- Where state lives, and how it survives a restart that happens mid-approval.
- How you implement the 48-hour timeout and the escalation to a director.
- What would make you switch from your chosen approach to a different one.

---

## Scenario 2 — Batch Product-Media Processing

### Context

An e-commerce team uploads a batch of product images (anywhere from 10 to several thousand at once). Each image must be processed independently, and a single completion manifest is produced only once the whole batch is done.

### Functional requirements

- Trigger when a batch is uploaded.
- For each item: generate multiple renditions (thumbnail / web / print), extract metadata, and store the results.
- Produce one completion manifest summarizing successes and failures — but only after every item has finished.
- A few bad images should be reported as failures without failing the whole batch.

### Constraints

- Process items in parallel for throughput, but bound the parallelism to control cost and respect downstream limits.
- Processing must be idempotent — re-running a batch shouldn't duplicate work or outputs.
- The aggregation step must wait for all items, however many there are.

### Your presentation should address

- How you fan work out and then reliably detect "all done" before aggregating.
- How you cap concurrency, and why the number matters.
- What happens to the manifest if 3 of 500 images fail.

---

## Scenario 3 — Order Event Distribution & Shipment Tracking

### Context

When a customer places an order, several independent systems must react: reserve inventory, start fulfillment, send a confirmation, and feed analytics. New reactors get added over time. Separately, once an order has shipped, its status must be tracked with the carrier until it's delivered, and then the customer notified.

### Functional requirements

- A single "order placed" event fans out to multiple independent consumers.
- Consumers can be added or removed without changing the publisher.
- Inventory reservation must not be lost; analytics can be best-effort.
- After fulfillment, poll the carrier for shipment status until "delivered," then notify the customer.
- Failed / poison messages must be handled, not silently dropped.

### Constraints

- Loose coupling — the publisher must not know who its subscribers are.
- Different consumers need different delivery guarantees.
- One consumer being down must not block the others.

### Your presentation should address

- How the publisher stays unaware of its subscribers.
- How you give inventory "guaranteed" delivery while analytics stays best-effort — in the same design.
- How you track shipment status without a server polling in a tight loop 24/7.