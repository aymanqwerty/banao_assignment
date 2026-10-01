#!/usr/bin/env python3
"""Vireo Support Triage - one-command pipeline.

    python run.py                 # full run, rule-based classifier (zero API cost)
    python run.py --classify llm  # optional: Claude Haiku classifier (needs ANTHROPIC_API_KEY)

Outputs land in ./outputs: dashboard.html, numbers.json, agent_scorecard.csv,
data_quality_report.md
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from vireo.config import load_config
from vireo.clean import load_clean
from vireo.classify import classify_frame, estimate_llm_cost
from vireo.scorecard import build_scorecard
from vireo.analyze import analyze
from vireo.validate import data_quality_checks, classifier_eval
from vireo.report import write_outputs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--classify", choices=["rule", "llm"], default="rule",
                    help="defect classifier backend (default: rule, zero cost)")
    ap.add_argument("--config", default=None)
    args = ap.parse_args()

    cfg = load_config(args.config)
    print("1/5  loading + cleaning exports ...")
    tickets, dq = load_clean(cfg)
    print(f"      {dq['rows_clean']} tickets | fixed {dq['legacy_resolved_before_created_before_fix']} "
          f"legacy timezones | excluded {dq['csat_blank']} blank CSAT")

    print(f"2/5  classifying defects ({args.classify}) ...")
    tickets["defect_label"] = classify_frame(tickets, backend=args.classify)
    est = estimate_llm_cost(len(tickets), cfg["usd_to_inr"])
    print(f"      this run cost: {'Rs 0 (offline rules)' if args.classify=='rule' else 'see Haiku call log'}"
          f"  |  Haiku would cost ~Rs {est['inr']:.0f} for all {est['tickets']} tickets")

    print("3/5  building fair agent scorecard ...")
    sc = build_scorecard(tickets, cfg)

    print("4/5  analysing replacement spend ...")
    an = analyze(tickets, cfg)

    print("5/5  validating + writing outputs ...")
    val = {
        "dq_checks": data_quality_checks(tickets, dq),
        "classifier": classifier_eval(tickets),
    }
    out = write_outputs(tickets, dq, sc, an, val, cfg)

    failed = [c for c in val["dq_checks"] if not c["pass"]]
    print("\nDONE.")
    print(f"  headline: Pulse 2 = {an['pulse2_share_of_cost']:.0%} of replacement spend, "
          f"Rs {an['pulse2_cost_since_surge']:,.0f} since Dec 2025")
    if val["classifier"].get("available"):
        print(f"  classifier accuracy: {val['classifier']['accuracy']:.0%} "
              f"on {val['classifier']['n']} labelled tickets")
    print(f"  data-quality checks: {len(val['dq_checks'])-len(failed)}/{len(val['dq_checks'])} passed")
    print(f"  open: {out / 'dashboard.html'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
