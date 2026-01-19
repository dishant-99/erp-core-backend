ERP Core Backend (Inventory · Procurement · Sales)

Overview
This repository contains the core ERP backend execution layer for an AI-first ERP system.
It implements:
•	Deterministic business logic
•	Clear state transitions
•	Clean API contracts
•	A relational source-of-truth database
This backend is designed to be AI-orchestrated, not AI-controlled.
AI will sit on top of this system to interpret intent and trigger workflows —
it will never directly mutate business logic or database state.

Design Philosophy
1.	Business logic must be deterministic and auditable
2.	AI is an operator, not a decision-maker
3.	All workflows reduce to atomic state transitions
4.	Illegal transitions are explicitly blocked
5.	ERP correctness > flexibility

This ensures:
•	Financial correctness
•	Compliance
•	Explainability
•	Safety against AI hallucinations

Modules Implemented

1. Inventory
Inventory acts as the central source of truth.
Capabilities:
•	Tracks stock per item
•	Updates via:
o	Procurement inbound deliveries
o	Sales outbound deliveries
•	Supports reservation logic:
o	Stock is reserved when a Sales Order is confirmed
o	Finalized when delivery is completed

2. Procurement
Procurement models real-world supplier workflows:
Flow:
Purchase Order
→ Supplier Acknowledgement (negotiation supported)
→ Delivery Inbound
→ Bill
Key features:
•	Multiple acknowledgements per PO (revision / supersession)
•	Final acknowledgement drives billing
•	Supplier account balance updates automatically
•	State-guarded transitions (no skipping steps)

3. Sales
Sales models customer-facing workflows:
Flow:
Quote
→ Sales Order
→ Invoice
→ Delivery Outbound
Key features:
•	Quote-based and direct Sales Orders supported
•	Inventory reserved at SO creation
•	Invoice auto-created on SO confirmation
•	Client account balance updates automatically
•	Delivery handled explicitly (not assumed)

State Management
Every core entity has explicit states.
Examples:
•	Quotes: sent → accepted / rejected / superseded
•	Sales Orders: confirmed → delivered → invoiced
•	Purchase Orders: pending → acknowledged → received
•	Invoices / Bills: pending → paid
State guards prevent:
•	Double delivery
•	Double billing
•	Invalid transitions

API-First Architecture
All logic is exposed via REST APIs.
This allows:
•	UI clients
•	AI agents
•	Integrations (email, WhatsApp, EDI)
•	Future workflow engines
The backend is headless by design.

AI Orchestration Layer (Planned)
AI responsibilities:
•	Parse natural language intent
•	Select workflows
•	Call APIs in correct sequence
•	Monitor states, deadlines, and anomalies
AI does not:
•	Write directly to the database
•	Create new business rules
•	Bypass validations
•	Modify financial logic
This separation is intentional.

What This Repo Is (and Is Not)
This repo is
•	A production-grade business logic foundation
•	Deterministic and extensible
•	Designed for real SME workflows
This repo is not
•	A UI
•	A workflow designer
•	An AI model
•	A completed ERP

What’s Next
Planned work:
•	Accounting suite (GL, journals, partial payments)
•	Partial deliveries & partial invoicing
•	Workflow configuration layer
•	AI orchestration & learning layer
•	Audit & compliance extensions

*Important* Diagrams
High-level workflows are documented in /docs:
•	Procurement flow
•	Sales flow
These diagrams map directly to the implemented code paths.


Tech Stack
•	Backend: Python (FastAPI)
•	Database: PostgreSQL
•	ORM: SQLAlchemy
•	IDs: UUIDs for global uniqueness

