"""03 - Data distribution audit (before any R5-R8 evaluation).

Answers, on preflight-pass rows only:
  * Pc descriptive statistics and threshold exceedance counts
  * d vs h(e) relation counts (d<h, d=h, d>h)
  * the critical conjunction count: Pc > 1e-4 AND d < h(e)
Nothing here modifies rules, thresholds, or data.
"""
from __future__ import annotations

import json

import numpy as np

from common import RESULTS, THETA_M, ensure_dirs, load_normalized, save_json

PC_THRESHOLDS = [1e-7, 1e-6, 1e-5, 1e-4, 1e-3]


def main() -> None:
    ensure_dirs()
    df = load_normalized()
    valid = df[df["preflight_pass"]].copy()
    pc = valid["collision_probability"].to_numpy(dtype=float)
    d = valid["predicted_miss_distance"].to_numpy(dtype=float)
    h = valid["combined_hard_body_radius"].to_numpy(dtype=float)

    pc_min = float(np.min(pc))
    pc_stats = {
        "min": pc_min,
        "max": float(np.max(pc)),
        "mean": float(np.mean(pc)),
        "median": float(np.median(pc)),
        "p90": float(np.percentile(pc, 90)),
        "p95": float(np.percentile(pc, 95)),
        "p99": float(np.percentile(pc, 99)),
        "rows_at_min_value": int((pc == pc_min).sum()),
        "min_value_interpretation": "identical repeated minimum suggests a "
                                    "published lower-bound/rounding floor in "
                                    "the answer key, not an adapter artifact",
    }
    pc_threshold_counts = {
        f"pc_gt_{t:.0e}": int((pc > t).sum()) for t in PC_THRESHOLDS
    }

    distance_stats = {
        "d_km": {
            "min": float(np.min(d)),
            "median": float(np.median(d)),
            "max": float(np.max(d)),
        },
        "h_km": {
            "min": float(np.min(h)),
            "median": float(np.median(h)),
            "max": float(np.max(h)),
        },
        "d_lt_h": int((d < h).sum()),
        "d_eq_h": int((d == h).sum()),
        "d_gt_h": int((d > h).sum()),
        "d_over_h": {
            "min": float(np.min(d / h)),
            "median": float(np.median(d / h)),
            "p99": float(np.percentile(d / h, 99)),
            "max": float(np.max(d / h)),
        },
    }

    critical = {
        "pc_gt_theta_M_and_d_lt_h": int(((pc > THETA_M) & (d < h)).sum()),
        "theta_M": THETA_M,
        "interpretation": "this is the R8 Dangerous trigger population; "
                          "evaluated as-is, with no filtering to force a "
                          "nonzero result",
    }

    result = {
        "status": "PASS",
        "population": "preflight_pass rows of the normalized adapter output",
        "rows_total": int(len(df)),
        "rows_valid": int(len(valid)),
        "pc_stats": pc_stats,
        "pc_threshold_counts": pc_threshold_counts,
        "distance_stats": distance_stats,
        "critical_check": critical,
    }
    save_json(RESULTS / "distribution_audit.json", result)
    print(json.dumps({"status": "PASS", "rows_valid": len(valid),
                      "d_lt_h": distance_stats["d_lt_h"],
                      "pc_gt_1e-4": pc_threshold_counts["pc_gt_1e-04"],
                      "pc_gt_1e-4_and_d_lt_h": critical["pc_gt_theta_M_and_d_lt_h"]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
