# ColdChain — App Flow Document

---

## 1. Flow Diagram

```
┌─────────────────┐
│   LANDING PAGE   │  User arrives, sees cinematic hero
│   (Screen 1)     │  with particle background
└────────┬────────┘
         │ user clicks "Start Pipeline"
         ▼
┌─────────────────┐
│   INPUT SCREEN   │  User types seed domain
│   (Screen 2)     │  e.g. razorpay.com
└────────┬────────┘
         │ user hits Enter or clicks Run
         ▼
┌─────────────────┐
│  PIPELINE VIEW   │  Live execution screen
│   (Screen 3)     │  4 stages + terminal stream
└────────┬────────┘
         │ all 4 stages complete
         ▼
┌─────────────────┐
│  REVIEW SCREEN   │  Safety checkpoint
│   (Screen 4)     │  Contact cards + email previews
└────────┬────────┘
         │ user clicks "Send Emails"
         ▼
┌─────────────────┐
│  RESULTS SCREEN  │  Sent confirmation
│   (Screen 5)     │  Stats + success animation
└────────┬────────┘
         │ user clicks "Run Another"
         ▼
     Back to Screen 2
```

---

## 2. Core Pages / Screens

---

### Screen 1 — Landing Page

**Purpose:** First impression. Sets the tone. Makes the user want to use it.

**Elements:**
- Full screen Three.js particle field background (dark, electric blue/purple nodes floating and connecting)
- ColdChain logo + tagline: *"One domain. Zero effort. Emails sent."*
- Animated text cycling through: "Find companies → Find people → Verify emails → Send outreach"
- Single CTA button: **"Start Pipeline"** (glowing, pulsing)
- Subtle scroll indicator

**User Actions:**
- Click "Start Pipeline" → navigates to Screen 2 with GSAP page transition
- Scroll down → optional about section (low priority)

**Animations:**
- Particles float and connect on load (Three.js)
- Tagline fades in with GSAP stagger
- CTA button has continuous pulse glow animation
- Page transition: particles collapse into center → Screen 2 slides in

---

### Screen 2 — Input Screen

**Purpose:** Take the one input. Make it feel powerful.

**Elements:**
- Large centered input field: placeholder `"Enter seed domain — e.g. razorpay.com"`
- Domain validation (must be valid domain format)
- Example chips below input: `stripe.com` `zepto.com` `razorpay.com` (clickable)
- Run button: **"Run ColdChain →"**
- Small text: "We'll find lookalike companies, their decision-makers, and send personalized emails. Automatically."

**User Actions:**
- Type domain → real-time format validation
- Click example chip → autofills input
- Click Run / press Enter → validation passes → POST /api/pipeline/start → navigate to Screen 3

**Edge Cases:**
- Invalid domain format → inline error: "Enter a valid domain like company.com"
- Empty input → button disabled, shake animation on submit attempt
- Domain with http:// prefix → auto-strip to bare domain

**Animations:**
- Input field expands slightly on focus (GSAP)
- Run button slides in from bottom on valid input
- Loading spinner on submit while API acknowledges

---

### Screen 3 — Pipeline Execution View

**Purpose:** The core experience. User watches the machine work.

**Layout (split screen):**
```
┌─────────────────────┬──────────────────────────┐
│   PIPELINE DIAGRAM  │    TERMINAL STREAM        │
│   (left 40%)        │    (right 60%)            │
│                     │                           │
│  ○ Stage 1          │  > Starting ColdChain...  │
│  Company Search     │  > Seed: razorpay.com     │
│  [RUNNING...]       │  > [Stage 1] Finding      │
│       ↓             │    lookalike companies...  │
│  ○ Stage 2          │  > Found: clevertap.com   │
│  People Search      │  > Found: moengage.com    │
│  [WAITING]          │  > [Stage 1] ✓ 8 companies│
│       ↓             │  > [Stage 2] Finding      │
│  ○ Stage 3          │    decision makers...      │
│  Email Verify       │                           │
│  [WAITING]          │                           │
│       ↓             │                           │
│  ○ Stage 4          │                           │
│  AI + Send          │                           │
│  [WAITING]          │                           │
└─────────────────────┴──────────────────────────┘
```

**Stage States:**
- `WAITING` — grey, pulsing dot
- `RUNNING` — blue, spinning ring + stage name animates
- `COMPLETE` — green checkmark, count shown (e.g. "8 companies found")
- `ERROR` — red, error message inline, pipeline continues

**Terminal:**
- xterm.js component, dark background, green/white text
- Streams real FastAPI stdout via WebSocket
- Auto-scrolls to bottom
- Shows timestamps per line
- Color coded: blue=info, green=success, yellow=warning, red=error

**User Actions:**
- Watch only — no input needed during execution
- Can scroll terminal output
- "Cancel" button (top right) — stops pipeline gracefully

**Edge Cases:**
- API rate limit hit → terminal shows: `[WARN] Rate limited, retrying in 2s...` → continues automatically
- Stage returns 0 results → terminal shows warning, skips to next stage
- Network error → retry shown in terminal, after 3 fails → error state shown, partial results preserved
- WebSocket disconnect → reconnects automatically, resumes streaming

**Animations:**
- Stage nodes light up sequentially with GSAP timeline
- Connecting lines between stages fill with color as stages complete
- Numbers count up when stage completes (e.g. "0 → 8 companies")
- Completion: all nodes green → brief celebration animation → auto-navigate to Screen 4

