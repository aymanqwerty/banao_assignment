"""Render outputs: numbers.json, agent_scorecard.csv, data_quality_report.md,
and a single self-contained dashboard.html (no external libraries, opens offline).
"""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd


def _rupee(x) -> str:
    try:
        return "Rs " + f"{float(x):,.0f}"
    except Exception:
        return str(x)


def _bar_rows(labels, values, fmt=_rupee, color="#2563eb"):
    mx = max(values) if len(values) and max(values) else 1
    out = []
    for lab, val in zip(labels, values):
        w = max(1, round(100 * val / mx))
        out.append(
            f"<div class='bar'><span class='lab'>{lab}</span>"
            f"<span class='track'><span class='fill' style='width:{w}%;background:{color}'></span></span>"
            f"<span class='val'>{fmt(val)}</span></div>"
        )
    return "\n".join(out)


def _table(df: pd.DataFrame, money_cols=()) -> str:
    cols = list(df.columns)
    head = "".join(f"<th>{c}</th>" for c in cols)
    body = []
    for _, r in df.iterrows():
        tds = []
        for c in cols:
            v = _rupee(r[c]) if c in money_cols else r[c]
            tds.append(f"<td>{v}</td>")
        body.append("<tr>" + "".join(tds) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def write_outputs(tickets, dq, sc, an, val, cfg):
    out: Path = cfg["_out_dir"]

    # ---- machine-readable numbers ----
    numbers = {
        "data_quality": dq,
        "money": {k: v for k, v in an.items() if not isinstance(v, pd.DataFrame)},
        "scorecard": {
            "naive_bottom_tier2_count": sc["naive_bottom_tier2_count"],
            "naive_bottom": sc["naive_bottom"].to_dict("records"),
            "fair_bottom": sc["fair_bottom"].to_dict("records"),
        },
        "validation": {
            "data_quality_checks": val["dq_checks"],
            "classifier": val["classifier"],
        },
    }
    (out / "numbers.json").write_text(json.dumps(numbers, indent=2, default=str), encoding="utf-8")
    sc["per_agent"].to_csv(out / "agent_scorecard.csv", index=False)

    # ---- data-quality report ----
    dq_md = ["# Data-quality report", ""]
    for c in val["dq_checks"]:
        mark = "PASS" if c["pass"] else "FAIL"
        dq_md.append(f"- [{mark}] **{c['check']}** - {c['detail']}")
    dq_md += ["", "## Raw counts"]
    for k, v in dq.items():
        dq_md.append(f"- {k}: {v}")
    (out / "data_quality_report.md").write_text("\n".join(dq_md), encoding="utf-8")

    # ---- dashboard ----
    cbp = an["cost_by_product"].head(8)
    qdf = an["cost_by_quarter"]
    clf = val["classifier"]
    clf_line = (
        f"{clf['accuracy']:.0%} on {clf['n']} hand-labelled tickets"
        if clf.get("available") else "not run"
    )
    left_share = an.get("pulse2_left_bud_share")
    left_line = f"{left_share:.0%} of Pulse 2 replacements are the same defect (left earbud won't charge)" if left_share is not None else ""

    dq_html = "".join(
        f"<li class='{'ok' if c['pass'] else 'bad'}'>{'PASS' if c['pass'] else 'FAIL'} - "
        f"<b>{c['check']}</b>: {c['detail']}</li>" for c in val["dq_checks"]
    )

    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Vireo Support Triage</title>
<style>
:root{{--ink:#0f172a;--mut:#64748b;--line:#e2e8f0;--bg:#f8fafc;--card:#fff;--blue:#2563eb;--red:#dc2626;--green:#16a34a;}}
*{{box-sizing:border-box}}body{{margin:0;font:15px/1.5 system-ui,Segoe UI,Roboto,sans-serif;color:var(--ink);background:var(--bg)}}
.wrap{{max-width:1040px;margin:0 auto;padding:28px 20px 64px}}
h1{{font-size:26px;margin:0 0 2px}}h2{{font-size:18px;margin:34px 0 12px;border-bottom:2px solid var(--line);padding-bottom:6px}}
.sub{{color:var(--mut);margin:0 0 20px}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px;margin:18px 0}}
.kpi{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}}
.kpi .n{{font-size:24px;font-weight:700}}.kpi .l{{color:var(--mut);font-size:13px;margin-top:4px}}
.kpi.red .n{{color:var(--red)}}.kpi.blue .n{{color:var(--blue)}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px;margin:12px 0}}
.bar{{display:grid;grid-template-columns:150px 1fr 110px;align-items:center;gap:10px;margin:6px 0;font-size:13px}}
.bar .track{{background:#eef2f7;border-radius:6px;overflow:hidden;height:16px}}.bar .fill{{display:block;height:16px}}
.bar .val{{text-align:right;color:var(--mut)}}
table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{text-align:left;padding:7px 9px;border-bottom:1px solid var(--line)}}
th{{color:var(--mut);font-weight:600}}
.callout{{background:#fff7ed;border:1px solid #fed7aa;border-radius:12px;padding:16px 18px;margin:16px 0}}
.callout b{{color:#b45309}}
ul.checks{{list-style:none;padding:0;margin:0;font-size:13px}}ul.checks li{{padding:4px 0}}
.ok{{color:var(--green)}}.bad{{color:var(--red)}}
.note{{color:var(--mut);font-size:12px;margin-top:8px}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}@media(max-width:760px){{.two{{grid-template-columns:1fr}}.bar{{grid-template-columns:110px 1fr 90px}}}}
</style></head><body><div class="wrap">
<h1>Vireo Audio - Support Triage</h1>
<p class="sub">Generated from tickets.csv (Jan 2025 - Jun 2026). All figures recomputed from the raw exports; replacement cost = unit_cost + Rs 340 (policy s5).</p>

<div class="callout">
<b>Headline:</b> The replacement bill, not the agents, is where the money is.
Pulse 2 earbuds account for <b>{_rupee(an['pulse2_cost_total'])}</b>
({an['pulse2_share_of_cost']:.0%}) of all replacement spend and
<b>{an['last_quarter_pulse2_share']:.0%}</b> of last quarter's bill.
{left_line}, concentrated in lots PL2-2510/2511/2512 - a batch problem, not a training problem.
</div>

<div class="kpis">
<div class="kpi red"><div class="n">{_rupee(an['pulse2_cost_since_surge'])}</div><div class="l">Pulse 2 replacement cost since Dec 2025 ({an['pulse2_units_since_surge']} units)</div></div>
<div class="kpi blue"><div class="n">{_rupee(an['replacement_cost_total'])}</div><div class="l">Total replacement spend, 18 months ({an['replacements_total']} units)</div></div>
<div class="kpi"><div class="n">{_rupee(an['avg_replacement_cost'])}</div><div class="l">Actual avg / replacement (Finance planned at Rs 2,500 - {int(an['arjun_overstatement_pct'])}% high)</div></div>
<div class="kpi"><div class="n">{sc['naive_bottom_tier2_count']} of 10</div><div class="l">"Bottom 10" that are Tier-2 triage agents (should not be ranked vs Tier 1)</div></div>
</div>

<h2>Replacement spend by quarter</h2>
<div class="card">{_bar_rows(qdf['created_quarter'].tolist(), qdf['cost'].tolist())}
<div class="note">Spend rose ~9x from 2025Q1 to {an['peak_quarter']}, then began falling as the bad lots cleared.</div></div>

<h2>Where the replacements are (by product)</h2>
<div class="card">{_bar_rows(cbp['product_name'].tolist(), cbp['cost'].tolist())}</div>

<h2>Pulse 2 - manufacturing lot concentration</h2>
<div class="card two">
<div>{_table(an['pulse2_top_lots'].head(10))}</div>
<div>{_table(an['pulse2_defect_mix']) if 'pulse2_defect_mix' in an else '<p class=note>run with classifier for defect mix</p>'}
<div class="note">Lot codes PL2-YYMM-batch. The failures cluster in Oct-Dec 2025 production.</div></div>
</div>

<h2>Agent scorecard - the "bottom 10" trap</h2>
<div class="two">
<div class="card"><h3 style="margin:0 0 8px;font-size:14px">What was asked: bottom 10 by CSAT (all tiers)</h3>
{_table(sc['naive_bottom'][['name','team','tier','csat','handle_min_median']], )}
<div class="note">{sc['naive_bottom_tier2_count']} of these are Tier-2 Escalations &amp; Warranty - the hardest queue by design (Neha; policy s6).</div></div>
<div class="card"><h3 style="margin:0 0 8px;font-size:14px">Fair version: bottom 10 within Tier 1</h3>
{_table(sc['fair_bottom'][['name','team','csat','handle_min_median','pulse2_share']])}
<div class="note">These are the agents a training budget could genuinely help. pulse2_share shows how much is product-driven.</div></div>
</div>

<h2>CSAT by team</h2>
<div class="card">{_table(sc['tier_summary'])}</div>

<h2>Does it work?</h2>
<div class="card">
<p>Classifier accuracy: <b>{clf_line}</b>.</p>
<ul class="checks">{dq_html}</ul>
</div>

</div></body></html>"""
    (out / "dashboard.html").write_text(html, encoding="utf-8")
    return out
