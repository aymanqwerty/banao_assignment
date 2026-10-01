# Decisions log

The brief is a client email, not a spec. Where it was silent or where the data
contradicted the ask, I decided, wrote it down, and said why. In order of how
much they change the answer.

## 1. I answered the question under the question
**Asked:** a dashboard of CSAT + handle time per agent, flag the bottom ten, to
aim a ₹4 lakh training budget.
**Decided:** build exactly that, but lead with *why CSAT is sliding*, because the
data answers it unambiguously and the training budget is pointed at the wrong
thing. The CSAT slide and the replacement surge are the same event: a Pulse 2
batch defect flooding the warranty queue. I kept the agent scorecard (it was
asked for) but the headline is the batch.
**Why:** Priya said "dashboard first, causes later" — but the cause was ₹20 lakh
large and sitting in the same table. Reporting the dashboard without it would be
technically compliant and practically negligent.

## 2. Tier-2 agents are not in the cross-tier ranking
**Decided:** the naive "bottom ten by CSAT" is shown (so the trap is visible),
but the *actionable* ranking is Tier-1-only.
**Why:** support-policy.pdf §6 — "Tier 2 agents are not to be compared with
Tier 1 on volume metrics", they're measured in days. Neha's email says the
Escalations & Warranty rota gets the angriest customers by design. The data
agrees: all six Tier-2 agents sit at the bottom on raw CSAT (2.4–2.8) with
handle times in the thousands of minutes. Retraining them would burn the budget
on the people absorbing the Pulse 2 fallout.

## 3. Replacement cost = unit_cost + ₹340, not refund_amount_inr
**Decided:** price every replacement from the policy formula, ignore the
`refund_amount_inr` column for totals.
**Why:** policy §9 says the legacy tool stored money in a different unit, and the
README says refund amounts are "as exported by each system" (i.e. not
normalised). The unit-cost formula is unit-safe and is what Finance uses for
business cases anyway. This also resolves the Arjun-vs-Priya argument in the
thread: actual average is **₹1,802**, not Arjun's ₹2,500 (39% high) — but the
*volume* he's worried about is real.

## 4. Fixed the legacy timezone before computing any duration
**Decided:** add +5:30 to `resolved_at` for `legacy_fd` rows only.
**Why:** 2,121 legacy tickets "resolve before they are created" because their
resolution timestamp was reconstructed from a UTC event log (policy §9) while
the rest of the export is IST. Left raw, every legacy handle time is negative or
wrong and the agent ranking is garbage.

## 5. Lot codes were the opposite of a distraction
Sameer said the orders export has lot codes, "ignore if not useful." They turned
out to be the whole story: the Pulse 2 failures concentrate in lots
PL2-2510/2511/2512 (Oct–Dec 2025 production). Kept them. The order join only
covers ~65% of tickets (customers often don't quote an order), so the lot view
is directional, not exact — stated as such.

## 6. Rule-based classifier shipped as the default; LLM is opt-in
**Why:** Arjun's cost line ("no per-ticket model calls at ₹5 a pop across twelve
thousand tickets"). The rules cost ₹0, run offline, and hit 88% / 100%-on-the-
key-label. A Haiku path exists for the upgrade conversation and to be
benchmarked, but shipping it as the default would have ignored the one hard cost
constraint in the thread.

## 7. What I deliberately left out (5-hour cap)
There is more here than fits. I cut, in rough priority order:
- **First-contact-resolution and repeat-contact costing** (policy §10) — real
  money, but a second analysis; the replacement story was bigger and cleaner.
- **SLA breach-credit P&L** (the ₹350 auto-credits) — computed the breach flag,
  did not cost it out.
- **Voice/IVR transcript NLP** — flagged and excluded the failed captures; did
  not try to parse the 1,081 voice transcripts.
- **Forecasting / seasonality model** — the trend is obvious by eye; a model
  would be effort without a decision attached.
- **Customer geography, care-plus cohort, channel deep-dives** — not on the
  critical path to "who to retrain / where's the money".
Each of these is a known next step, not an oversight.

## 8. Small thresholds
- An agent needs ≥20 CSAT responses to be ranked (noise control).
- Kept "bottom ten" at ten, per the literal ask.
- "Surge" defined as from 2025-12-01, matching Priya's "since the festive season"
  and the inflection in the monthly replacement counts.
