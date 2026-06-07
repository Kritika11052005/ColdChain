# ColdChain — Backend Schema Document

---

## 1. Overview

ColdChain uses **Turso** (cloud-hosted libSQL / SQLite-compatible) for persistence.
Connection via `libsql-client` Python SDK.

**Why Turso over local SQLite:**
- Zero local file management
- CLI and web app share the same database automatically
- Data persists across machine restarts
- Free tier is more than sufficient (500 DBs, 9GB storage)

### Required env vars:
```bash
TURSO_DATABASE_URL=libsql://your-db-name.turso.io
TURSO_AUTH_TOKEN=your_turso_auth_token
```

### Python connection setup:
```python
# database.py
import libsql_client
import os

def get_client():
    return libsql_client.create_client(
        url=os.getenv("TURSO_DATABASE_URL"),
        auth_token=os.getenv("TURSO_AUTH_TOKEN"),
    )

# Usage in any service:
async def execute_query(sql: str, params: list = []):
    async with get_client() as client:
        result = await client.execute(sql, params)
        return result.rows
```

### Database initialization (run once on startup):
```python
# FastAPI startup event
@app.on_event("startup")
async def init_db():
    async with get_client() as client:
        await client.batch([
            CREATE_PIPELINE_RUNS_SQL,
            CREATE_COMPANIES_SQL,
            CREATE_CONTACTS_SQL,
            CREATE_EMAIL_LOGS_SQL,
            CREATE_RUN_LOGS_SQL,
        ])
```

---

## 2. Entity Relationship Diagram

```
pipeline_runs
     │
     ├──── companies (many per run)
     │         │
     │         └──── contacts (many per company)
     │                   │
     │                   └──── email_logs (one per contact per run)
     │
     └──── run_logs (all terminal output lines)
```

---

## 3. Tables

---

### Table: `pipeline_runs`

Stores each full pipeline execution.

```sql
CREATE TABLE pipeline_runs (
    id              TEXT PRIMARY KEY,          -- UUID: "run_550e8400-e29b..."
    seed_domain     TEXT NOT NULL,             -- "razorpay.com"
    status          TEXT NOT NULL,             -- RUNNING | COMPLETE | ERROR | CANCELLED
    started_at      DATETIME NOT NULL,         -- UTC timestamp
    completed_at    DATETIME,                  -- NULL until done
    duration_seconds REAL,                     -- 134.5
    companies_found INTEGER DEFAULT 0,
    prospects_found INTEGER DEFAULT 0,
    contacts_verified INTEGER DEFAULT 0,
    contacts_scored INTEGER DEFAULT 0,         -- contacts that passed score filter
    emails_sent     INTEGER DEFAULT 0,
    emails_failed   INTEGER DEFAULT 0,
    error_message   TEXT,                      -- NULL if no error
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes:**
```sql
CREATE INDEX idx_runs_status ON pipeline_runs(status);
CREATE INDEX idx_runs_started ON pipeline_runs(started_at DESC);
```

---

### Table: `companies`

Lookalike companies discovered in Stage 1.

```sql
CREATE TABLE companies (
    id              TEXT PRIMARY KEY,          -- UUID
    run_id          TEXT NOT NULL,             -- FK → pipeline_runs.id
    domain          TEXT NOT NULL,             -- "clevertap.com"
    name            TEXT,                      -- "CleverTap"
    industry        TEXT,                      -- "Marketing Technology"
    employee_count  INTEGER,                   -- 500
    country         TEXT,                      -- "India"
    description     TEXT,                      -- short company description
    source          TEXT DEFAULT 'serper_gemini',     -- which API found this
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES pipeline_runs(id) ON DELETE CASCADE
);
```

**Indexes:**
```sql
CREATE INDEX idx_companies_run ON companies(run_id);
CREATE UNIQUE INDEX idx_companies_run_domain ON companies(run_id, domain);
```

---

### Table: `contacts`

Decision-makers found in Stage 2 + emails resolved in Stage 3.

```sql
CREATE TABLE contacts (
    id              TEXT PRIMARY KEY,          -- UUID
    run_id          TEXT NOT NULL,             -- FK → pipeline_runs.id
    company_id      TEXT NOT NULL,             -- FK → companies.id
    company_domain  TEXT NOT NULL,             -- denormalized for quick access
    company_name    TEXT,
    first_name      TEXT,                      -- "Rohan"
    last_name       TEXT,                      -- "Mehta"
    full_name       TEXT,                      -- "Rohan Mehta"
    title           TEXT,                      -- "VP of Sales"
    seniority       TEXT,                      -- C_SUITE | VP | DIRECTOR | MANAGER
    linkedin_url    TEXT,
    email           TEXT,                      -- "rohan@clevertap.com"
    email_verified  BOOLEAN DEFAULT FALSE,
    email_source    TEXT,                      -- 'prospeo'
    lead_score      INTEGER,                   -- 0-100, NULL until scored
    score_reason    TEXT,                      -- brief AI explanation of score
    included        BOOLEAN DEFAULT TRUE,      -- FALSE if user removed on review screen
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);
```

**Indexes:**
```sql
CREATE INDEX idx_contacts_run ON contacts(run_id);
CREATE INDEX idx_contacts_company ON contacts(company_id);
CREATE INDEX idx_contacts_email ON contacts(email);
CREATE INDEX idx_contacts_score ON contacts(lead_score DESC);
-- Prevent duplicate emails within a run
CREATE UNIQUE INDEX idx_contacts_run_email ON contacts(run_id, email)
    WHERE email IS NOT NULL;
