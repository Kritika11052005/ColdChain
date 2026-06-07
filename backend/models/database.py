import os
import libsql_client
from dotenv import load_dotenv

# Load env vars
load_dotenv()

TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")

# Ensure URL uses https instead of libsql to prevent websocket issues on Windows
if TURSO_DATABASE_URL and TURSO_DATABASE_URL.startswith("libsql://"):
    TURSO_DATABASE_URL = TURSO_DATABASE_URL.replace("libsql://", "https://")

def get_client():
    if not TURSO_DATABASE_URL:
        raise RuntimeError("TURSO_DATABASE_URL environment variable is not set")
    return libsql_client.create_client(
        url=TURSO_DATABASE_URL,
        auth_token=TURSO_AUTH_TOKEN
    )

# SQL statements for schema initialization
CREATE_PIPELINE_RUNS_SQL = """
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id              TEXT PRIMARY KEY,
    seed_domain     TEXT NOT NULL,
    status          TEXT NOT NULL,
    started_at      DATETIME NOT NULL,
    completed_at    DATETIME,
    duration_seconds REAL,
    companies_found INTEGER DEFAULT 0,
    prospects_found INTEGER DEFAULT 0,
    contacts_verified INTEGER DEFAULT 0,
    contacts_scored INTEGER DEFAULT 0,
    emails_sent     INTEGER DEFAULT 0,
    emails_failed   INTEGER DEFAULT 0,
    error_message   TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_COMPANIES_SQL = """
CREATE TABLE IF NOT EXISTS companies (
    id              TEXT PRIMARY KEY,
    run_id          TEXT NOT NULL,
    domain          TEXT NOT NULL,
    name            TEXT,
    industry        TEXT,
    employee_count  INTEGER,
    country         TEXT,
    description     TEXT,
    source          TEXT DEFAULT 'serper_gemini',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES pipeline_runs(id) ON DELETE CASCADE
);
"""

CREATE_CONTACTS_SQL = """
CREATE TABLE IF NOT EXISTS contacts (
    id              TEXT PRIMARY KEY,
    run_id          TEXT NOT NULL,
    company_id      TEXT NOT NULL,
    company_domain  TEXT NOT NULL,
    company_name    TEXT,
    first_name      TEXT,
    last_name       TEXT,
    full_name       TEXT,
    title           TEXT,
    seniority       TEXT,
    linkedin_url    TEXT,
    email           TEXT,
    email_verified  BOOLEAN DEFAULT 0,
    email_source    TEXT,
    lead_score      INTEGER,
    score_reason    TEXT,
    included        BOOLEAN DEFAULT 1,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);
"""

CREATE_EMAIL_LOGS_SQL = """
CREATE TABLE IF NOT EXISTS email_logs (
    id              TEXT PRIMARY KEY,
    run_id          TEXT NOT NULL,
    contact_id      TEXT NOT NULL,
    recipient_email TEXT NOT NULL,
    recipient_name  TEXT,
    subject         TEXT NOT NULL,
    body_html       TEXT NOT NULL,
    body_text       TEXT NOT NULL,
    status          TEXT NOT NULL,
    brevo_message_id TEXT,
    error_message   TEXT,
    sent_at         DATETIME,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE
);
"""

CREATE_RUN_LOGS_SQL = """
CREATE TABLE IF NOT EXISTS run_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL,
    level           TEXT NOT NULL,
    stage           INTEGER,
    message         TEXT NOT NULL,
    timestamp       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES pipeline_runs(id) ON DELETE CASCADE
);
"""

# Indexes
INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_runs_status ON pipeline_runs(status);",
    "CREATE INDEX IF NOT EXISTS idx_runs_started ON pipeline_runs(started_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_companies_run ON companies(run_id);",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_companies_run_domain ON companies(run_id, domain);",
    "CREATE INDEX IF NOT EXISTS idx_contacts_run ON contacts(run_id);",
    "CREATE INDEX IF NOT EXISTS idx_contacts_company ON contacts(company_id);",
    "CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email);",
    "CREATE INDEX IF NOT EXISTS idx_contacts_score ON contacts(lead_score DESC);",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_contacts_run_email ON contacts(run_id, email) WHERE email IS NOT NULL;",
    "CREATE INDEX IF NOT EXISTS idx_email_logs_run ON email_logs(run_id);",
    "CREATE INDEX IF NOT EXISTS idx_email_logs_contact ON email_logs(contact_id);",
    "CREATE INDEX IF NOT EXISTS idx_email_logs_status ON email_logs(status);",
    "CREATE INDEX IF NOT EXISTS idx_run_logs_run ON run_logs(run_id);",
    "CREATE INDEX IF NOT EXISTS idx_run_logs_run_time ON run_logs(run_id, timestamp ASC);"
]

async def init_db():
    print("Initializing Turso database...")
    async with get_client() as client:
        # Run table creations
        await client.execute(CREATE_PIPELINE_RUNS_SQL)
        await client.execute(CREATE_COMPANIES_SQL)
        await client.execute(CREATE_CONTACTS_SQL)
        await client.execute(CREATE_EMAIL_LOGS_SQL)
        await client.execute(CREATE_RUN_LOGS_SQL)
        
        # Run index creations
        for idx_sql in INDEXES_SQL:
            await client.execute(idx_sql)
            
    print("Database initialization complete.")

async def execute_query(sql: str, params: list = []):
    async with get_client() as client:
        result = await client.execute(sql, params)
        return result.rows
