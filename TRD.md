# ColdChain — Technical Requirements Document (TRD)

---

## 1. Stack Decision

ColdChain is built as a full-stack web application with a Python CLI that shares the same backend logic. The stack is chosen for:
- Speed of development (2-day build)
- Maximum visual impact (cinematic frontend)
- Real-time pipeline streaming (WebSockets)
- AI integration depth (Gemini)

---

## 2. System Overview

```
┌─────────────────────────────────────────────────────────┐
│                    USER INTERFACE                        │
│         Next.js 16 + Three.js + GSAP + Framer           │
│              runs on localhost:3000                      │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP REST + WebSoc│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ Prospeo  │ │ Serper   │ │  Brevo   │ │  Gemini  │   │
│  │ Service  │ │ Service  │ │ Service  │ │  Service │   │
│  │ └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                   SQLite DATABASE                        │
│             pipeline_runs, contacts, logs               │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Frontend Stack

### Core Framework
- **Next.js 16** (App Router) — React framework
- **TypeScript** — type safety throughout
- **Tailwind CSS** — utility-first styling

### Animation & 3D (Cinematic Layer)
- **Three.js** — 3D particle background, floating nodes
- **GSAP** — timeline animations, stage transitions, scroll triggers
- **Framer Motion** — component enter/exit animations, layout transitions
- **Lenis** — smooth scroll
- **Spline** (optional) — 3D scene embeds if time allows

### Terminal Component
- **xterm.js** — real browser terminal that streams WebSocket output
- Renders actual CLI stdout in the browser
- Looks and feels like a real terminal, dark themed

### UI Components
- **shadcn/ui** — base component library
- Custom components built on top for the pipeline visualization
- No generic AI-looking UI — everything custom styled

### Real-time
- **Native WebSocket** — streams pipeline stdout from FastAPI to xterm.js
- No polling — true real-time character-by-character output

### State Management
- **Zustand** — lightweight global state for pipeline run status
- React Query — API data fetching and caching

---

## 4. Backend Stack

### Framework
- **FastAPI** (Python 3.11+) — async REST API + WebSocket server
- **Uvicorn** — ASGI server

### Architecture Pattern: Microservices
Each pipeline stage is an independent service module:

```
backend/
├── main.py                  # FastAPI app entry point
├── api/
│   ├── pipeline.py          # /api/pipeline/* orchestrator routes
│   ├── websocket.py         # WebSocket endpoint for terminal streaming
│   └── history.py           # /api/history/* run history routes
├── services/
│   ├── discovery_service.py # Stage 1: Serper + Gemini company search
│   ├── prospeo_service.py   # Stage 2: Prospeo people search & verification
│   ├── brevo_service.py     # Stage 3: Brevo email sending
│   ├── gemini_service.py    # AI: scoring + personalization
│   └── serper_service.py    # AI: company web research
├── models/
│   ├── schemas.py           # Pydantic request/response models
│   └── database.py          # SQLAlchemy models
├── utils/
│   ├── rate_limiter.py      # Exponential backoff + retry
│   ├── deduplicator.py      # Email/contact deduplication
│   └── logger.py            # Structured logging
└── cli/
    └── main.py              # CLI entry point (shares services/)
```

### Service Contracts
Each service exposes a single async function:

```python
# discovery_service.py
async def find_lookalike_companies(seed_domain: str, run_id: str) -> List[dict]: ...

# prospeo_service.py
async def find_decision_makers(domain: str, run_id: str) -> List[dict]: ...

# gemini_service.py
async def score_lead(contact: dict, run_id: str) -> tuple: ...  # (score, reason)
async def personalize_email(contact: dict, research: str, sender_name: str, run_id: str) -> tuple: ...

# brevo_service.py
async def send_outreach(contacts: List[dict], run_id: str) -> List[dict]: ...
```

---

## 5. Database

### Engine: Turso (cloud-hosted libSQL / SQLite-compatible)
- Zero local setup — cloud hosted, always available
- SQLite-compatible — same SQL syntax, same schema
- Shared between CLI and web app automatically (both point to same Turso URL)
- Python SDK: `libsql-client`
- Connection: `libsql://your-db.turso.io` + auth token

### Why Turso over local SQLite
- Data persists across machine restarts
- CLI and web UI read/write the same database
- No `coldchain.db` file to manage or accidentally delete
- Free tier: 500 databases, 9GB storage — more than enough

