# Automotive CS03 — AI-Powered Customer Service Copilot

## Architecture & Design Document

**Version:** 1.0
**Stack:** FastAPI · Angular · Google Gemini · Anthropic Claude · ChromaDB · MySQL
**Theme:** Real-Time Vehicle Diagnostics & Remote Monitoring Copilot

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Overview](#2-system-overview)
3. [High-Level Architecture](#3-high-level-architecture)
4. [Component Architecture](#4-component-architecture)
   - 4.1 [Frontend (Angular)](#41-frontend-angular)
   - 4.2 [Backend (FastAPI)](#42-backend-fastapi)
   - 4.3 [AI Agent Layer](#43-ai-agent-layer)
   - 4.4 [Orchestration Engine](#44-orchestration-engine)
   - 4.5 [RAG System (Knowledge Retrieval)](#45-rag-system-knowledge-retrieval)
   - 4.6 [Services Layer](#46-services-layer)
   - 4.7 [Data Layer](#47-data-layer)
5. [Data Flow Diagrams](#5-data-flow-diagrams)
6. [API Reference](#6-api-reference)
7. [Database Schema](#7-database-schema)
8. [Intent Classification & Routing](#8-intent-classification--routing)
9. [Technology Stack](#9-technology-stack)
10. [Implementation Status](#10-implementation-status)
11. [Pending Features & Roadmap](#11-pending-features--roadmap)
12. [Setup & Running Locally](#12-setup--running-locally)

---

## 1. Executive Summary

Automotive CS03 is an **AI-powered productivity copilot** for automotive customer service agents. It reduces Average Handling Time (AHT) and increases First-Call Resolution (FCR) by providing agents with real-time access to:

- Vehicle diagnostics and fault code interpretation
- Warranty eligibility validation
- Intelligent service scheduling
- Retrieval-augmented knowledge base (service manuals, TSBs)
- Natural language conversational interface with multi-agent routing

**Business Metrics Targeted:**

| Metric | Target Impact |
|---|---|
| Average Handling Time (AHT) | Reduce by ~30% via instant data retrieval |
| First-Call Resolution (FCR) | Increase by surfacing relevant docs & warranty status immediately |
| Agent Productivity | Copilot eliminates manual lookup across 4+ systems |
| Customer Satisfaction | Faster, accurate resolution of vehicle issues |

---

## 2. System Overview

```
╔══════════════════════════════════════════════════════════════════════════════════════════╗
║                    AUTOMOTIVE AI COPILOT — SYSTEM OVERVIEW                               ║
╚══════════════════════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND  (Angular 19 · Standalone)                        │
│                                                                                         │
│   ┌──────────┐  ┌──────────┐  ┌──────────────────────────────────────────────────────┐  │
│   │  Login   │  │  Signup  │  │  Protected Routes (authGuard + JWT)                  │  │
│   └──────────┘  └──────────┘  │                                                      │  │
│                                │  ┌─────────────┐  ┌──────────┐  ┌────────────────┐  │  │
│                                │  │  Copilot    │  │ Vehicles │  │ Vehicle Detail │  │  │
│                                │  │  Panel  ◄──┼──►  Info    │  │                 │  │  │
│                                │  │  (Chat UI)  │  └──────────┘  └────────────────┘  │  │
│                                │  │             │  ┌──────────┐  ┌──────────────┐    │  │
│                                │  │  sends msg  │  │ Warranty │  │  Scheduling  │    │  │
│                                │  │  + vehicle_ │  └──────────┘  └──────────────┘    │  │
│                                │  │  id + user_ │  ┌──────────┐                      │  │
│                                │  │  id         │  │Insurance │                      │  │
│                                │  └──────┬──────┘  └──────────┘                      │  │
│                                └─────────┼────────────────────────────────────────── ┘  │
│                                          │                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │  ApiService  (HttpClient + authInterceptor → adds Bearer JWT to every request)  │    │
│  │  • askAgent()     POST /api/agent/ask                                           │    │
│  │  • listVehicles() GET  /api/vehicles/          • getWarranty()                  │    │
│  │  • getSlots()     POST /api/scheduling/slots   • bookAppt()                     │    │
│  │  • getInsurance() GET  /api/insurance/{code}   • getTelematics()                │    │
│  └─────────────────────────────────────┬───────────────────────────────────────────┘    │
└────────────────────────────────────────┼────────────────────────────────────────────────┘
                                         │  HTTP/REST  (CORS → localhost:4200)
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND  (FastAPI + Uvicorn)                               │
│                                                                                         │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │                         API LAYER  (FastAPI Routers)                              │  │
│  │                                                                                   │  │
│  │  /api/agent/ask ──┐   /api/vehicles   /api/warranty   /api/scheduling             │  │
│  │  (POST)           │   /api/telematics /api/insurance  /api/user (auth)            │  │
│  └───────────────────┼───────────────────────────────────────────────────────────────┘  │
│                      │                                                                  │
│                      ▼                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │                        ORCHESTRATOR  (orch/orchestrator.py)                       │  │
│  │                                                                                   │  │
│  │  1. classify_intent(message)  →  Gemini LLM                                       │  │
│  │     Returns: ["vehicle"], ["warranty","scheduler"], ["telemetry"], ["general"]    │  │
│  │                                                                                   │  │
│  │  2. Spawn matched agents in PARALLEL  (asyncio.gather)                            │  │
│  │                          │                                                        │  │
│  │      ┌───────────────────┼───────────────────┐                                    │  │
│  │      ▼                   ▼                   ▼                   ▼                │  │
│  │  [vehicle]          [warranty]          [scheduler]         [telemetry]           │  │
│  │      │                   │                   │                   │                │  │
│  │  3. asyncio.gather(*tasks) → collect all responses                                │  │
│  │  4. _merge_responses() → deduplicate + join with \n\n                             │  │
│  │                                                                                   │  │
│  │  Fallback 1 ──► RAG Agent (intent=general + has knowledge question)               │  │
│  │  Fallback 2 ──► Conversational LLM  run_agent()  (session history)                │  │
│  └───────────────────────────────────────────────────────────────────────────────────┘  │
│                      │                                                                  │
│  ┌───────────────────┼───────────────────────────────────────────────────────────────┐  │
│  │                   AGENT LAYER                                                     │  │
│  │                                                                                   │  │
│  │  ┌────────────────────┐  ┌─────────────────────┐  ┌────────────────────┐          │  │
│  │  │   VehicleAgent     │  │  TelemetryAgent     │  │  SchedulerAgent    │          │  │
│  │  │                    │  │                     │  │                    │          │  │
│  │  │ resolve_vehicle()  │  │ get_vehicle_data()  │  │ infer_service()    │          │  │
│  │  │ detect_fields()    │  │ decode_dtc()        │  │ infer_urgency()    │          │  │
│  │  │ ├ rule-based       │  │ _diagnose()─────┐   │  │ get_slots()        │          │  │
│  │  │ └ LLM fallback     │  │                 │   │  │ is_booking_intent()│          │  │
│  │  │ fetch_data()       │  │ reads from:     │   │  │ _create_appt()─┐   │          │  │
│  │  │ ├ cs03_vehicle     │  │ cs03_vehicle    │   │  │ ├ confirms slot │  │          │  │
│  │  │ ├ cs03_warranty    │  │ cs03_telematics │   │  │ └ INSERT to DB  │  │          │  │
│  │  │ └ cs03_scheduler   │  │                 │   │  └────────────────┼───┘          │  │
│  │  │ _compose_res()──┐  │  │                 │   │                   │              │  │
│  │  └─────────────────┼──┘  └─────────────────┼───┘                   │              │  │
│  │                    │                       │                       │              │  │
│  │  ┌────────────────────┐  ┌─────────────────────┐  ┌────────────────────┐          │  │
│  │  │  WarrantyAgent     │  │    RAGAgent         │  │  ConversationalLLM │          │  │
│  │  │                    │  │                     │  │  (askAI.py)        │          │  │
│  │  │ infer_repair_type()│  │ enrich_query()      │  │                    │          │  │
│  │  │ check_warranty()   │  │ search_docs()──┐    │  │ load_history()     │          │  │
│  │  │ ├ load rules       │  │ LLM synthesize │    │  │ call Gemini LLM    │          │  │
│  │  │ ├ check dates      │  │                │    │  │ save_history()     │          │  │
│  │  │ └ check mileage    │  │ ChromaDB ──────┘    │  │ cs03_agent DB      │          │  │
│  │  └────────────────────┘  └─────────────────────┘  └────────────────────┘          │  │
│  │                                    │                                              │  │
│  │                    all LLM calls ──┴──────────────────────────────────────►       │  │
│  └────────────────────────────────────────────────────────────────────────────┼──────┘  │
│                                                                                │        │
│  ┌─────────────────────────────────────────────────────────────────────────────┼─────┐  │
│  │                 SERVICES LAYER  (Business Logic, no HTTP)                   │     │  │
│  │                                                                             │     │  │
│  │  warranty_engine.check_warranty()     scheduler.get_slots()                │      │  │
│  │  telematics.get_vehicle_data()        insurance.get_vehicle_insurance()     │     │  │
│  └─────────────────────────────────────────────────────────────────────────────┼─────┘  │
│                                                                                │        │
└────────────────────────────────────────────────────────────────────────────────┼────────┘
                                                                                 │
           ┌─────────────────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                         INFRASTRUCTURE LAYER                                             │
│                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐     │
│  │                    MySQL  (same server · 7 isolated schemas)                    │     │
│  │                                                                                 │     │
│  │  ┌─────────────┐ ┌─────────────┐ ┌──────────────┐ ┌─────────────────────────┐   │     │
│  │  │cs03_vehicle │ │cs03_warranty│ │cs03_scheduler│ │   cs03_telematics       │   │     │
│  │  │─────────────│ │─────────────│ │──────────────│ │─────────────────────────│   │     │
│  │  │customers    │ │warranty_    │ │technicians   │ │dtc_codes                │   │     │
│  │  │vehicles     │ │ records     │ │service_      │ │ (P0300, P0217, B0001…)  │   │     │
│  │  │active_fault_│ │warranty_    │ │ appointments │ │telematics_snapshots     │   │     │
│  │  │ codes       │ │ rules       │ │              │ │ (fuel, temp, oil_life…) │   │     │
│  │  └─────────────┘ └─────────────┘ └──────────────┘ └─────────────────────────┘   │     │
│  │                                                                                 │     │
│  │  ┌─────────────┐ ┌─────────────┐ ┌──────────────────────────────┐               │     │
│  │  │  cs03_auth  │ │ cs03_agent  │ │       cs03_insurance         │               │     │
│  │  │─────────────│ │─────────────│ │──────────────────────────────│               │     │
│  │  │users        │ │agent_       │ │insurance_plans               │               │     │
│  │  │(JWT, roles) │ │ sessions    │ │vehicle_insurance             │               │     │
│  │  └─────────────┘ └─────────────┘ └──────────────────────────────┘               │     │
│  └─────────────────────────────────────────────────────────────────────────────────┘     │
│                                                                                          │
│  ┌──────────────────────────────┐   ┌──────────────────────────────────────────────┐     │
│  │  ChromaDB (Vector Store)     │   │  Gemini API  (gemini-2.5-flash-lite)         │     │
│  │  ──────────────────────────  │   │  ──────────────────────────────────────────  │     │
│  │  • Service manuals           │   │  Used by:                                    │     │
│  │  • Repair guides             │   │  • classify_intent()  → intent routing       │     │
│  │  • Historical cases          │   │  • VehicleAgent._compose_response()          │     │
│  │  • FAQs                      │   │  • TelemetryAgent._diagnose()                │     │
│  │  Embedded at startup         │   │  • VehicleAgent._detect_fields_llm()         │     │
│  │  Queried by RAGAgent         │   │  • WarrantyAgent (RAG fallback)              │     │
│  └──────────────────────────────┘   │  • ConversationalAgent (history chat)        │     │
│                                     └──────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────────────────────────────┘

```

---

## 3. High-Level Architecture

### Architectural Pattern
**Multi-Agent Orchestration with RAG** — a supervisor orchestrator classifies incoming user queries into one or more intents, dispatches them to specialist agents in parallel, and merges structured responses into a single unified reply.

### Core Principles
- **Intent-first routing** — every message is classified before any agent is invoked
- **Agent specialization** — each agent owns a single domain (vehicle, warranty, scheduling, telematics)
- **RAG-augmented responses** — knowledge retrieval supplements structured data for unrecognized questions
- **Layered architecture** — API → Orchestrator → Agent → Service → Database

---

## 4. Component Architecture

### 4.1 Frontend (Angular)

**Framework:** Angular 21.2.3 (Standalone Components)

```
frontend/src/app/
├── components/
│   ├── login/                  # Authentication entry point
│   ├── signup/                 # User registration
│   ├── dashboard-home/         # App shell with sidebar navigation
│   ├── vehicles-info/          # Vehicle list & fleet overview
│   ├── vehicle-detail/         # Single vehicle info + warranty check
│   ├── vehicle-stats/          # Telematics gauges (fuel, battery, engine temp)
│   ├── copilot-panel/          # AI chat interface (core UX)
│   ├── maintenance-timeline/   # Service history visualization
│   ├── scheduling/             # Appointment booking UI
│   ├── warranty/               # Warranty coverage view
│   ├── insurance/              # Insurance info (stub)
│   └── ai-diagnostics/         # Dashboard warning light analyzer (stub)
├── services/
│   ├── api.service.ts          # All HTTP calls to backend
│   └── auth.service.ts         # JWT token management
└── guards/
    └── auth.guard.ts           # Route protection
```

**Routing Structure:**

| Path | Component | Auth Required |
|---|---|---|
| `/` | LoginComponent | No |
| `/signup` | SignupComponent | No |
| `/home` | VehiclesinfoComponent | Yes |
| `/vehicles-dashboard` | VehiclesinfoComponent | Yes |
| `/vehicles-details` | VehicleDetailComponent | Yes |
| `/copilot` | CopilotPanelComponent | Yes |
| `/warranty` | Warranty | Yes |
| `/scheduling` | Scheduling | Yes |
| `/insurance` | Insurance | Yes |

---

### 4.2 Backend (FastAPI)

**Entry Point:** `backend/app/main.py`

**Startup Sequence:**
1. Create MySQL tables (SQLAlchemy auto-create)
2. Ingest knowledge base into ChromaDB (skips if already loaded)
3. Start FastAPI application

**CORS:** Configured for `http://localhost:4200` (Angular dev server)

```
backend/app/
├── main.py             # FastAPI app, lifespan, router registration
├── config.py           # Pydantic Settings (env vars / .env file)
├── api/                # HTTP route handlers
│   ├── agent.py        # POST /api/agent/ask
│   ├── vehicles.py     # GET /api/vehicles/
│   ├── warranty.py     # POST /api/warranty/check
│   ├── scheduling.py   # POST /api/scheduling/slots
│   ├── telematics.py   # GET /api/telematics/{id}, POST /api/telematics/decode
│   └── user.py         # POST /api/user/signup, /login
├── agent/              # AI agent implementations
├── orch/               # Multi-agent orchestrator
├── rag/                # RAG pipeline
├── services/           # Business logic
└── db/                 # ORM models & database session
```

---

### 4.3 AI Agent Layer

Each agent implements a `process_query(user_message, context) → dict` interface.

#### Vehicle Agent (`agent/vehicle_agent.py`)
**Purpose:** Retrieve structured vehicle information from MySQL
**Capabilities:**
- Resolve vehicle by `vehicle_code` or `user_id` from context
- Detect requested fields (model, make, year, owner, faults, warranty, service history)
- Return structured vehicle summary with active fault codes

**Output Schema:**
```json
{
  "response": "Vehicle details for VH001...",
  "vehicle_code": "VH001",
  "make": "Toyota",
  "model": "Camry",
  "year": 2021,
  "fault_codes": ["P0300", "P0171"]
}
```

---

#### Warranty Agent (`agent/warranty_agent.py`)
**Purpose:** Validate warranty eligibility
**Current State:** Partial — hardcoded OEM lookup for "VH002", falls back to RAG
**Target State:** Should call `services/warranty_engine.py → check_warranty()`

---

#### Scheduler Agent (`agent/scheduler_agent.py`)
**Purpose:** Recommend service appointment slots
**Current State:** Stub — returns placeholder text
**Target State:** Should call `services/scheduler.py → get_slots(service_type, urgency)`

---

#### Telemetry Agent (`agent/telemetry_agent.py`)
**Purpose:** Interpret live vehicle sensor data and fault codes
**Current State:** Stub — returns placeholder text
**Target State:** Should call `services/telematics.py` to decode DTCs and return health summary

---

#### RAG Agent (`agent/rag_agent.py`)
**Purpose:** Answer questions from the knowledge base (service manuals, TSBs)
**Current State:** Broken import path — not wired into orchestrator
**Target State:** Called as fallback when no structured agent can answer

---

### 4.4 Orchestration Engine

**File:** `orch/orchestrator.py`

```
User Message
     │
     ▼
┌──────────────────────┐
│   classify_intent()  │  ← Gemini LLM
│   Returns list of    │
│   matched intents    │
└──────────┬───────────┘
           │
     ┌─────┴──────────────────────────────────┐
     │    Multi-Intent Parallel Dispatch       │
     ├────────────────────────────────────────┤
     │  "vehicle"   → VehicleAgent            │
     │  "warranty"  → WarrantyAgent           │
     │  "scheduler" → SchedulerAgent          │
     │  "telemetry" → TelemetryAgent          │
     │  "general"   → run_agent() (LLM)       │
     └──────────────┬─────────────────────────┘
                    │
              merge_responses()
                    │
                    ▼
           Unified JSON Response
           { response, data, sources }
```

**Intent Types:**

| Intent | Triggered By | Agent Invoked |
|---|---|---|
| `vehicle` | "what car", "vehicle model", "VIN", "owner" | VehicleAgent |
| `warranty` | "warranty", "covered", "claim", "expired" | WarrantyAgent |
| `scheduler` | "book", "appointment", "schedule", "service slot" | SchedulerAgent |
| `telemetry` | "fault code", "engine", "battery", "OBD", "diagnostics" | TelemetryAgent |
| `general` | Everything else | Gemini LLM direct |

---

### 4.5 RAG System (Knowledge Retrieval)

**Vector Store:** ChromaDB (persistent at `./chroma_db`)
**Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2`
**Collection:** `automotive_knowledge`

```
knowledge_base/*.txt
        │
        ▼ (on startup)
   ingest.py
   ├── Read .txt files
   ├── Chunk at 500 chars (450 char overlap)
   └── Store in ChromaDB with source metadata
        │
        ▼ (at query time)
   retriever.py → search_docs(query, top_k=3)
   └── Semantic similarity search
       └── Returns top-k chunks + source filenames
```

**Current Knowledge Base:**
- `warranty.txt` — minimal warranty policy text (156 bytes)

**Target Knowledge Base:**
- Vehicle Owner Manuals (per make/model/year)
- Technical Service Bulletins (TSBs)
- OBD-II fault code reference database
- Recall notices
- Maintenance interval schedules

---

### 4.6 Services Layer

**Pure business logic — no LLM dependency**

#### Warranty Engine (`services/warranty_engine.py`)

Coverage mapping:
```python
COVERAGE_MAP = {
    "bumper_to_bumper": ["electrical", "interior", "ac", "brakes"],
    "powertrain":       ["engine", "transmission", "drivetrain"],
    "emission":         ["catalytic_converter", "o2_sensor"],
}
EXCLUSIONS = ["tires", "wiper_blades", "wear_items", "accident_damage"]
```

Logic: Checks repair type against coverage map → validates date and mileage against `WarrantyRecord` → returns coverage status with expiry and miles remaining.

---

#### Scheduler Service (`services/scheduler.py`)

Technician specialization matrix:
```
T01_Kumar  → engine, transmission, drivetrain
T02_Patel  → electrical, diagnostics
T03_Ahmed  → brakes, suspension
T04_Ramos  → ac, interior, general
```

Slot generation: 4 available slots, weekdays only, times: 08:00 / 10:00 / 13:00 / 15:00, offset by urgency (critical=+1 day, high=+2 days, normal=+3 days).

---

#### Telematics Service (`services/telematics.py`)

OBD-II DTC database (6 codes):

| Code | Description | Severity |
|---|---|---|
| P0300 | Random/Multiple Cylinder Misfire | HIGH |
| P0171 | System Too Lean (Bank 1) | MEDIUM |
| P0420 | Catalyst System Below Threshold | MEDIUM |
| C0035 | Left Front Wheel Speed Sensor Circuit | HIGH |
| B0001 | Driver Frontal Stage 1 Deployment Control | CRITICAL |
| P0562 | System Voltage Low | MEDIUM |

---

### 4.7 Data Layer

**Database:** MySQL 8.x via SQLAlchemy ORM + PyMySQL driver

**Connection:** `mysql+pymysql://cs03_user:admin@localhost:3306/automotive_cs03`

---

## 5. Data Flow Diagrams

### Copilot Query Flow

```
Agent types message in Copilot Panel
            │
            ▼
POST /api/agent/ask
{ message, session_id, vehicle_id?, image? }
            │
            ▼
     run_orchestrator()
            │
            ├──▶ classify_intent()  ──▶  Gemini API
            │         │
            │    returns ["vehicle", "warranty"]
            │
            ├──▶ VehicleAgent.process_query()
            │         └──▶ MySQL query → vehicle + fault codes
            │
            ├──▶ WarrantyAgent.process_query()
            │         └──▶ warranty_engine.check_warranty()
            │                   └──▶ MySQL warranty_records
            │
            └──▶ merge_responses()
                      │
                      ▼
            { response, data, sources }
                      │
                      ▼
           Rendered in Copilot Panel
```

### Warranty Check Flow

```
POST /api/warranty/check
{ vehicle_id, repair_type }
        │
        ▼
warranty_engine.check_warranty()
        │
        ├── Is repair_type in EXCLUSIONS? → { covered: false }
        │
        ├── Query Vehicle by vehicle_code
        │
        └── For each WarrantyRecord:
              ├── Get covered types from COVERAGE_MAP
              ├── Check repair_type in covered_types
              ├── Validate: start_date ≤ today ≤ end_date
              └── Validate: odometer ≤ mileage_limit
                       │
                       ▼
              { covered, coverage_type, expires, miles_remaining }
```

---

## 6. API Reference

### Base URL
```
http://localhost:8000
```

### Endpoints

#### Health
```
GET /
Response: { "status": "ok", "service": "Automotive CS03" }
```

#### Agent Copilot
```
POST /api/agent/ask
Body: {
  "message":    "Is my warranty still valid for engine repair?",
  "session_id": "sess_abc123",
  "vehicle_id": "VH001",        // optional
  "image":      "<base64>"      // optional, dashboard photo
}
Response: {
  "response": "Your powertrain warranty covers engine repairs...",
  "data":     { "covered": true, "expires": "2026-06-01" },
  "sources":  ["warranty.txt"]
}
```

#### Vehicles
```
GET  /api/vehicles/
GET  /api/vehicles/{vehicle_code}
Response: { id, vehicle_code, vin, make, model, year, odometer,
            fuel_level, battery_voltage, engine_temp, oil_life,
            customer, fault_codes }
```

#### Warranty
```
POST /api/warranty/check
Body:     { "vehicle_id": "VH001", "repair_type": "engine" }
Response: { "covered": true, "coverage_type": "powertrain",
            "expires": "2026-06-01", "miles_remaining": 12000,
            "deductible": 0 }
```

#### Scheduling
```
POST /api/scheduling/slots
Body:     { "service_type": "engine", "urgency": "high" }
Response: {
  "slots": [
    { "date": "2026-03-22", "time": "08:00",
      "technician": "T01_Kumar", "duration_hours": 2, "bay": 3 }
  ],
  "urgency": "high",
  "service_type": "engine"
}
```

#### Telematics
```
GET  /api/telematics/{vehicle_id}
Response: { fuel_level, battery_voltage, engine_temp, oil_life, fault_codes }

POST /api/telematics/decode
Body:     { "codes": ["P0300", "P0171"] }
Response: { "decoded": [
  { "code": "P0300", "description": "...", "severity": "HIGH" }
]}
```

#### Authentication
```
POST /api/user/signup
Body:     { "first_name", "last_name", "email", "password", "mobile" }

POST /api/user/login
Body:     { "email", "password" }
Response: { "token": "<jwt>", "user_id": 1 }
```

---

## 7. Database Schema

```
┌──────────────────────────────────────────────────────────────────┐
│                        customers                                 │
│  id · name · email · phone · created_at                         │
│  └──< vehicles (1:N)                                            │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                         vehicles                                 │
│  id · vehicle_code · vin · make · model · year · odometer       │
│  purchase_date · customer_id(FK)                                │
│  fuel_level · battery_voltage · engine_temp · oil_life          │
│  ├──< active_fault_codes (1:N)                                  │
│  ├──< warranty_records   (1:N)                                  │
│  └──< service_appointments (1:N)                                │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                     active_fault_codes                           │
│  id · vehicle_id(FK) · dtc_code · detected_at · resolved        │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                      warranty_records                            │
│  id · vehicle_id(FK) · coverage_type · start_date · end_date    │
│  mileage_limit · is_extended                                     │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                    service_appointments                          │
│  id · vehicle_id(FK) · service_type · scheduled_date            │
│  scheduled_time · technician · status · warranty_covered · notes│
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                       agent_sessions                             │
│  id · session_id · vehicle_id · history_json · updated_at       │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                          users                                   │
│  id · first_name · last_name · email · password · mobile        │
└──────────────────────────────────────────────────────────────────┘
```

---

## 8. Intent Classification & Routing

**Classifier:** `agent/classify_intent.py`
**LLM Used:** Google Gemini (`gemini-2.5-flash-lite`)
**Output:** JSON array of valid intents

**Classification Prompt Pattern:**
```
Identify ALL relevant intents: vehicle | warranty | scheduler | telemetry | general
Return ONLY JSON: {"intents": ["intent1", "intent2"]}
```

**Examples:**

| User Query | Classified Intents | Agents Invoked |
|---|---|---|
| "Is my warranty expired?" | `["warranty"]` | WarrantyAgent |
| "Book service and check warranty" | `["scheduler", "warranty"]` | SchedulerAgent + WarrantyAgent |
| "Car model and fault codes?" | `["vehicle", "telemetry"]` | VehicleAgent + TelemetryAgent |
| "What does P0300 mean?" | `["telemetry"]` | TelemetryAgent |
| "Tell me a joke" | `["general"]` | Gemini LLM direct |

**Response Merging:**
When multiple agents respond, `merge_responses()` concatenates text with ` | ` separator and deep-merges structured `data` fields. Last-write-wins for conflicting scalar keys; lists are concatenated.

---

## 9. Technology Stack

### Backend
| Component | Technology | Version |
|---|---|---|
| API Framework | FastAPI | Latest |
| Language | Python | 3.11+ |
| ORM | SQLAlchemy | 2.x |
| DB Driver | PyMySQL | Latest |
| Validation | Pydantic v2 | Latest |
| Logging | Loguru | Latest |
| Auth | python-jose (JWT) | Latest |

### AI / ML
| Component | Technology | Notes |
|---|---|---|
| Intent Classification | Google Gemini 2.5 Flash Lite | Fast, low-latency |
| General Q&A | Google Gemini 2.5 Flash Lite | Conversational fallback |
| RAG Synthesis | Anthropic Claude Sonnet | Structured response generation |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) | Local, no API cost |
| Vector Store | ChromaDB | Persistent local store |

### Database
| Component | Technology | Notes |
|---|---|---|
| Primary DB | MySQL 8.x | Vehicles, warranty, appointments |
| Vector DB | ChromaDB | Knowledge base embeddings |

### Frontend
| Component | Technology | Version |
|---|---|---|
| Framework | Angular | 21.2.3 |
| HTTP Client | Angular HttpClient + RxJS | Built-in |
| Auth | jwt-decode | Latest |
| Notifications | ngx-toastr | Latest |
| Build | Angular CLI | Latest |

---

## 10. Implementation Status

| Component | Status | Coverage |
|---|---|---|
| FastAPI application & routing | ✅ Complete | 100% |
| MySQL schema & ORM models | ✅ Complete | 100% |
| JWT Authentication (signup/login) | ⚠️ Partial | 60% — password stored plaintext |
| Intent classification | ✅ Complete | 100% |
| Multi-agent orchestrator | ✅ Complete | 100% |
| Vehicle Agent | ✅ Complete | 90% |
| Warranty Engine (service layer) | ✅ Complete | 85% |
| Warranty Agent (LLM integration) | ⚠️ Partial | 40% — not calling service layer |
| Scheduler Service | ✅ Complete | 80% |
| Scheduler Agent | ⚠️ Stub | 15% — returns placeholder only |
| Telemetry Service (DTC decode) | ✅ Complete | 70% |
| Telemetry Agent | ⚠️ Stub | 15% — returns placeholder only |
| RAG pipeline (ChromaDB) | ⚠️ Partial | 40% — broken import, minimal content |
| RAG Agent | ✅ Complete | 80% |
| Dashboard warning image analysis | ✅ Complete | 80% |
| Driver notifications | ✅ Complete | 80% |
| Angular frontend (shell + routing) | ✅ Complete | 100% |
| Copilot Chat UI | ✅ Complete | 80% |
| Vehicle detail UI | ✅ Complete | 80% |
| Scheduling UI | ⚠️ Partial | 40% — not connected to API |
| Image upload UI | ⚠️ Partial | 50% — UI exists, no backend processing |
| Resource booking persistence | ⚠️ Partial | 30% |

**Overall Completion: ~80%**

---

### P3 — Future Enhancements

| # | Feature | Description |
|---|---|---|
| 19 | Mobile driver app | Driver-facing view of repair schedule and vehicle status |
| 20 | Fleet dashboard | Multi-vehicle telematics overview for fleet operators |
| 21 | Recall alerts integration | Auto-match VIN against NHTSA recall database |
| 22 | Parts inventory integration | Check part availability before scheduling repairs |
| 23 | AI-generated customer replies | Draft customer-facing response emails from agent notes |

---

## 12. Setup & Running Locally

### Prerequisites
- Python 3.11+
- Node.js 20+
- MySQL 8.x running locally
- Git

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Create MySQL database
mysql -u root -p
CREATE DATABASE automotive_cs03;
CREATE USER 'cs03_user'@'localhost' IDENTIFIED BY 'admin';
GRANT ALL PRIVILEGES ON automotive_cs03.* TO 'cs03_user'@'localhost';
FLUSH PRIVILEGES;

# Configure credentials (do NOT commit to git)
cp .env.example .env
# Edit .env with your API keys

# Start the server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
ng serve                      # Runs at http://localhost:4200
```

### Environment Variables (`.env`)

```env
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIzaSy...
MYSQL_USER=cs03_user
MYSQL_PASSWORD=admin
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=automotive_cs03
SECRET_KEY=your-secure-jwt-secret
ENVIRONMENT=development
```

> **Security Note:** API keys are currently hardcoded in `config.py`. Before any deployment, move all secrets to environment variables and ensure `.env` is in `.gitignore`.

---

## Appendix: Agent Response Contract

All agents must return a `dict` conforming to this schema:

```python
{
    "response": str,          # Human-readable text answer
    "sources":  List[str],    # Knowledge sources used (e.g. ["warranty.txt"])
    # + any domain-specific keys:
    "vehicle_code": str,      # (VehicleAgent)
    "covered":      bool,     # (WarrantyAgent)
    "slots":        List,     # (SchedulerAgent)
    "fault_codes":  List,     # (TelemetryAgent)
}
```

The orchestrator's `merge_responses()` will union all keys from all agents, concatenate `response` strings with ` | `, and union all `sources` lists.

---

## WorkFlow steps

```
┌─────────────────────────────────────────────────────────┐
│  STEP 1 — Angular UI                                    │
│  User types in Copilot panel → ApiService.askAgent()    │
│  POST /api/agent/ask  { session_id, message,            │
│                         vehicle_id, image_base64? }     │
│                    + Bearer JWT header                  │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  STEP 2 — FastAPI Router                                │
│  Verify JWT → resolve user_id from cs03_auth            │
│  Forward validated payload to Orchestrator              │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  STEP 3 — Orchestrator                                  │
│  classify_intent(message) ──► Gemini 2.5 Flash          │
│  Returns: ["vehicle"], ["warranty","scheduler"], etc.   │
│  asyncio.gather → spawn matched agents in PARALLEL      │
└───────┬──────────────┬──────────────┬───────────────────┘
        │              │              │
        ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  STEP 4a     │ │  STEP 4b     │ │  STEP 4c     │
│  Vehicle     │ │  Warranty    │ │  Scheduler   │
│  Agent       │ │  Agent       │ │  Agent       │
│              │ │              │ │              │
│ cs03_vehicle │ │ cs03_warranty│ │cs03_scheduler│
│ cs03_        │ │ rules engine │ │ get slots    │
│  telematics  │ │ date+mileage │ │ book appt    │
│ decode DTC   │ │ check        │ │              │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       └────────────────┴────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  STEP 5 — Orchestrator + Gemini                         │
│  Collect all agent results via asyncio.gather           │
│  _merge_responses() → deduplicate + combine             │
│  Load session history from cs03_agent                   │
│  Gemini: compose final human-readable response          │
│  Save new turn → cs03_agent.agent_sessions              │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  STEP 6 — Angular UI                                    │
│  CopilotPanelComponent renders agent bubble             │
│  Tool trace chips show which agents fired               │
│  session_id persisted for next turn                     │
└─────────────────────────────────────────────────────────┘
```
