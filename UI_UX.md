# ColdChain — UI/UX Design Document

---

## 1. Overall Feel & Vision

**ColdChain should feel like mission control.**

Not a SaaS dashboard. Not another AI tool. A living, breathing system that gives the user the feeling that a machine is working *for* them — intelligently, automatically, relentlessly.

Think: the aesthetic of a Bloomberg terminal crossed with a sci-fi HUD, built with the craft of a Vercel or Linear. Dark. Precise. Alive.

When someone watches the demo they should think: *"I've never seen a student build something that looks like this."*

---

## 2. Mood & Aesthetic

**Keywords:** Cinematic · Command-driven · Intelligent · Precise · Dark luxury

**References:**
- Linear.app (precision, dark, fast)
- Vercel dashboard (clean, monospace, real-time logs)
- Raycast (command palette feel)
- Resend.com (developer-first dark design)
- Framer.com hero animations
- NASA mission control (multiple data streams, authoritative)

**NOT:**
- Generic AI blue gradients
- Rounded pastel cards
- ChatGPT-style chat bubbles
- Bootstrap or Material UI components
- Anything that looks like it was scaffolded in 5 minutes

---

## 3. Color Palette

```
Background (primary):     #050508   — near black, deep space
Background (secondary):   #0D0D14   — card backgrounds
Background (elevated):    #12121C   — modals, overlays

Border (subtle):          #1E1E2E   — card borders
Border (active):          #2D2D4E   — focused states

Text (primary):           #F0F0FF   — near white, slight blue tint
Text (secondary):         #8888AA   — muted labels
Text (tertiary):          #444466   — placeholders, disabled

Accent (primary):         #6366F1   — electric indigo — CTAs, highlights
Accent (glow):            #818CF8   — glow states, hover
Accent (secondary):       #06B6D4   — cyan — terminal text, data
Accent (success):         #10B981   — emerald — completed stages
Accent (warning):         #F59E0B   — amber — warnings, rate limits
Accent (error):           #EF4444   — red — errors, failures
Accent (score-high):      #10B981   — green — score ≥ 80
Accent (score-mid):       #F59E0B   — amber — score 65-79

Terminal background:      #0A0A0F   — deepest black
Terminal text:            #00FF88   — classic green terminal
Terminal timestamp:       #444466   — dim grey
Terminal success:         #10B981   — green
Terminal warning:         #F59E0B   — amber  
Terminal error:           #EF4444   — red
```

---

## 4. Typography

```
Display / Hero:     "Cal Sans" or "Syne" — bold, geometric, modern
                    Weight: 800
                    Size: 64-96px (hero), 40px (screen titles)

UI / Labels:        "Inter" — clean, readable, professional
                    Weight: 400/500/600
                    Size: 14px (body), 12px (labels), 11px (micro)

Monospace:          "JetBrains Mono" or "Geist Mono"
                    Used for: terminal, domain input, code, API data
                    Size: 13px (terminal), 16px (main input)

Numbers / Stats:    "Syne" or tabular variant of Inter
                    Tabular figures enabled for counting animations
```

---

## 5. UI Components

### Input Field (Screen 2)
```
- Full width, centered
- Height: 72px
- Border: 1px solid #1E1E2E
- Border-radius: 12px
- Background: #0D0D14
- Font: JetBrains Mono, 18px
- Focus: border color → #6366F1, outer glow: 0 0 0 3px rgba(99,102,241,0.15)
- Placeholder: "razorpay.com" in #444466
- Left icon: terminal prompt `>_` in #6366F1
- Right: domain validation indicator (✓ green / ✗ red)
```

### Pipeline Stage Node
```
States:
  WAITING:  12px circle, #1E1E2E fill, #444466 border, dashed
  RUNNING:  12px circle, indigo fill, spinning ring animation
  COMPLETE: 12px circle, #10B981 fill, checkmark icon
  ERROR:    12px circle, #EF4444 fill, × icon

Connecting line between nodes:
  WAITING:  dashed, #1E1E2E
  COMPLETE: solid, gradient from #6366F1 to #10B981, animated fill
```

### Contact Card
```
- Width: ~280px
- Background: #0D0D14
- Border: 1px solid #1E1E2E
- Border-radius: 16px
- Padding: 20px
- Hover: border → #2D2D4E, subtle lift (translateY -2px)

Score badge:
  ≥ 80: #10B981 background, "87" white text
  65-79: #F59E0B background
  < 65: filtered out, never shown

Remove button: top-right ×, appears on hover only
```

### Terminal Component (xterm.js)
```
- Background: #0A0A0F
- Border: 1px solid #1E1E2E
- Border-radius: 12px
- Padding: 16px
- Font: JetBrains Mono 13px
- Line height: 1.6
- Custom scrollbar: thin, #1E1E2E track, #444466 thumb
- Header bar: "● ● ●" traffic lights (decorative) + "coldchain — pipeline"
```

### CTA Buttons
```
Primary:
  Background: #6366F1
  Text: white, 500 weight
  Border-radius: 10px
  Padding: 12px 24px
  Hover: background → #818CF8, scale(1.02)
  Active: scale(0.98)
  Glow on hover: 0 0 20px rgba(99,102,241,0.4)

Destructive:
  Background: transparent
  Border: 1px solid #EF4444
  Text: #EF4444
  Hover: background → rgba(239,68,68,0.1)

Ghost:
  Background: transparent
  Text: #8888AA
  Hover: text → #F0F0FF
```

