# Submission form — Vireo Audio (Set B)

> Draft answers for the web form. Two fields need YOUR input before you submit:
> **honest_hours** (your real number) and the **video link** inside *ai_usage*.
> Read everything before pasting — this goes in under your name.

---

### 1. What did you build, and what business outcome does it move? (number + money)

A small Python tool (`python run.py`, runs offline) that cleans Vireo's support
exports and produces a fair per-agent CSAT/handle-time scorecard plus a
root-cause view of replacement spend, output as one `dashboard.html`.

The outcome it moves: it finds that the CSAT slide is a **Pulse 2 earbud batch
defect**, not an agent problem. Pulse 2 replacements are **₹19.6 lakh since
Dec 2025** (62% of all replacement spend; 85% of the Jan–Mar bill), and
**66% are the identical fault — left earbud won't charge** — concentrated in
lots PL2-2510/2511/2512. Quarantining those lots is worth roughly **₹8–13 lakh a
quarter**, versus a ₹4 lakh training budget currently aimed at agents who are
mostly just absorbing the warranty fallout.

### 2. What does one run cost, and what would a month cost at Vireo's volume?

**One run: ₹0.** The shipped pipeline is deterministic and offline — no model
calls. Monthly cost at ~650 tickets/week: **still ₹0.**

Optional LLM classifier (Claude Haiku 4.5, $1/1M input, $5/1M output):
- Per ticket ≈ 320 input + 6 output tokens → (320×$1 + 6×$5)/1e6 = **$0.00035 ≈ ₹0.029**.
- All 11,750 tickets once: **≈ $4.11 ≈ ₹345**.
- Monthly at 650/week (~2,800 tickets): **≈ $0.98 ≈ ₹82/month** (halve with the Batch API).

For context, Finance feared "₹5/ticket × 12k ≈ ₹60,000". Even the paid path is
~₹345, and the default is ₹0.

### 3. How do you know it works?

- **Classifier:** scored against a **60-ticket hand-labelled gold set**
  (`tests/gold_labels.csv`, labelled by reading each ticket). **88% overall
  accuracy; 100% recall and precision on `left_bud_charging`**, the label the
  headline depends on. It runs on every pipeline execution.
- **Data quality:** 6 automated invariants run each time (no negative handle
  times after the timezone fix; CSAT never zero-filled; 100% agent-join;
  response rate 44% ≈ policy's 45%; replacements all unit-priced). All pass.
- **Where it's wrong:** the ~12% of errors are *non-defect* tickets (delivery,
  billing) leaking into a defect bucket because an agent note contains a word
  like "transit". That inflates the small non-left buckets slightly; it does not
  touch the Pulse 2 / left-bud headline. `other`-class recall is 0.71.

### 4. Did you change, narrow, or push back on the client's ask?

Yes, three times (detail in `docs/decisions.md`):
- **Pushed back on "flag the bottom ten".** Delivered it, but the actionable
  ranking excludes Tier-2, because policy §6 and Neha's email both say the
  warranty team can't be compared to Tier-1 — and all six sit at the bottom
  purely because of the queue they're given.
- **Narrowed "dashboard first, causes later"** by putting the cause on the front
  page: it's a ₹20 lakh batch defect sitting in the same table.
- **Corrected the money:** replacement cost is ₹1,802, not Arjun's ₹2,500 — but
  his volume concern is real.

### 5. What is wrong with what you are handing us?

- Lot-level numbers cover only **~65% of tickets** (customers don't always quote
  an order_id), so lots are "where to look first," not an exact count.
- The rule classifier over-triggers on non-defect tickets (see Q3) — fine for
  the headline, not for a precise full-category breakdown.
- Replacement cost is the policy *planning* figure, not billed rupees; I did not
  reconcile against actual refunds (legacy currency unit is unsafe — §9).
- No dedup beyond a logical-duplicate check; I trusted that `ticket_id` is unique
  (it is, in this export).
- `honest_hours` and the data are committed to a public repo — the data is the
  (fictional) sample you provided, but worth noting.

### 6. What did you deliberately leave out, and why?

First-contact-resolution + repeat-contact costing, the ₹350 SLA-credit P&L,
voice/IVR transcript parsing (1,081 of them), and any forecasting model. Each is
real but was a *second* analysis; with a 5-hour cap I spent the budget on the one
finding that changes a decision and carries the most money. They're listed as
next steps in `docs/decisions.md`, not dropped silently.

### 7. Anything you built or found that nobody asked for?

- The **timezone bug**: 2,121 legacy tickets "resolve before they're created."
  Any handle-time report built on the raw export is wrong; I'd flag this to
  Sameer regardless of this engagement.
- The **"right one is fine" signal**: customers describe the same defect dozens
  of ways ("left is a paperweight", "lft one won't wake up", "right at 100");
  the classifier reads the implied-left-failure phrasing, not just the word
  "left".
- The replacement surge is **already declining** (Apr–Jun), consistent with the
  bad lots working through the field — useful for sizing the remaining exposure.

### 8. What did you use AI for? (tools, models, where it helped/wasted time, what you threw away) + video link

> **[CONFIRM this reflects your reality before submitting, then paste your video link.]**

This was an AI-first build. I used **Claude Code (Opus 4.8)** as the primary
engineer and directed it end-to-end in one session; I reviewed the data findings,
made the scoping/judgment calls, and wrote the gold labels by reading tickets.

- **Where it helped most:** the exploratory data analysis (it found the timezone
  bug, the Pulse 2 concentration, and the Tier-2-at-the-bottom trap fast), and
  turning that into a runnable pipeline + dashboard.
- **Where it wasted time / what I threw away:** the first defect classifier was
  too literal — it keyed on "left" + "charge" and missed the common paraphrases
  ("paperweight", "does not wake up", "right one is fine", the "lft" typo). I
  caught it against the gold set (it was ~80%), read more raw tickets, and
  rewrote the patterns to 88% / 100%-on-left-bud. I also discarded the idea of
  running the LLM classifier across all tickets once I re-read Finance's cost line.
- **Models considered:** shipped rules (₹0) as the default; Claude Haiku 4.5 as
  the optional paid path (~₹345/full run).

**Three-minute screen recording:** https://drive.google.com/file/d/1tMK7Kvqkua0-7fIGqu2VHkbwrRpY6hRM/view?usp=sharing

### 9. Someone picks this up Monday and you're unreachable. The three things.

1. `python run.py` from the repo reproduces everything into `outputs/`; the
   headline is Pulse 2 lots PL2-2510/2511/2512.
2. The agent "bottom ten" is a trap — use the **Tier-1-only** table in the
   dashboard, not the raw one. Why is in `docs/decisions.md`.
3. All cost/SLA constants live in `config.yaml`, lifted from `support-policy.pdf`
   — change them there, not in code. Lot numbers are ~65%-coverage, directional.

### 10. Honest hours spent. One number.

> **[FILL IN YOUR REAL NUMBER.]** Count your actual hands-on time: directing the
> build, reading the output, understanding it well enough to defend it, and
> recording the video. Be honest — the form says this can only help you, and the
> next round is a live conversation about this work.

### 11. GitHub repo link

https://github.com/aymanqwerty/banao_assignment
