"""Load the raw exports and apply the data-quality fixes the brief hides in
support-policy.pdf and email-thread.txt.

Every non-obvious transformation here maps to a line in one of those documents.
The decisions are logged in docs/decisions.md. Nothing is cleaned silently:
counts for each fix land in the returned `dq` (data-quality) dict so the
dashboard and validator can show their working.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np


def _read(data_dir: Path, name: str, **kw) -> pd.DataFrame:
    return pd.read_csv(data_dir / name, **kw)


def load_clean(cfg: dict) -> tuple[pd.DataFrame, dict]:
    data_dir: Path = cfg["_data_dir"]
    dq: dict = {}

    tickets = _read(data_dir, "tickets.csv")
    agents = _read(data_dir, "agents.csv", parse_dates=["from_date", "to_date"])
    products = _read(data_dir, "products.csv")
    orders = _read(data_dir, "orders.csv")

    dq["rows_raw"] = len(tickets)

    for c in ("created_at", "first_response_at", "resolved_at"):
        tickets[c] = pd.to_datetime(tickets[c], errors="coerce")

    # ---- TRAP 1: timezone. (support-policy.pdf s9 + README) ---------------
    # The helpdesk export is IST, but legacy (Freshdesk) resolved_at was
    # reconstructed from a UTC event log. Left raw, 2,300+ legacy tickets
    # "resolve" before they are created and every legacy handle time is wrong.
    # Fix: push legacy resolved_at forward to IST. created_at / first_response_at
    # are already IST for every source.
    legacy = tickets["source_system"] == "legacy_fd"
    offset = pd.Timedelta(hours=cfg["legacy_resolved_utc_to_ist_hours"])
    dq["legacy_resolved_before_created_before_fix"] = int(
        (legacy & (tickets["resolved_at"] < tickets["created_at"])).sum()
    )
    tickets["resolved_at_fixed"] = tickets["resolved_at"]
    tickets.loc[legacy, "resolved_at_fixed"] = tickets.loc[legacy, "resolved_at"] + offset

    # ---- handle time + first-response latency ------------------------------
    tickets["handle_min"] = (
        tickets["resolved_at_fixed"] - tickets["first_response_at"]
    ).dt.total_seconds() / 60.0
    tickets["first_response_min"] = (
        tickets["first_response_at"] - tickets["created_at"]
    ).dt.total_seconds() / 60.0
    dq["negative_handle_after_fix"] = int((tickets["handle_min"] < 0).sum())
    # A handful of genuinely bad rows can remain; null them rather than let a
    # negative duration poison a median.
    tickets.loc[tickets["handle_min"] < 0, "handle_min"] = np.nan

    # ---- TRAP 2: CSAT blanks. (support-policy.pdf s8) ----------------------
    # Blank = no survey response. Must be EXCLUDED from averages, never treated
    # as zero. We keep it as NaN; pandas .mean() ignores NaN by default.
    tickets["csat_score"] = pd.to_numeric(tickets["csat_score"], errors="coerce")
    dq["csat_blank"] = int(tickets["csat_score"].isna().sum())
    dq["csat_response_rate"] = round(float(tickets["csat_score"].notna().mean()), 3)

    # ---- TRAP 3: agent identity. (email-thread.txt, Sameer) ----------------
    # Two agents share a display name ("Kavya Pandey"). Join on agent_id only.
    # An agent may have several roster rows (site/shift changes); take the most
    # recent assignment for their current tier/team/site.
    latest = (
        agents.sort_values("from_date").groupby("agent_id", as_index=False).tail(1)
    )
    dq["agents_sharing_a_name"] = int(
        (agents.groupby("name")["agent_id"].nunique() > 1).sum()
    )
    amap = latest.set_index("agent_id")
    for col in ("name", "team", "tier", "site", "shift"):
        tickets[f"agent_{col}"] = tickets["agent_id"].map(amap[col])

    # ---- TRAP 4: junk free-text. (email-thread.txt, Sameer) ----------------
    # Failed IVR captures are phone-system noise, not agent behaviour. Flag the
    # voice-transcript marker and the genuinely empty/garbage messages so text
    # analysis can exclude them.
    msg = tickets["customer_message"].fillna("").astype(str)
    tickets["is_ivr_transcript"] = msg.str.contains(r"\[IVR transcript\]", case=False)
    stripped = msg.str.replace(r"\[IVR transcript\]", "", regex=True).str.strip()
    tickets["is_junk_message"] = stripped.str.len() < 5
    dq["ivr_transcripts"] = int(tickets["is_ivr_transcript"].sum())
    dq["junk_messages"] = int(tickets["is_junk_message"].sum())

    # ---- TRAP 5: legacy money unit. (support-policy.pdf s9) ----------------
    # The legacy tool stored money in its own unit. We therefore DO NOT trust
    # refund_amount_inr from legacy rows for totals; the replacement-cost number
    # below is built from products.unit_cost instead, which is unit-safe.
    tickets["refund_amount_trusted"] = tickets["refund_amount_inr"]
    tickets.loc[legacy, "refund_amount_trusted"] = np.nan
    dq["legacy_refund_rows_excluded"] = int(
        (legacy & tickets["refund_amount_inr"].notna()).sum()
    )

    # ---- TRAP 6: re-imported duplicates. (support-policy.pdf s9) -----------
    # ticket_id is unique in this export, but check for the logical duplicate
    # the policy warns about: same customer, same minute, same opening message.
    key = (
        tickets["customer_id"].astype(str)
        + "|" + tickets["created_at"].astype(str)
        + "|" + msg.str.slice(0, 40)
    )
    dq["logical_duplicate_rows"] = int(key.duplicated().sum())

    # ---- enrichment: product cost + replacement cost ----------------------
    pcols = ["sku", "product_name", "family", "unit_cost_inr"]
    tickets = tickets.merge(
        products[pcols], left_on="product_sku", right_on="sku", how="left"
    ).drop(columns="sku")
    logistics = cfg["costs"]["replacement_logistics_inr"]
    tickets["replacement_cost_inr"] = np.where(
        tickets["replacement_issued"].eq("Y"),
        tickets["unit_cost_inr"] + logistics,
        0.0,
    )

    # lot code (manufacturing batch) via order_id; ~36% of tickets quote no order
    o = orders[["order_id", "lot_code"]].drop_duplicates("order_id")
    tickets = tickets.merge(o, on="order_id", how="left")
    dq["lot_join_rate_overall"] = round(float(tickets["lot_code"].notna().mean()), 3)

    # ---- SLA first-response breach. (support-policy.pdf s3) ----------------
    targets = cfg["sla_first_response_min"]
    tgt = tickets["channel"].map(targets)
    tickets["sla_breach"] = tickets["first_response_min"] > tgt

    tickets["created_month"] = tickets["created_at"].dt.to_period("M").astype(str)
    tickets["created_quarter"] = tickets["created_at"].dt.to_period("Q").astype(str)

    dq["rows_clean"] = len(tickets)
    return tickets, dq