---

### Screen 4 — Review Screen (Safety Checkpoint)

**Purpose:** User reviews before emails fire. Required by assignment spec.

**Layout:**
```
┌─────────────────────────────────────────────────────┐
│  PIPELINE SUMMARY                                    │
│  8 companies → 23 prospects → 14 verified contacts  │
│  AI filtered to: 11 contacts (score ≥ 65)           │
├─────────────────────────────────────────────────────┤
│  CONTACT CARDS (scrollable grid)                    │
│                                                     │
│  ┌──────────────────┐  ┌──────────────────┐        │
│  │ Rohan Mehta      │  │ Priya Sharma      │        │
│  │ VP Sales         │  │ CEO               │        │
│  │ CleverTap        │  │ MoEngage          │        │
│  │ rohan@clever...  │  │ priya@moengage... │        │
│  │ Score: 87/100    │  │ Score: 92/100     │        │
│  │ [Preview Email]  │  │ [Preview Email]   │        │
│  │ [Remove] ✕       │  │ [Remove] ✕        │        │
│  └──────────────────┘  └──────────────────┘        │
│                                                     │
├─────────────────────────────────────────────────────┤
│  [← Back]        [Send 11 Emails →]                │
└─────────────────────────────────────────────────────┘
```

**Contact Card:**
- Name, title, company, email (partially masked: `rohan@cl*****p.com`)
- Lead score badge (color coded: green ≥80, yellow 65-79)
- "Preview Email" → expands inline showing AI-generated subject + body
- "Remove" → removes contact from send list, card fades out

**Email Preview Modal:**
```
Subject: Quick thought on CleverTap's Q4 push strategy

Hi Rohan,

Noticed CleverTap just launched your new retention 
analytics suite — impressive timing given how saturated 
the market is getting...
[full AI-generated body]

Best,
[Sender Name]
```

**User Actions:**
- Scroll through contact cards
- Preview any email
- Remove individual contacts
- Click "Send X Emails" → confirmation dialog → POST /api/pipeline/{id}/send → Screen 5

**Confirmation Dialog:**
```
"You're about to send 11 personalized emails.
 This cannot be undone. Continue?"
[Cancel]  [Yes, Send]
```

**Edge Cases:**
- All contacts removed → "Send" button disabled, message: "Add at least one contact"
- 0 contacts from pipeline → skip to error state with message
- User removes contacts → count in button updates in real time

---

### Screen 5 — Results Screen

**Purpose:** Confirm success. Make the user feel good about what just happened.

**Elements:**
- Large success animation (particles converge into checkmark — Three.js/GSAP)
- Stats:
  ```
  ✓ 11 emails sent
  ✗ 0 failed
  ⏱ Pipeline completed in 2m 14s
  ```
- List of sent contacts (condensed)
- Two CTAs:
  - **"Run Another Domain →"** → back to Screen 2
  - **"View History"** → future feature placeholder

**Edge Cases:**
- Partial send (some sent, some failed) → show split stats, list failures with reason
- All failed → error state, suggest checking Brevo API key
- Single email sent → still shows success

---

## 3. Navigation Rules

- No traditional nav bar — full screen immersive experience
- Progress is linear: 1 → 2 → 3 → 4 → 5
- Back navigation allowed from Screen 4 only (to review pipeline results)
- Screen 3 (pipeline running) — no back, only cancel
- Screen 5 → "Run Another" resets state and goes to Screen 2

---

## 4. Primary Actions Per Screen

| Screen | Primary Action | Secondary Action |
|--------|---------------|------------------|
| Landing | Start Pipeline | Scroll to learn more |
| Input | Run ColdChain | Select example domain |
| Pipeline | Watch / Cancel | Scroll terminal |
| Review | Send Emails | Remove contacts / Preview |
| Results | Run Another | View History |

---

## 5. User States

```
IDLE          → Screen 1 or 2, no pipeline running
RUNNING       → Screen 3, pipeline executing
REVIEWING     → Screen 4, checkpoint before send
SENDING       → Screen 4→5 transition, emails firing
COMPLETE      → Screen 5, pipeline done
ERROR         → Inline on Screen 3/4/5, recoverable
```

---

## 6. Edge Cases (Global)

| Scenario | Handling |
|----------|----------|
| API key invalid | Error message on Screen 3 terminal: "Prospeo API key invalid — check .env" |
| All credits exhausted | Stage fails gracefully, shows in terminal, uses fallback service |
| No lookalike companies found | Screen 3 error: "No similar companies found for this domain. Try a larger company." |
| No contacts found | Screen 3 error: "No decision-makers found. Pipeline stopped." |
| All emails unverifiable | Review screen shows 0 contacts, prevents send |
| Network goes down mid-pipeline | Auto-retry 3x with backoff, then graceful error |
| User closes tab during pipeline | Run continues on backend, resumable on return (future feature) |
| Duplicate emails across companies | Deduplication layer removes before review screen |

---

## 7. Flow Notes

- The terminal is always visible during Screen 3 — this is the proof that the CLI is running
- Lead scores are computed during Stage 3 (async, doesn't slow pipeline)
- Email personalization (Gemini) runs after user confirms on Screen 4, not before — saves API credits
- The pipeline never auto-sends — the human confirmation on Screen 4 is non-negotiable
- All stage outputs are cached in SQLite — refreshing Screen 4 doesn't re-run the pipeline