"""How do you know it works?

Two kinds of check, both run every pipeline:

1. Data-quality assertions - cheap invariants that must hold after cleaning.
   If one fails, the number downstream is not trustworthy and the run says so.

2. Classifier accuracy - the rule classifier is scored against a hand-labelled
   gold set (tests/gold_labels.csv, 60 tickets labelled by reading them). We
   report overall accuracy, per-class recall, and the cases it gets wrong.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

from .classify import classify_rule, combined_text
from .config import REPO_ROOT


def data_quality_checks(tickets: pd.DataFrame, dq: dict) -> list[dict]:
    checks = []

    def add(name, ok, detail):
        checks.append({"check": name, "pass": bool(ok), "detail": detail})

    add("no_negative_handle_time",
        dq["negative_handle_after_fix"] == 0,
        f"{dq['negative_handle_after_fix']} rows still negative after TZ fix")
    add("timezone_fix_applied",
        dq["legacy_resolved_before_created_before_fix"] > 0,
        f"{dq['legacy_resolved_before_created_before_fix']} legacy rows needed the +5:30 fix")
    add("csat_not_zero_filled",
        (tickets["csat_score"].fillna(-1).ge(1) | tickets["csat_score"].isna()).all(),
        "blank CSAT kept as NaN, never 0")
    add("csat_response_rate_plausible",
        0.3 <= dq["csat_response_rate"] <= 0.6,
        f"response rate {dq['csat_response_rate']:.0%} (policy says ~45%)")
    add("agent_join_complete",
        tickets["agent_tier"].notna().mean() > 0.99,
        f"{tickets['agent_tier'].notna().mean():.1%} tickets matched to an agent")
    add("replacement_cost_unit_safe",
        (tickets.loc[tickets['replacement_issued'].eq('Y'), 'replacement_cost_inr'] > 0).all(),
        "every replacement priced from unit_cost + logistics")
    return checks


def classifier_eval(tickets: pd.DataFrame) -> dict:
    gold_path = REPO_ROOT / "tests" / "gold_labels.csv"
    if not gold_path.exists():
        return {"available": False, "note": "no gold set found"}

    gold = pd.read_csv(gold_path)
    merged = gold.merge(
        tickets[["ticket_id", "customer_message", "agent_notes"]],
        on="ticket_id", how="left",
    )
    missing = int(merged["customer_message"].isna().sum())
    merged = merged.dropna(subset=["customer_message", "agent_notes"], how="all")
    merged["pred"] = combined_text(merged).map(classify_rule)

    n = len(merged)
    correct = int((merged["pred"] == merged["label"]).sum())
    acc = round(correct / n, 3) if n else 0.0

    # per-class recall
    merged["_hit"] = merged["pred"] == merged["label"]
    per_class = (
        merged.groupby("label")["_hit"].agg(n="size", recall="mean").round(2).reset_index()
    )
    errors = merged.loc[merged["pred"] != merged["label"],
                        ["ticket_id", "label", "pred"]].to_dict("records")
    return {
        "available": True,
        "n": n,
        "accuracy": acc,
        "correct": correct,
        "gold_rows_unmatched": missing,
        "per_class_recall": per_class.to_dict("records"),
        "errors": errors,
    }
