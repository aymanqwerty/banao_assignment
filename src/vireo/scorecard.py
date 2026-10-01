"""Agent scorecard.

The client asked for "CSAT and handle time per agent, flag the bottom ten".
We build exactly that - and then correct it, because a naive bottom-ten is
actively misleading here:

  * support-policy.pdf s6: "Tier 2 agents are not to be compared with Tier 1 on
    volume metrics" and are measured in days, not tickets.
  * email-thread.txt (Neha): the Escalations & Warranty rota gets the angriest
    customers BY DESIGN - a low CSAT there is the queue, not the person.

So the fair ranking is computed WITHIN Tier 1 only, and we attach each agent's
"defect load" (share of their tickets that are replacement/Pulse-2 cases) so a
reader can see when a low score is being driven by the product, not the agent.
"""
from __future__ import annotations
import pandas as pd


def build_scorecard(tickets: pd.DataFrame, cfg: dict) -> dict:
    min_rated = cfg["scorecard"]["min_rated_tickets"]
    flag_n = cfg["scorecard"]["flag_count"]

    t = tickets.copy()
    t["is_pulse2"] = t["product_sku"].eq("VA-EB-PL2")
    has_defect = "defect_label" in t.columns

    g = t.groupby("agent_id")
    rows = pd.DataFrame({
        "name": g["agent_name"].first(),
        "team": g["agent_team"].first(),
        "tier": g["agent_tier"].first(),
        "site": g["agent_site"].first(),
        "tickets": g.size(),
        "n_rated": g["csat_score"].count(),
        "csat": g["csat_score"].mean().round(2),
        "handle_min_median": g["handle_min"].median().round(0),
        "sla_breach_rate": g["sla_breach"].mean().round(3),
        "replacement_rate": g["replacement_issued"].apply(lambda s: s.eq("Y").mean()).round(3),
        "pulse2_share": g["is_pulse2"].mean().round(3),
    })
    if has_defect:
        rows["left_bud_share"] = g["defect_label"].apply(
            lambda s: s.eq("left_bud_charging").mean()
        ).round(3)

    rows = rows.reset_index()
    rated = rows[rows["n_rated"] >= min_rated].copy()

    # What the client literally asked for: bottom N by CSAT, all tiers mixed.
    naive_bottom = rated.sort_values("csat").head(flag_n).reset_index(drop=True)

    # The fair version: Tier 1 only (Tier 2 is out of scope for this comparison
    # per policy s6), ranked by CSAT.
    tier1 = rated[rated["tier"] == 1].copy()
    fair_bottom = tier1.sort_values("csat").head(flag_n).reset_index(drop=True)

    tier_summary = (
        t.dropna(subset=["csat_score"]).groupby(["agent_tier", "agent_team"])["csat_score"]
        .agg(csat_mean="mean", n_rated="size").round(2).reset_index()
        .rename(columns={"agent_tier": "tier", "agent_team": "team"})
    )

    naive_tier2 = int((naive_bottom["tier"] == 2).sum())

    return {
        "per_agent": rows.sort_values(["tier", "csat"]).reset_index(drop=True),
        "naive_bottom": naive_bottom,
        "fair_bottom": fair_bottom,
        "tier_summary": tier_summary,
        "naive_bottom_tier2_count": naive_tier2,
    }