### Connection (Python)
```python
import libsql_client

client = libsql_client.create_client(
    url=os.getenv("TURSO_DATABASE_URL"),       # libsql://your-db.turso.io
    auth_token=os.getenv("TURSO_AUTH_TOKEN"),
)
```

### Schema (see Backend Schema doc for full detail)
```
pipeline_runs    — each full run record
companies        — discovered lookalike companies
contacts         — resolved contacts with emails
email_logs       — sent email records
run_logs         — terminal output lines per run
```

---

## 6. Auth & Security

- **No user auth in v1** — single user local tool
- **API keys** — stored in `.env` only, never in code, never in frontend
- **Backend proxy pattern** — all external API calls go through FastAPI, never from browser directly
- **CORS** — restricted to localhost:3000 only
- **Rate limiting** — per-service rate limiting with exponential backoff
- **Input validation** — Pydantic models validate all inputs
- **No secrets in git** — `.env` in `.gitignore`, `.env.example` committed

---

## 7. AI & APIs

### Gemini (Google AI)
- Model: `gemini-3.5-flash` (fast + free)
- Usage: lead scoring, email personalization, company research synthesis
- Integration: `google-generativeai` Python SDK

### Serper
- Usage: Google search results for company research
- Called before Gemini email generation
- Fetches: company description, recent news, product info

### Serper API
- Stage 1: Search competitor domains
- Stage 3: Search company context for lead scoring
- Auth: `X-API-KEY` header

### Prospeo
- Stage 2: `POST /search-person` to find contacts and `POST /enrich-person` to retrieve verified emails
- Auth: `X-KEY` header

### Brevo
- Stage 3: `POST /v3/smtp/email` — send transactional email
- Auth: `api-key` header

---

## 8. Deployment (Local Only — v1)

```bash
# Terminal 1: Backend
cd backend && uvicorn main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev

# Terminal 3: CLI (optional)
python cli/main.py razorpay.com
```

Single command startup via `Makefile`:
```bash
make dev   # starts both frontend and backend
make cli   # runs CLI mode
```

---

## 9. Architecture Flow

```
User types: razorpay.com
      │
      ▼
POST /api/pipeline/start {seed_domain: "razorpay.com"}
      │
      ▼
WebSocket /ws/pipeline/{run_id} ──────────────────────►  xterm.js in browser
      │                                                   (streams all logs)
      ▼
[Stage 1] discovery_service.find_lookalike_companies() (Serper + Gemini)
      │ → yields: [clevertap.com, moengage.com, webengage.com ...]
      ▼
[Stage 2] prospeo_service.find_decision_makers() (Search + Enrich)
      │ → yields: [{name, title, linkedin, email, email_verified}, ...]
      ▼
[Stage 3] gemini_service.score_lead() (using Serper context)
      │ → yields: [{...contact, email, score}, ...]
      ▼
GET /api/pipeline/{run_id}/contacts
      │ → Frontend renders review screen
      ▼
User confirms → POST /api/pipeline/{run_id}/send
      │
      ▼
[Stage 4] gemini_service.personalize_email() per contact
          + brevo_service.send_outreach()
      │ → yields: [{success, message_id}, ...]
      ▼
Pipeline complete → results stored in SQLite
```

---

## 10. Engineering Rules

### Scalability
- All service functions are `async` — non-blocking I/O throughout
- Pipeline stages run concurrently where possible (Stage 2 companies processed in parallel)
- Rate limiter prevents thundering herd on external APIs

### Modularity
- Each service is completely independent — swap providers by editing one file
- CLI and web UI share identical service layer — zero code duplication
- Pydantic schemas enforce contracts between services

### Observability
- Structured logging with timestamps per stage
- Every API call logged: endpoint, status, response time
- WebSocket streams all logs to frontend in real time
- SQLite stores full run history for debugging

### Security by Default
- Zero API keys in frontend code — ever
- All external calls proxied through FastAPI
- Pydantic validates and sanitizes all inputs
- `.env` never committed

### Resilience
- Exponential backoff with jitter on all external API calls
- Missing contacts skipped gracefully — pipeline continues
- Per-stage error isolation — Stage 3 failure doesn't kill Stage 4
- Partial results saved to SQLite even on partial failure

### Developer Experience
- Single `make dev` command starts everything
- Hot reload on both frontend and backend
- `.env.example` with all required keys documented
- Clear README with setup in under 5 minutes