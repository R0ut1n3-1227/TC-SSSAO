"""05 - Dangerous-reachability analysis.

If R8 Dangerous instances exist: export the top 20 (by Pc) and verify each
one end-to-end (raw row exists, prob/min_range match the normalized values,
HBR join re-derived from the mapping file, unit conversion re-checked).

If Dangerous is empty: do NOT fabricate samples and do NOT touch rules;
instead decompose the cause into the exact failing conjuncts.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from common import (
    RESULTS, THETA_M, classify_states, ensure_dirs, load_hbr_map,
    load_normalized, load_sfsh, rel, save_json,
)

TOP_N = 20


def main() -> None:
    ensure_dirs()
    df = load_normalized()
    df = df.assign(state=classify_states(df))
    valid = df[df["preflight_pass"]].copy()
    pc = valid["collision_probability"]
    d = valid["predicted_miss_distance"]
    h = valid["combined_hard_body_radius"]

    dangerous = valid[valid["state"] == "Dangerous"].sort_values(
        "collision_probability", ascending=False, kind="mergesort")

    result = {
        "status": "PASS",
        "dangerous_count": int(len(dangerous)),
        "theta_M": THETA_M,
    }

    if len(dangerous) > 0:
        top = dangerous.head(TOP_N)
        export = pd.DataFrame({
            "event_id": top["event_id"],
            "pc": top["collision_probability"],
            "d_km": top["predicted_miss_distance"],
            "h_km": top["combined_hard_body_radius"],
            "d_over_h": top["predicted_miss_distance"] / top["combined_hard_body_radius"],
            "object1_id": top["object1_id"],
            "object2_id": top["object2_id"],
        })
        out_csv = RESULTS / "dangerous_top20.csv"
        export.to_csv(out_csv, index=False, float_format="%.10g")

        # --- end-to-end verification against the raw files ----------------
        raw = load_sfsh().set_index("conj_id")
        hbr_lookup = load_hbr_map().set_index("catalog_num")["hbr_m"]
        checks = []
        for row in top.itertuples(index=False):
            src = raw.loc[row.event_id]
            ok_raw_pc = bool(np.isclose(src["prob"], row.collision_probability,
                                        rtol=0, atol=1e-300))
            ok_raw_d = bool(np.isclose(src["min_range"], row.predicted_miss_distance,
                                       rtol=0, atol=1e-12))
            h_expected = (hbr_lookup.get(row.object1_id, np.nan)
                          + hbr_lookup.get(row.object2_id, np.nan)) / 1000.0
            ok_hbr = bool(np.isfinite(h_expected)
                          and np.isclose(h_expected, row.combined_hard_body_radius,
                                         rtol=0, atol=1e-12))
            ok_units = bool(row.combined_hard_body_radius > 0
                            and row.predicted_miss_distance >= 0
                            and 0.0 <= row.collision_probability <= 1.0)
            ok_rule = bool(row.collision_probability > THETA_M
                           and row.predicted_miss_distance
                           < row.combined_hard_body_radius)
            checks.append({
                "event_id": int(row.event_id),
                "raw_row_exists": True,
                "pc_matches_raw": ok_raw_pc,
                "min_range_matches_raw": ok_raw_d,
                "hbr_join_reverified": ok_hbr,
                "units_plausible": ok_units,
                "r8_condition_holds": ok_rule,
            })
        all_ok = all(all(v for k, v in c.items() if k != "event_id")
                     for c in checks)
        result.update({
            "top20_csv": rel(out_csv),
            "top20_verification": checks,
            "top20_all_verified": all_ok,
            "conclusion": "Dangerous instances are REAL (verified against raw "
                          "files, HBR join, and unit conversions)"
            if all_ok else
            "Dangerous instances FAILED verification - treat as adapter "
            "artifact until resolved",
        })
        if not all_ok:
            result["status"] = "FAIL"
    else:
        # Cause decomposition over valid rows; no fabrication, no rule edits.
        close = d < h
        high = pc > THETA_M
        result["cause_analysis"] = {
            "rows_d_lt_h": int(close.sum()),
            "rows_pc_gt_theta_M": int(high.sum()),
            "rows_d_lt_h_and_pc_le_theta_M": int((close & ~high).sum()),
            "rows_pc_gt_theta_M_and_d_ge_h": int((high & ~close).sum()),
            "rows_pc_gt_theta_M_and_d_lt_h": int((high & close).sum()),
            "max_pc_among_d_lt_h": float(pc[close].max()) if close.any() else None,
            "min_d_over_h_among_high_pc": float((d[high] / h[high]).min())
            if high.any() else None,
            "min_d_over_h_overall": float((d / h).min()),
        }
        ca = result["cause_analysis"]
        reasons = []
        if ca["rows_d_lt_h"] == 0:
            reasons.append("no row satisfies d < h(e): every published "
                           "conjunction has a miss distance at or above the "
                           "combined hard-body radius")
        if ca["rows_d_lt_h"] > 0 and ca["rows_pc_gt_theta_M_and_d_lt_h"] == 0:
            reasons.append("d < h(e) rows exist but all have Pc <= 1e-4 "
                           "(max Pc among them: "
                           f"{ca['max_pc_among_d_lt_h']:.3e})")
        if ca["rows_pc_gt_theta_M"] > 0 and ca["rows_pc_gt_theta_M_and_d_lt_h"] == 0:
            reasons.append("high-Pc rows exist but all have d >= h(e) "
                           "(min d/h among them: "
                           f"{ca['min_d_over_h_among_high_pc']:.3e})")
        result["conclusion"] = "; ".join(reasons) if reasons else "unresolved"

    save_json(RESULTS / "dangerous_analysis.json", result)
    print(json.dumps({"status": result["status"],
                      "dangerous_count": result["dangerous_count"]},
                     ensure_ascii=False))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
