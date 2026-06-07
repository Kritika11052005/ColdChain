# ColdChain — Product Requirements Document (PRD)

---

## 1. App Overview

**ColdChain** is a fully automated B2B cold outreach platform. A user inputs a single seed company domain and the system — without any further human input — discovers lookalike companies, finds their C-suite and VP-level decision makers, verifies their work emails, scores each lead with AI, writes hyper-personalized outreach emails per contact, and sends them automatically via Brevo.

The product is delivered as:
- A **cinematic web application** (primary interface) where users watch the pipeline execute live with real terminal output streamed to the browser
- A **CLI tool** (`python main.py razorpay.com`) that runs the same backend pipeline for power users and interview demos

---

## 2. Problem

Cold outreach is broken. Sales teams waste hours:
- Manually finding similar companies
- Hunting for decision maker emails
- Writing generic copy-paste emails that nobody opens
- Managing follow-ups across spreadsheets

Existing tools (Lemlist, Instantly) solve pieces of this but require significant manual effort to chain together. There is no single tool that goes from "one domain" to "emails sent" with zero human involvement.

---

## 3. Target Users

**Primary:** B2B sales teams, SDRs, founders doing outbound sales at early-stage startups

**Secondary:** Freelancers and consultants doing business development

**Tertiary:** Recruiters sourcing candidates (future use case)

**User profile:**
- Non-technical — will not run CLIs
- Time-poor — wants results in minutes not hours
- Skeptical — has seen too many spray-and-pray tools fail

---

## 4. Core Features

### F1 — Pipeline Orchestration
- Accept one seed domain as input
- Run all 4 stages automatically, output of each feeds next
- Safety checkpoint before emails fire (review screen)
- Full pipeline runs in under 3 minutes for 10 companies

### F2 — Company Discovery (Stage 1)
- Use Serper API + Gemini to find competitor companies dynamically
- Analyze seed domain to find lookalike company domains
- Deduplicate and clean results

### F3 — Decision Maker Discovery (Stage 2)
- For each company domain, find C-suite and VP-level contacts
- Pull name, title, LinkedIn URL, company
- Filter by seniority: CEO, CTO, CMO, VP, Head of, Director, Founder, Co-Founder
- Use Prospeo Search API and Prospeo Enrich API exclusively

### F4 — Email Verification (Stage 3)
- Skip contacts without verified emails returned directly by Prospeo
- No pattern-guessing or sandbox email generation
- Skip unverifiable contacts gracefully — never send to invalid emails

### F5 — AI Lead Scoring
- Score each contact 0–100 using Gemini AI
- Factors: seniority level, company size fit, industry match, email confidence
- Only email contacts scoring ≥ 65
- Show score visually in the review screen

### F6 — AI Email Personalization
- For each contact, Gemini:
  1. Searches company website via Serper API
  2. Reads company context (product, industry, recent news)
  3. Generates a unique subject line and email body
  4. Personalizes to contact's name, title, and company
- Emails feel hand-written, not templated

### F7 — Review & Safety Checkpoint
- Before any email fires, show full summary:
  - List of contacts with name, title, company, email, score
  - Email preview per contact (expandable)
  - Total count
- User must explicitly confirm before send
- Option to remove individual contacts before sending

### F8 — Outreach Sending (Stage 4)
- Send via Brevo transactional email API
- From: verified sender email
- Personalized subject + body per contact
- Track: sent, failed, skipped
- Show real-time sending progress

### F9 — Live Terminal Visualization
- Web UI embeds a real terminal component
- CLI output streams live via WebSocket to browser
- Each stage lights up in the pipeline diagram as it completes
- Errors shown inline — pipeline continues where possible

### F10 — Pipeline History
- Store each run: seed domain, companies found, contacts found, emails sent
- Accessible from dashboard
- SQLite local storage (no cloud database needed for v1)

---

## 5. Goals

**Assignment goal:** Impress Vocallabs with engineering depth, product thinking, and a working end-to-end demo

**Product goal:** A user types one domain and receives sent outreach emails in under 3 minutes with zero manual steps

**Demo goal:** A recruiter watching the 5-minute video should immediately understand what the product does and want to use it

---

## 6. User Stories

```
As a sales manager,
I want to type one competitor's domain
So that I can automatically reach their lookalike company's decision makers

As a founder doing outbound,
I want AI to write personalized emails per contact
So that my outreach doesn't feel like spam

As a user reviewing contacts before send,
I want to see each contact's lead score and email preview
So that I can make an informed decision before emails fire

As a power user,
I want to run the pipeline from the terminal
So that I can automate it in scripts or cron jobs

As a user watching the pipeline run,
I want to see live progress in a terminal on the web UI
So that I know exactly what's happening at each stage
```

---

## 7. Success Metrics

| Metric | Target |
|--------|--------|
| Pipeline completion rate | > 90% of runs reach Stage 4 |
| Email resolve rate | > 60% of prospects get verified email |
| Lead score filter | Only contacts ≥ 65 score get emailed |
| End-to-end time | < 3 minutes for 10 companies |
| Demo wow factor | Interviewer asks follow-up questions about the product |

---

## 8. Feature Map

```
ColdChain
│
├── Input Layer
│   ├── Web UI input screen
│   └── CLI argument parser
│
├── Pipeline Engine
│   ├── Stage 1: Serper + Gemini company search
│   ├── Stage 2: Prospeo people search & email verification
│   └── Stage 3: Brevo email sending
│
├── AI Layer (Gemini)
│   ├── Lead scoring (0-100)
│   ├── Company context enrichment (Serper)
│   └── Email personalization
│
├── Safety Layer
│   ├── Review screen (web)
│   ├── CLI confirmation prompt
│   └── Email deduplication
│
├── Visualization Layer
│   ├── Pipeline stage diagram
│   ├── Live terminal stream (WebSocket)
│   └── Contact cards with scores
│
└── Storage Layer
    ├── SQLite pipeline runs
    ├── Contact cache
    └── Email logs
```

---

## 9. Out of Scope (v1)

- User authentication / multi-user
- Email follow-up sequences
- CRM integrations
- Cloud deployment
- Mobile app
- Billing / subscriptions