# ColdChain — Security Document

---

## 1. Security Philosophy

ColdChain follows a **defense in depth** approach. Even though v1 is a local single-user tool, it is built with production security patterns from day one — because:
1. The code will be reviewed by engineers in the interview
2. Good security habits are non-negotiable in professional engineering
3. The product may become multi-user in the future

**Core principle: API keys never leave the backend. Period.**

---

## 2. API Key Protection

### Rule: Zero Keys in Frontend
All API keys live exclusively in the backend `.env` file. The Next.js frontend never touches them.

```
✅ CORRECT:
  Browser → FastAPI (no key) → External API (key added by backend)

❌ WRONG:
  Browser → External API (key in JS bundle) ← never do this
```

### .env File Structure
```bash
# .env (never committed to git)
PROSPEO_API_KEY=pk_xxxxxxxxxxxx
BREVO_API_KEY=xkeysib-xxxxxxxxxxxx
SERPER_API_KEY=xxxxxxxxxxxx
GEMINI_API_KEY=AIzaxxxxxxxxxxxx

# Database (Turso)
TURSO_DATABASE_URL=https://your-db-name.turso.io
TURSO_AUTH_TOKEN=your_turso_auth_token

# Sender Details
SENDER_EMAIL=your_sender_email_here
SENDER_NAME=your_sender_name_here
```

### .env.example (committed to git)
```bash
# .env.example — copy this to .env and fill in your keys
PROSPEO_API_KEY=your_prospeo_key_here
BREVO_API_KEY=your_brevo_key_here
SERPER_API_KEY=your_serper_key_here
GEMINI_API_KEY=your_gemini_key_here
TURSO_DATABASE_URL=https://your-db-name.turso.io
TURSO_AUTH_TOKEN=your_turso_auth_token
SENDER_EMAIL=your_sender_email_here
SENDER_NAME=your_sender_name_here
```

### .gitignore (mandatory)
```
.env
.env.local
*.env
coldchain.db
__pycache__/
node_modules/
.next/
```

### Validation on Startup
```python
# FastAPI startup event
@app.on_event("startup")
async def validate_env():
    required_keys = [
        "PROSPEO_API_KEY", "BREVO_API_KEY",
        "SERPER_API_KEY", "GEMINI_API_KEY",
        "SENDER_EMAIL", "SENDER_NAME"
    ]
    missing = [k for k in required_keys if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Missing required env vars: {missing}")
```

---

## 3. CORS Configuration

Only localhost:3000 can call the FastAPI backend. No other origin accepted.

```python
from fastapi.middleware.cors import CORSMiddleware

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,       # ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["GET", "POST"],        # only what's needed
    allow_headers=["Content-Type"],
    max_age=3600,
)
```

---

## 4. Input Validation & Sanitization

### Domain Input Validation
Every seed domain is validated before the pipeline runs:

```python
import re
from pydantic import BaseModel, validator

DOMAIN_PATTERN = re.compile(
    r'^(?:[a-zA-Z0-9]'
    r'(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)'
    r'+[a-zA-Z]{2,}$'
)

class PipelineStartRequest(BaseModel):
    seed_domain: str

    @validator('seed_domain')
    def validate_domain(cls, v):
        # Strip protocol if present
        v = v.strip().lower()
        v = re.sub(r'^https?://', '', v)
        v = re.sub(r'^www\.', '', v)
        v = v.split('/')[0]  # remove path

        if not DOMAIN_PATTERN.match(v):
            raise ValueError('Invalid domain format')
        if len(v) > 253:
            raise ValueError('Domain too long')

        return v
```

### Email Validation
```python
from email_validator import validate_email, EmailNotValidError

def is_valid_email(email: str) -> bool:
    try:
        validate_email(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False
```

### SQL Injection Prevention
- SQLAlchemy ORM used exclusively — no raw SQL strings
- All values passed as parameters, never interpolated
- Example:
```python
# ✅ Safe — parameterized
result = await db.execute(
    select(Contact).where(Contact.run_id == run_id)
)

# ❌ Never do this
result = await db.execute(f"SELECT * FROM contacts WHERE run_id = '{run_id}'")
```

---

## 5. Rate Limiting

### Per-Service Rate Limiting
Each external API call goes through a rate limiter that respects the service's published limits:

```python
# rate_limiter.py
import asyncio
import time
from collections import defaultdict

class RateLimiter:
    def __init__(self, calls_per_second: float = 1.0):
        self.delay = 1.0 / calls_per_second
        self._last_call = defaultdict(float)
        self._locks = defaultdict(asyncio.Lock)

    async def acquire(self, service: str):
        async with self._locks[service]:
            elapsed = time.monotonic() - self._last_call[service]
            if elapsed < self.delay:
                await asyncio.sleep(self.delay - elapsed)
            self._last_call[service] = time.monotonic()

# Per-service limits
RATE_LIMITS = {
    "prospeo": RateLimiter(calls_per_second=0.5),   # 1 call per 2s
    "brevo":   RateLimiter(calls_per_second=2.0),   # 2 calls per second
    "gemini":  RateLimiter(calls_per_second=1.0),   # 1 call per second
    "serper":  RateLimiter(calls_per_second=2.0),
}
```

