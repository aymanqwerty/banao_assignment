"""Find the money. Everything here is replacement-cost arithmetic built on the
unit-safe formula from support-policy.pdf s5 (unit_cost + Rs 340), NOT on the
legacy-tainted refund_amount column.
"""
from __future__ import annotations
import pandas as pd


def analyze(tickets: pd.DataFrame, cfg: dict) -> dict:
    logistics = cfg["costs"]["replacement_logistics_inr"]
    surge_start = pd.Timestamp(cfg["surge_start"])
    rep = tickets[tickets["replacement_issued"].eq("Y")].copy()
    rep["created_at"] = pd.to_datetime(rep["created_at"])

    out: dict = {}
    out["replacements_total"] = int(len(rep))
    out["replacement_cost_total"] = float(rep["replacement_cost_inr"].sum())
    out["avg_replacement_cost"] = round(float(rep["replacement_cost_inr"].mean()), 0)

    # Arjun (email-thread.txt) planned at Rs 2,500 all-in. Policy says unit+340.
    out["arjun_estimate_inr"] = 2500
    out["arjun_overstatement_pct"] = round(
        (2500 - out["avg_replacement_cost"]) / out["avg_replacement_cost"] * 100, 0
    )

    # Trend
    by_q = rep.groupby("created_quarter")["replacement_cost_inr"].agg(["size", "sum"])
    out["cost_by_quarter"] = by_q.rename(columns={"size": "units", "sum": "cost"}).reset_index()
    by_m = rep.groupby("created_month").size()
    out["units_by_month"] = by_m.reset_index(name="units")

    # Concentration
    by_prod = (
        rep.groupby("product_name")["replacement_cost_inr"]
        .agg(units="size", cost="sum").sort_values("cost", ascending=False).reset_index()
    )
    out["cost_by_product"] = by_prod
    by_fam = (
        rep.groupby("family")["replacement_cost_inr"]
        .agg(units="size", cost="sum").sort_values("cost", ascending=False).reset_index()
    )
    out["cost_by_family"] = by_fam

    # --- The Pulse 2 story -------------------------------------------------
    p2 = rep[rep["product_name"] == "Pulse 2 True Wireless Earbuds"]
    p2_surge = p2[p2["created_at"] >= surge_start]
    out["pulse2_units_total"] = int(len(p2))
    out["pulse2_cost_total"] = float(p2["replacement_cost_inr"].sum())
    out["pulse2_share_of_cost"] = round(out["pulse2_cost_total"] / out["replacement_cost_total"], 3)
    out["pulse2_units_since_surge"] = int(len(p2_surge))
    out["pulse2_cost_since_surge"] = float(p2_surge["replacement_cost_inr"].sum())

    # Latest full quarter share
    last_q = by_q.index.max()
    q_total = float(by_q.loc[last_q, "sum"])
    q_p2 = float(p2[p2["created_quarter"] == last_q]["replacement_cost_inr"].sum())
    out["last_quarter"] = str(last_q)
    out["last_quarter_cost_total"] = q_total
    out["last_quarter_pulse2_cost"] = q_p2
    out["last_quarter_pulse2_share"] = round(q_p2 / q_total, 3) if q_total else 0.0

    # Peak quarter (the run-rate to quote)
    peak_q = by_q["sum"].idxmax()
    out["peak_quarter"] = str(peak_q)
    out["peak_quarter_cost"] = float(by_q.loc[peak_q, "sum"])
    out["peak_quarter_pulse2_cost"] = float(
        p2[p2["created_quarter"] == str(peak_q)]["replacement_cost_inr"].sum()
    )

    # Manufacturing-lot concentration among Pulse 2 replacements
    lot = p2["lot_code"].dropna()
    out["pulse2_lot_join_rate"] = round(float(p2["lot_code"].notna().mean()), 3)
    out["pulse2_top_lots"] = (
        lot.value_counts().head(12).rename_axis("lot_code").reset_index(name="units")
    )

    # Defect-theme split for Pulse 2 replacements (if classifier was run)
    if "defect_label" in p2.columns:
        vc = p2["defect_label"].value_counts()
        out["pulse2_defect_mix"] = vc.rename_axis("defect").reset_index(name="units")
        out["pulse2_left_bud_share"] = round(
            float((p2["defect_label"] == "left_bud_charging").mean()), 3
        )

    return out