```

---

### Table: `email_logs`

Records of each email send attempt in Stage 4.

```sql
CREATE TABLE email_logs (
    id              TEXT PRIMARY KEY,          -- UUID
    run_id          TEXT NOT NULL,             -- FK → pipeline_runs.id
    contact_id      TEXT NOT NULL,             -- FK → contacts.id
    recipient_email TEXT NOT NULL,
    recipient_name  TEXT,
    subject         TEXT NOT NULL,             -- AI-generated subject
    body_html       TEXT NOT NULL,             -- AI-generated body (HTML)
    body_text       TEXT NOT NULL,             -- plain text version
    status          TEXT NOT NULL,             -- SENT | FAILED | SKIPPED
    brevo_message_id TEXT,                     -- Brevo's message ID for tracking
    error_message   TEXT,                      -- NULL if sent successfully
    sent_at         DATETIME,                  -- NULL until sent
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE
);
```

**Indexes:**
```sql
CREATE INDEX idx_email_logs_run ON email_logs(run_id);
CREATE INDEX idx_email_logs_contact ON email_logs(contact_id);
CREATE INDEX idx_email_logs_status ON email_logs(status);
```

---

### Table: `run_logs`

Every terminal output line for a run (powers the WebSocket stream + history replay).

```sql
CREATE TABLE run_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL,             -- FK → pipeline_runs.id
    level           TEXT NOT NULL,             -- INFO | SUCCESS | WARNING | ERROR | DEBUG
    stage           INTEGER,                   -- 1/2/3/4/NULL for orchestrator messages
    message         TEXT NOT NULL,             -- "[Stage 1] Found clevertap.com"
    timestamp       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES pipeline_runs(id) ON DELETE CASCADE
);
```

**Indexes:**
```sql
CREATE INDEX idx_run_logs_run ON run_logs(run_id);
CREATE INDEX idx_run_logs_run_time ON run_logs(run_id, timestamp ASC);
```

---

## 4. Pydantic Schemas (API Layer)

These are the request/response shapes for the FastAPI endpoints:

```python
# schemas.py

class PipelineStartRequest(BaseModel):
    seed_domain: str                    # "razorpay.com"

class PipelineStartResponse(BaseModel):
    run_id: str                         # UUID
    status: str                         # "RUNNING"
    websocket_url: str                  # "ws://localhost:8000/ws/run_id"

class CompanySchema(BaseModel):
    id: str
    domain: str
    name: Optional[str]
    industry: Optional[str]
    employee_count: Optional[int]
    country: Optional[str]

class ContactSchema(BaseModel):
    id: str
    full_name: str
    title: Optional[str]
    company_name: Optional[str]
    company_domain: str
    email: str
    email_verified: bool
    lead_score: Optional[int]
    score_reason: Optional[str]
    included: bool

class EmailPreviewSchema(BaseModel):
    contact_id: str
    subject: str
    body_text: str
    body_html: str

class PipelineStatusResponse(BaseModel):
    run_id: str
    status: str
    seed_domain: str
    companies_found: int
    contacts_verified: int
    contacts_scored: int
    duration_seconds: Optional[float]

class ReviewContactsResponse(BaseModel):
    run_id: str
    total_contacts: int
    contacts: List[ContactSchema]

class SendRequest(BaseModel):
    run_id: str
    contact_ids: List[str]              # which contacts to send to

class SendResponse(BaseModel):
    sent: int
    failed: int
    results: List[EmailResult]

class EmailResult(BaseModel):
    contact_id: str
    email: str
    success: bool
    message_id: Optional[str]
    error: Optional[str]
```

---

## 5. Data Flow Through Schema

```
Stage 1 output:
  List[Company] → saved to companies table

Stage 2 output:
  List[Prospect] → saved to contacts table (email=NULL, score=NULL)

Stage 3 output:
  Updates contacts.email, contacts.email_verified, contacts.email_source
  Updates contacts.lead_score, contacts.score_reason

User confirmation:
  Updates contacts.included = FALSE for removed contacts

Stage 4 output:
  Creates email_logs rows per contact
  Updates pipeline_runs.emails_sent, emails_failed
  Updates pipeline_runs.status = 'COMPLETE'
  Updates pipeline_runs.completed_at, duration_seconds
```

---

## 6. Key Design Decisions

**Why Turso?**
- SQLite-compatible — same SQL, same schema, zero learning curve
- Cloud hosted — CLI and web app share one database automatically
- Free tier covers everything needed for this project
- No local file to manage or accidentally delete
- Can scale to millions of rows if this becomes a real product

**Why UUIDs for IDs?**
- Safe to expose in URLs and WebSocket channels
- No sequential guessing of run IDs
- Consistent across all tables

**Why denormalize `company_domain` in contacts?**
- Avoids JOIN in the most common query (get all contacts for a run)
- The domain is immutable once set

**Why store `body_html` and `body_text` separately?**
- Brevo requires both for proper email delivery
- Plain text is the fallback for email clients that don't render HTML
- Audit trail — know exactly what was sent

**Why `included` boolean instead of deleting removed contacts?**
- Preserves the full pipeline result for history/debugging
- User can see they had 23 contacts, chose to send to 11
- Allows future "re-include" feature