### Retry with Exponential Backoff
```python
import random

async def with_retry(func, max_retries=3, base_delay=1.0):
    for attempt in range(1, max_retries + 1):
        try:
            return await func()
        except RateLimitError:
            delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
            await asyncio.sleep(delay)
        except Exception as e:
            if attempt == max_retries:
                raise
    raise Exception("Max retries exceeded")
```

---

## 6. WebSocket Security

### Connection Validation
WebSocket connections require a valid `run_id`:

```python
@app.websocket("/ws/{run_id}")
async def websocket_pipeline(websocket: WebSocket, run_id: str):
    # Validate run_id is a real UUID
    try:
        uuid.UUID(run_id)
    except ValueError:
        await websocket.close(code=1008)  # Policy violation
        return

    # Verify run exists in DB
    run = await get_run(run_id)
    if not run:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    # ... stream logs
```

### No Sensitive Data in WebSocket Stream
Terminal output is scrubbed before sending — API keys are never logged:

```python
import re

SENSITIVE_PATTERNS = [
    re.compile(r'(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*\S+'),
    re.compile(r'xkeysib-[a-zA-Z0-9-]+'),
    re.compile(r'AIza[a-zA-Z0-9_-]{35}'),
]

def scrub_sensitive(message: str) -> str:
    for pattern in SENSITIVE_PATTERNS:
        message = pattern.sub('[REDACTED]', message)
    return message
```

---

## 7. Cloudflare Turnstile CAPTCHA

Add Turnstile to the pipeline input form to prevent automated abuse:

### Frontend (Next.js)
```tsx
import { Turnstile } from '@marsidev/react-turnstile'

// In the Input Screen component:
<Turnstile
  siteKey={process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY!}
  onSuccess={(token) => setTurnstileToken(token)}
  options={{ theme: 'dark' }}
/>
```

### Backend Verification
```python
async def verify_turnstile(token: str) -> bool:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={
                "secret": os.getenv("TURNSTILE_SECRET_KEY"),
                "response": token,
            }
        )
    return response.json().get("success", False)

# In pipeline start endpoint:
@app.post("/api/pipeline/start")
async def start_pipeline(
    request: PipelineStartRequest,
    turnstile_token: str = Header(alias="X-Turnstile-Token")
):
    if not await verify_turnstile(turnstile_token):
        raise HTTPException(status_code=403, detail="CAPTCHA verification failed")
    # ... proceed
```

### Additional env vars needed:
```bash
NEXT_PUBLIC_TURNSTILE_SITE_KEY=your_site_key   # public, safe in frontend
TURNSTILE_SECRET_KEY=your_secret_key            # private, backend only
```

**Note:** Turnstile is free with a Cloudflare account. Sign up at `dash.cloudflare.com` → Turnstile.

---

## 8. Secrets Never in Git

### Pre-commit hook (optional but recommended)
Add to `.git/hooks/pre-commit`:
```bash
#!/bin/bash
# Block commits containing potential API keys

if git diff --cached --name-only | xargs grep -l 'AIza\|xkeysib-\|pk_\|ak_' 2>/dev/null; then
    echo "❌ Potential API key detected in staged files. Commit blocked."
    exit 1
fi
```

---

## 9. Security Checklist

| Check | Status | How |
|-------|--------|-----|
| API keys in .env only | ✅ | Never in code or frontend |
| .env in .gitignore | ✅ | First line of .gitignore |
| CORS restricted to localhost | ✅ | FastAPI CORS middleware |
| All inputs validated | ✅ | Pydantic models |
| SQL injection impossible | ✅ | SQLAlchemy ORM only |
| No keys in WebSocket stream | ✅ | scrub_sensitive() on all logs |
| Rate limiting per service | ✅ | RateLimiter class |
| Retry with backoff | ✅ | with_retry() wrapper |
| WebSocket run_id validated | ✅ | UUID check + DB lookup |
| CAPTCHA on input form | ✅ | Cloudflare Turnstile |
| Sensitive patterns redacted | ✅ | Regex scrubber on all logs |

---

## 10. What Hackers Can't Do

| Attack | Protection |
|--------|-----------|
| Steal API keys from JS bundle | Keys never in frontend |
| CSRF attacks | CORS + Turnstile |
| SQL injection via domain input | Pydantic validation + ORM |
| Flood the pipeline endpoint | Turnstile CAPTCHA + rate limiting |
| Read other users' run data | Single-user local tool (no auth needed) |
| Intercept API keys in logs | scrub_sensitive() on all output |
| Brute-force run IDs | UUID v4 (122 bits of entropy) |