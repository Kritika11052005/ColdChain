<div align="center">

```
 ██████╗ ██████╗ ██╗     ██████╗  ██████╗██╗  ██╗ █████╗ ██╗███╗   ██╗
██╔════╝██╔═══██╗██║     ██╔══██╗██╔════╝██║  ██║██╔══██╗██║████╗  ██║
██║     ██║   ██║██║     ██║  ██║██║     ███████║███████║██║██╔██╗ ██║
██║     ██║   ██║██║     ██║  ██║██║     ██╔══██║██╔══██║██║██║╚██╗██║
╚██████╗╚██████╔╝███████╗██████╔╝╚██████╗██║  ██║██║  ██║██║██║ ╚████║
 ╚═════╝ ╚═════╝ ╚══════╝╚═════╝  ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝
```

**One domain. Zero humans. Emails sent.**

[![Next.js](https://img.shields.io/badge/Next.js-16.2-black?style=for-the-badge&logo=next.js)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-4.0-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![Gemini AI](https://img.shields.io/badge/Gemini-AI-8E44AD?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev)
[![License](https://img.shields.io/badge/License-MIT-6366F1?style=for-the-badge)](LICENSE)

<br/>

> *Built as a take-home assignment for Vocallabs/Subspace SDE Intern *

</div>

---

## ⚡ What is ColdChain?

ColdChain is a **fully automated B2B cold outreach engine**. You type one company domain. The system discovers lookalike competitors, finds their C-suite and VP-level decision makers, verifies their emails, scores every lead with AI, writes a hyper-personalized email per contact — and sends them all. Automatically.

No copy-paste. No manual research. No spreadsheets. Zero humans in the loop.

```
You type:  razorpay.com
               │
               ▼
    ┌─────────────────────┐
    │  🔍 Stage 1         │  Serper + Gemini discovers 7 real competitors
    │  Company Discovery  │  cashfree.com · payu.in · billdesk.com ...
    └──────────┬──────────┘
               │
               ▼
    ┌─────────────────────┐
    │  🧑‍💼 Stage 2         │  Prospeo finds C-suite & VP decision makers
    │  People Discovery   │  Name · Title · LinkedIn · Verified Email
    └──────────┬──────────┘
               │
               ▼
    ┌─────────────────────┐
    │  🤖 Stage 3         │  Gemini scores each lead 0–100
    │  AI Lead Scoring    │  Only contacts ≥ 65 proceed
    └──────────┬──────────┘
               │
               ▼
    ┌─────────────────────┐
    │  ✉️  Stage 4         │  Gemini writes · Brevo sends
    │  AI Outreach        │  Personalized per contact, per company
    └─────────────────────┘

    Result: Real emails in real inboxes. ~2 minutes total.
```

---

## 🎬 Demo

> *Pipeline executing live — one domain in, emails out.*

```
[09:41:22] ColdChain Pipeline initiated for seed domain: clevertap.com
[09:41:23] [STAGE-1] Querying Serper for competitors of CleverTap...
[09:41:26] [STAGE-1] Gemini extraction: moengage.com · braze.com · webengage.com
[09:41:26] [STAGE-1] ✓ Serper + Gemini discovered 7 competitor companies.
[09:41:27] [STAGE-2] Querying Prospeo for decision makers at moengage.com...
[09:41:31] [STAGE-2] ✓ Got verified email for Rajkumar S (VP Product): r.s@moengage.com
[09:41:33] [STAGE-2] ✓ Got verified email for Yash Reddy (CEO): yash@webengage.com
[09:41:39] [STAGE-3] AI Lead Scored: Rajkumar S → 87/100 (VP, strategic industry fit)
[09:41:41] [STAGE-3] AI Lead Scored: Yash Reddy → 94/100 (CEO, direct competitor)
[09:41:43] [STAGE-4] Gemini personalizing email for Rajkumar S...
[09:41:46] [STAGE-4] ✓ Email dispatched via Brevo → r.s@moengage.com
[09:41:51] Pipeline COMPLETE. Sent: 9 · Failed: 0 · Duration: 1m 52s
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND  (Next.js 16 + React 19)            │
│   Landing → Input → Pipeline View → Review → Results           │
│   Three.js particles · GSAP animations · xterm.js terminal     │
│   Cloudflare Turnstile CAPTCHA · WebSocket live streaming       │
└──────────────────────────┬──────────────────────────────────────┘
                           │  REST + WebSocket
┌──────────────────────────▼──────────────────────────────────────┐
│                    BACKEND  (FastAPI + Python 3.11)             │
│                                                                  │
│  ┌─────────────────┐  ┌──────────────┐  ┌────────────────────┐ │
│  │ discovery_service│  │prospeo_service│  │  gemini_service    │ │
│  │ Serper + Gemini  │  │ Search+Enrich │  │ Score + Personalize│ │
│  └─────────────────┘  └──────────────┘  └────────────────────┘ │
│  ┌─────────────────┐  ┌──────────────┐  ┌────────────────────┐ │
│  │  brevo_service  │  │ serper_service│  │  rate_limiter      │ │
│  │  Email Sending  │  │ Web Research  │  │  Backoff + Retry   │ │
│  └─────────────────┘  └──────────────┘  └────────────────────┘ │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    DATABASE  (Turso / libSQL)                    │
│   pipeline_runs · companies · contacts · email_logs · run_logs  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

### Frontend
| Technology | Version | Purpose |
|---|---|---|
| **Next.js** | 16.2.7 | App framework, App Router |
| **React** | 19.2.4 | UI library |
| **TypeScript** | 5.x | Type safety |
| **Tailwind CSS** | 4.x | Utility styling |
| **Three.js** | latest | 3D particle background |
| **GSAP** | latest | Timeline animations |
| **Framer Motion** | latest | Component transitions |
| **xterm.js** | latest | Real terminal in browser |
| **Cloudflare Turnstile** | 1.5.2 | CAPTCHA protection |
| **Lucide React** | 1.17.0 | Icon system |

### Backend
| Technology | Version | Purpose |
|---|---|---|
| **FastAPI** | 0.115+ | Async REST API + WebSocket |
| **Python** | 3.11+ | Runtime |
| **httpx** | latest | Async HTTP client |
| **Pydantic** | v2 | Request/response validation |
| **Uvicorn** | latest | ASGI server |

### APIs & AI
| Service | Purpose | Free Tier |
|---|---|---|
| **Gemini 2.0 Flash** | Competitor extraction, lead scoring, email writing | 1M tokens/min |
| **Prospeo** | Decision maker search + email enrichment | 50/day |
| **Serper** | Google search for company research | 2,500/month |
| **Brevo** | Transactional email sending | 300 emails/day |

### Infrastructure
| Technology | Purpose |
|---|---|
| **Turso** | Cloud-hosted libSQL database |
| **Cloudflare Turnstile** | Bot protection on pipeline trigger |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- API keys (see `.env.example`)

### 1. Clone the repository
```bash
git clone https://github.com/Kritika11052005/coldchain.git
cd coldchain
```

### 2. Backend setup
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Fill in your API keys in .env
uvicorn main:app --reload --port 8000
```

### 3. Frontend setup
```bash
cd frontend
npm install
cp .env.example .env.local
# Add NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

### 4. Open in browser
```
http://localhost:3000
```

Or use the Makefile shortcut:
```bash
make dev    # starts both frontend and backend
make cli    # run CLI mode directly
```

---

## ⚙️ Environment Variables

```bash
# ── AI & Search ──────────────────────────────────
GEMINI_API_KEY=          # Google AI Studio — free at aistudio.google.com
SERPER_API_KEY=          # serper.dev — 2500 free searches

# ── People & Email Discovery ─────────────────────
PROSPEO_API_KEY=         # app.prospeo.io — 50 free enrich/day

# ── Email Sending ────────────────────────────────
BREVO_API_KEY=           # app.brevo.com — 300 free emails/day
SENDER_EMAIL=            # verified sender email in Brevo
SENDER_NAME=             # display name for outreach emails

# ── Database ─────────────────────────────────────
TURSO_DATABASE_URL=      # libsql://your-db.turso.io
TURSO_AUTH_TOKEN=        # from Turso dashboard

# ── Security ─────────────────────────────────────
TURNSTILE_SECRET_KEY=    # Cloudflare Turnstile secret
NEXT_PUBLIC_TURNSTILE_SITE_KEY=   # Cloudflare Turnstile site key
```

---

## 📁 Project Structure

```
coldchain/
├── backend/
│   ├── api/
│   │   ├── pipeline.py        # Orchestrator — runs all 4 stages
│   │   ├── websocket.py       # WebSocket endpoint for terminal stream
│   │   └── history.py         # Pipeline run history
│   ├── services/
│   │   ├── discovery_service.py   # Stage 1: Serper + Gemini competitor AI
│   │   ├── prospeo_service.py     # Stage 2: Decision maker search + enrich
│   │   ├── gemini_service.py      # Stage 3: Lead scoring + email writing
│   │   ├── brevo_service.py       # Stage 4: Email dispatch
│   │   └── serper_service.py      # Company web research for personalization
│   ├── models/
│   │   ├── schemas.py         # Pydantic request/response models
│   │   └── database.py        # Turso DB connection + schema init
│   ├── utils/
│   │   ├── rate_limiter.py    # Exponential backoff + per-service limits
│   │   ├── deduplicator.py    # Email deduplication across companies
│   │   └── logger.py          # Structured logging to DB + WebSocket
│   ├── cli/
│   │   └── main.py            # CLI entry point (same logic, terminal UI)
│   ├── main.py                # FastAPI app entrypoint
│   └── requirements.txt
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx           # Landing page (Three.js particles)
│   │   ├── input/page.tsx     # Domain input screen
│   │   ├── pipeline/page.tsx  # Live pipeline + xterm.js terminal
│   │   ├── review/page.tsx    # Safety checkpoint — contact cards
│   │   └── results/page.tsx   # Success screen
│   ├── components/            # Reusable UI components
│   └── public/
│
├── Makefile                   # make dev / make cli
├── PRD.md                     # Product Requirements Document
├── TRD.md                     # Technical Requirements Document
├── APP_FLOW.md                # Full user journey + edge cases
├── UI_UX.md                   # Design system + component specs
├── BACKEND_SCHEMA.md          # Database schema + data flow
└── SECURITY.md                # Security architecture
```

---

## 🔒 Security

- **Zero API keys in frontend** — all external calls proxied through FastAPI
- **Cloudflare Turnstile CAPTCHA** on pipeline trigger endpoint
- **CORS** restricted to localhost:3000 / your deployed frontend only
- **Input validation** via Pydantic on all endpoints
- **WebSocket output scrubbed** — API keys never appear in terminal stream
- **Rate limiting** per service with exponential backoff + jitter
- **`.env` never committed** — `.env.example` documents all required keys

---

## 🧠 AI Features

### Dynamic Competitor Discovery
Instead of a hardcoded list, Stage 1 runs **3 Serper searches** and feeds all results to **Gemini** which extracts real competitor domains. Works for any company in any industry.

### Lead Scoring (0–100)
Every contact is scored by Gemini before the review screen. Factors: seniority level, company size fit, industry match. Only contacts scoring ≥ 65 are shown.

### Hyper-Personalized Emails
Before writing each email, Gemini reads a **Serper-researched company summary** — recent news, product focus, growth signals. Every email feels genuinely hand-written, not templated.

---

## 📋 CLI Mode

ColdChain works as a standalone CLI tool — same pipeline logic, terminal interface:

```bash
cd backend
python cli/main.py clevertap.com

# Output:
# [Stage 1] Executing Dynamic AI-Powered Company Discovery...
# [Stage 1] AI discovered competitor: moengage.com (MoEngage)
# [Stage 2] Sourcing decision makers for MoEngage...
# [Stage 2] ✓ Got verified email for ...
# ...
# ⚠️  SAFETY CHECKPOINT — Review before sending
# ┌─────────────────────────────────────────────────┐
# │  9 contacts ready · 0 skipped · 2m 14s elapsed  │
# └─────────────────────────────────────────────────┘
# Send outreach emails to the above contacts? [y/N]:
```

---

## 📊 Pipeline Stats

| Metric | Typical Value |
|---|---|
| Time per pipeline run | ~2 minutes |
| Companies discovered | 6–8 |
| Contacts found | 15–30 |
| Email resolve rate | 40–70% |
| Contacts passing score filter | 60–80% |
| End-to-end (input → emails sent) | < 3 minutes |

---

## 🤝 Built For

This project was built as the take-home engineering assignment for **SDE Intern at Vocallabs/Subspace** — an automated cold-outreach pipeline from scratch in under 48 hours.

**What was asked:** Build a CLI that goes from one domain to emails sent.

**What was developed* A full-stack product with a cinematic web UI, AI competitor discovery, lead scoring, personalized email generation, live terminal streaming, and CAPTCHA protection.

---

## 👩‍💻 Author

**Kritika Benjwal** — AI/ML Engineer · Full Stack Developer · Researcher

[![GitHub](https://img.shields.io/badge/GitHub-Kritika11052005-181717?style=for-the-badge&logo=github)](https://github.com/Kritika11052005)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-kritika--benjwal-0A66C2?style=for-the-badge&logo=linkedin)](https://linkedin.com/in/kritika-benjwal)

---

<div align="center">

*Built with obsession, developed in 48 hours.*

**⭐ Star this repo if ColdChain impressed you**

</div>