---

## 6. Screen-by-Screen Design

### Screen 1 — Landing

**Background:** Three.js scene
- 200+ small particles on canvas
- Particles connected by lines when within distance threshold
- Slow drift animation
- Mouse parallax — particles subtly follow cursor
- Color: deep indigo to cyan gradient particles

**Hero content (centered, z-index above canvas):**
```
[Small tag: "Automated Outreach · AI-Powered"]

COLDCHAIN
[Animated text: "From domain to inbox. Automatically."]

[Subtext: "One domain in. Zero humans in the loop. Emails sent."]

[CTA: "Start Pipeline →"]
```

**Animation sequence on load:**
1. Particles fade in (0-800ms)
2. Logo slams in with GSAP elastic ease (800ms)
3. Tagline types in character by character (1000-1400ms)
4. Subtext fades up (1400-1800ms)
5. CTA button slides up with glow (1800-2200ms)

---

### Screen 2 — Input

**Layout:** Centered vertically and horizontally

**Animation in:** GSAP page transition — particles compress → screen 2 fades in

**Above input:**
```
[Small breadcrumb: "Step 1 of 4"]
[Title: "Enter your seed domain"]
[Subtitle: "A company similar to your ideal customer"]
```

**Input field:** Large, monospace, centered

**Below input:**
```
[Label: "Try an example:"]
[Chips: stripe.com · razorpay.com · zepto.com · groww.in]
```

**Run button** appears only after valid domain entered (GSAP slide-up)

---

### Screen 3 — Pipeline Execution

**Full screen split layout:**

Left panel (40%):
- ColdChain wordmark top-left
- 4 stage nodes connected by vertical line
- Each node: icon + stage name + status badge + result count
- Stage icons: 🔍 🧑‍💼 ✉️ 🤖

Right panel (60%):
- Terminal header: traffic light dots + "coldchain — live pipeline"
- xterm.js terminal filling the rest
- Auto-scroll enabled
- Semi-transparent backdrop blur border between panels

Bottom bar (full width):
- "Seed: razorpay.com" left
- Elapsed timer counting up center
- "Cancel" button right (ghost style)

---

### Screen 4 — Review

**Header:**
```
Pipeline Complete — Review Before Sending
8 companies · 23 prospects · 11 verified contacts
```

**Lead score filter toggle:**
```
[Show all] [Score ≥ 65 only ✓]
```

**Card grid:** Responsive, 3 columns on large screen, 2 on medium

**Email preview:** Expands inline below card (Framer Motion accordion)

**Footer sticky bar:**
```
[← Back to pipeline]     [11 contacts selected]     [Send Emails →]
```

---

### Screen 5 — Results

**Center of screen:**
- Three.js celebration: particles spiral inward → form checkmark → explode outward
- Stats appear after animation:
  ```
  ✓ 11 sent  ✗ 0 failed  ⚡ 2m 14s
  ```
- Condensed sent list below
- Two buttons: "Run Another" (primary) + "View History" (ghost)

---

## 7. Animation Principles

**Timing:**
- Fast UI responses: 150-200ms
- Page transitions: 400-600ms
- Stage completion celebrations: 800ms
- Load animations: staggered, 100ms between elements

**Easing:**
- Entrances: `cubic-bezier(0.16, 1, 0.3, 1)` — expo out (fast snap)
- Exits: `cubic-bezier(0.7, 0, 1, 1)` — fast exit
- Elastic: for logo and big moments only

**Rules:**
- Never animate more than 3 things simultaneously
- Every animation has a purpose — no decorative spin
- Mobile: reduce animation complexity, respect prefers-reduced-motion
- Terminal: never animate text, it types itself via WebSocket

---

## 8. Design Principles

**Simplicity:** One action per screen. Never two competing CTAs.

**Consistency:** Same border radius (12px), same spacing unit (4px base), same font everywhere.

**Usability:** User always knows what stage they're in. Progress is always visible.

**Accessibility:**
- Contrast ratio ≥ 4.5:1 for all text
- Focus rings on all interactive elements
- Keyboard navigable (Tab through all actions)
- prefers-reduced-motion respected — fallback to fade

**Performance:**
- Three.js canvas never blocks main thread
- Framer Motion uses GPU-accelerated transforms only
- xterm.js virtual DOM — handles thousands of lines without lag
- Images: none (pure code UI)

---

## 9. Responsive Behavior

**Desktop (1280px+):** Full split-screen layout as designed

**Tablet (768-1279px):**
- Pipeline screen: terminal takes full width, stage diagram collapses to top bar
- Review screen: 2 column card grid

**Mobile (< 768px):**
- Not primary target (this is a B2B tool used on desktop)
- Functional but simplified — single column, no Three.js background (performance)
- Terminal still works but smaller

---

## 10. What Makes This UI Unique

1. **Real terminal in the browser** — not a fake log list, actual xterm.js streaming real output
2. **Pipeline as a living diagram** — nodes light up as stages complete, feels like watching a circuit activate
3. **Lead scores as a concept** — no other cold outreach tool shows you why a contact was chosen
4. **Email preview before send** — transparency that competitors don't offer
5. **No navigation bar** — fully immersive, each screen owns the full viewport
6. **Particles that react to mouse** — the background is alive, not static
7. **Monospace input** — domain input feels like typing into a terminal, not a form