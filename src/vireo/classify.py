"""Classify a ticket's free-text into a defect theme.

Two interchangeable backends:
  * rule   - deterministic regex. Zero API cost. This is the default and what
             the numbers in the report are built on.
  * llm    - Claude Haiku 4.5, one cheap call per ticket, batched. Optional,
             only runs if you ask for it and set ANTHROPIC_API_KEY. It exists to
             show the upgrade path and to be benchmarked against the rules.

Finance (email-thread.txt, Arjun) explicitly did not want "per-ticket model
calls at Rs 5 a pop". The rule backend is the answer to that: it gets the same
headline signal for Rs 0. See docs/decisions.md.
"""
from __future__ import annotations
import re
import pandas as pd

# Ordered most-specific -> least. First match wins.
LABELS = [
    "left_bud_charging",
    "charging_battery",
    "connectivity_pairing",
    "audio_quality",
    "transit_damage",
    "wrong_item",
    "other",
]

# "One side is dead" is the Pulse 2 signature. Customers phrase it many ways, so
# we match (a) a left-side token near a failure word, (b) the reverse order, and
# (c) "the right one is fine / at 100 / lights up" - which also means the left is
# the broken one. Window is wide (60 chars) because the clause is chatty.
_LEFT = r"(left|lft|\bl\b|l[-\s]?bud|l[-\s]?pod|lhs)"
_FAIL = (r"(charg|not taking|no\s*charge|won'?t charge|0\s*%|dead|won'?t turn on|"
         r"green light|lights?\s*up|\bled\b|power|wake up|does ?n'?t wake|paperweight|"
         r"stays flat|gives up|not working|\bflat\b|sits? (properly|flat))")
_RIGHT_FINE = r"right\s*(one|side|bud|ear|pod)?.{0,20}(fine|works?|perfectly|100|lasts|all day|lights?\s*up)"
_PATTERNS = [
    ("left_bud_charging", re.compile(_LEFT + r".{0,60}?" + _FAIL, re.I)),
    ("left_bud_charging", re.compile(_FAIL + r".{0,60}?" + _LEFT, re.I)),
    ("left_bud_charging", re.compile(_RIGHT_FINE, re.I)),
    ("charging_battery", re.compile(r"(charg|battery|drain|discharge|\bdies\b|0\s*%|not taking charge|won'?t turn on)", re.I)),
    ("connectivity_pairing", re.compile(r"(pair|bluetooth|connect|disconnect|drop|cutting out|cuts out|keeps cutting|vanish|latency|\blag\b|discoverable)", re.I)),
    ("audio_quality", re.compile(r"(sound|audio|stutter|crackl|distort|muffl|static|volume|\bmic\b|microphone|low vol|one side.{0,10}(quiet|silent))", re.I)),
    ("transit_damage", re.compile(r"(damag|broke|broken|crack|dent|crush|transit|smashed|physically)", re.I)),
    ("wrong_item", re.compile(r"(wrong|different (item|thing|one|product|variant|colou?r|ting)|completely different|something else|not what i ordered|got.{0,15}else|mismatch)", re.I)),
]


def classify_rule(text: str) -> str:
    """Return a single defect label for one ticket's combined text."""
    t = (text or "").lower()
    for label, pat in _PATTERNS:
        if pat.search(t):
            return label
    return "other"


def combined_text(df: pd.DataFrame) -> pd.Series:
    msg = df["customer_message"].fillna("").astype(str)
    note = df["agent_notes"].fillna("").astype(str)
    # Drop the IVR marker so it is not read as signal.
    msg = msg.str.replace(r"\[IVR transcript\]", "", regex=True)
    return (msg + " || " + note).str.strip()


def classify_frame(df: pd.DataFrame, backend: str = "rule", model: str = "claude-haiku-4-5") -> pd.Series:
    text = combined_text(df)
    if backend == "rule":
        return text.map(classify_rule)
    if backend == "llm":
        return _classify_llm(text, model=model)
    raise ValueError(f"unknown backend: {backend}")


# --------------------------------------------------------------------------- #
# Optional LLM backend. Not imported unless called.
# --------------------------------------------------------------------------- #
_SYSTEM = (
    "You label a consumer-earbuds support ticket with ONE defect theme. "
    "Reply with exactly one of: " + ", ".join(LABELS) + ". "
    "Use 'left_bud_charging' only when one earbud (usually the left) will not "
    "charge or is dead. No other words."
)


def estimate_llm_cost(n_tickets: int, usd_to_inr: float = 84.0) -> dict:
    """Haiku 4.5 is $1.00 / 1M input, $5.00 / 1M output (Anthropic list price).
    Budget ~320 input tokens (system + ticket text) and ~6 output tokens each.
    """
    in_tok, out_tok = 320, 6
    usd = (n_tickets * in_tok / 1e6) * 1.00 + (n_tickets * out_tok / 1e6) * 5.00
    return {
        "tickets": n_tickets,
        "model": "claude-haiku-4-5",
        "usd": round(usd, 4),
        "inr": round(usd * usd_to_inr, 2),
        "inr_per_ticket": round(usd * usd_to_inr / max(n_tickets, 1), 4),
    }


def _classify_llm(text: pd.Series, model: str = "claude-haiku-4-5") -> pd.Series:
    from anthropic import Anthropic  # noqa: local import, optional dependency

    client = Anthropic()  # reads ANTHROPIC_API_KEY / ant profile
    valid = set(LABELS)
    out = []
    for snippet in text:
        resp = client.messages.create(
            model=model,
            max_tokens=8,
            system=_SYSTEM,
            messages=[{"role": "user", "content": snippet[:1200]}],
        )
        label = resp.content[0].text.strip().lower()
        out.append(label if label in valid else "other")
    return pd.Series(out, index=text.index)
