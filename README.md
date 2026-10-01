# Vireo Audio — Support Triage

A small, runnable tool that turns Vireo's raw support exports into two things
the "CSAT dashboard" brief was really asking for:

1. **A fair agent scorecard** — CSAT and handle time per agent, with the "bottom
   ten" the client asked for *and* the corrected version that doesn't punish the
   Tier-2 warranty team for handling the hardest queue by design.
2. **A root-cause view of the money** — where replacement spend is actually going.

**Headline it produces:** the replacement bill, not the agents, is the problem.
Pulse 2 earbuds are **62% of all replacement spend** and **₹19.6 lakh since
December 2025**, two-thirds of it the *same* defect (the left earbud won't
charge), concentrated in manufacturing lots PL2-2510/2511/2512. A ₹4 lakh
agent-training budget addresses none of it.

---

## Quickstart (clean machine)

Requires Python 3.10+.

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

python run.py
```

That's the whole thing. It reads the CSVs in `data/`, runs offline (no API
calls, no network, ₹0), and writes to `outputs/`:

| file | what it is |
|---|---|
| `dashboard.html` | open in any browser — the one page to look at |
| `numbers.json` | every figure the memo cites, machine-readable |
| `agent_scorecard.csv` | per-agent CSAT, handle time, SLA breach, defect load |
| `data_quality_report.md` | the cleaning decisions + pass/fail checks |

The run prints the headline number and the validation results, and exits
non-zero if any data-quality check fails.

> In a hurry? A pre-generated copy is committed in **`sample_output/`** — open
> `sample_output/dashboard.html` to see the result without running anything.

## Optional: LLM defect classifier

The defect themes are tagged by a deterministic rule classifier by default
(zero cost — this is deliberate; see "On cost" below). An optional Claude Haiku
backend exists for comparison:

```bash
export ANTHROPIC_API_KEY=sk-ant-...   # your own key; none is bundled
python run.py --classify llm
```

Estimated cost of the LLM path: **~₹345 to classify all 11,750 tickets once**
(Haiku 4.5 at $1/$5 per 1M tokens). The rule classifier gets the headline signal
for ₹0 and scores **88% against a 60-ticket hand-labelled set** (100% on the one
label that matters, `left_bud_charging`).

## On cost

Finance (see `data/email-thread.txt`) explicitly did not want "per-ticket model
calls at ₹5 a pop across twelve thousand tickets" (≈ ₹60,000). This tool's
default answer to that is ₹0: the rules run locally. The LLM is strictly an
opt-in upgrade, and even then costs ~₹345/run, not ₹60,000.

## What it handles (and why)

The raw data has traps that quietly break the obvious analysis. Each is handled
in `src/vireo/clean.py` and logged in `docs/decisions.md`:

- Legacy (Freshdesk) `resolved_at` is in **UTC** while everything else is IST —
  2,121 tickets otherwise "resolve before they're created". Fixed with +5:30.
- Blank CSAT (56% of rows) is **excluded**, never treated as 0 (policy §8).
- Two agents share the name "Kavya Pandey" — joins are on `agent_id` only.
- Replacement cost uses `unit_cost + ₹340` (policy §5), which sidesteps the
  legacy tool's different money unit.
- Tier-2 agents are kept out of the cross-tier ranking (policy §6).

## Repo layout

```
run.py                 # one-command pipeline
config.yaml            # all cost/SLA constants (from support-policy.pdf)
src/vireo/
  clean.py             # load + data-quality fixes
  classify.py          # defect classifier (rule default, Haiku optional)
  scorecard.py         # fair agent scorecard
  analyze.py           # replacement-cost / root-cause arithmetic
  validate.py          # data-quality checks + classifier accuracy
  report.py            # dashboard.html + numbers.json
tests/gold_labels.csv  # 60 hand-labelled tickets for the accuracy check
docs/decisions.md      # what I decided where the brief was silent, and why
data/                  # the provided assignment exports
outputs/               # generated (gitignored)
```

## A note on the data

`data/` contains the assignment's own (fictional) Vireo Audio exports, included
so the tool runs end-to-end on a clean machine. It is synthetic sample data.
