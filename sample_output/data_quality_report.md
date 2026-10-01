# Data-quality report

- [PASS] **no_negative_handle_time** - 0 rows still negative after TZ fix
- [PASS] **timezone_fix_applied** - 2121 legacy rows needed the +5:30 fix
- [PASS] **csat_not_zero_filled** - blank CSAT kept as NaN, never 0
- [PASS] **csat_response_rate_plausible** - response rate 44% (policy says ~45%)
- [PASS] **agent_join_complete** - 100.0% tickets matched to an agent
- [PASS] **replacement_cost_unit_safe** - every replacement priced from unit_cost + logistics

## Raw counts
- rows_raw: 11750
- legacy_resolved_before_created_before_fix: 2121
- negative_handle_after_fix: 0
- csat_blank: 6554
- csat_response_rate: 0.442
- agents_sharing_a_name: 1
- ivr_transcripts: 1076
- junk_messages: 14
- legacy_refund_rows_excluded: 572
- logical_duplicate_rows: 0
- lot_join_rate_overall: 0.65
- rows_clean: 11750