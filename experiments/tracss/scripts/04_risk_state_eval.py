"""04 - Run the frozen R5-R8 classification on the TraCSS adapter output.

Thresholds are the formal parameters (THETA_A = 1e-7, THETA_M = 1e-4) and
the rule semantics are unchanged.  As a semantic lock, this script also
loads the ESA experiment's own classify_states (read-only import) and
verifies that both implementations assign identical states on every row,
and that the four rule masks form an exact partition of the valid rows
(no overlap, no gap, N = sum of state counts).
"""
from __future__ import annotations

import importlib.util
import json

import numpy as np
import pandas as pd

from common import (
    RESULTS, THETA_A, THETA_M, WORKSPACE, classify_states, ensure_dirs,
    load_normalized, save_json,
)

ESA_COMMON = WORKSPACE / "experiments" / "esa_cdm" / "scripts" / "common.py"


def load_esa_classify():
    spec = importlib.util.spec_from_file_location("esa_common", ESA_COMMON)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    ensure_dirs()
    df = load_normalized()
    state = classify_states(df)
    df = df.assign(state=state)
    valid = df[df["preflight_pass"]]

    counts = valid["state"].value_counts(dropna=False)
    states = {}
    for name in ("Normal", "Attention", "Warning", "Dangerous"):
        count = int(counts.get(name, 0))
        states[name] = {"count": count,
                        "ratio": count / len(valid) if len(valid) else 0.0}
    n_valid = int(len(valid))
    n_sum = int(sum(s["count"] for s in states.values()))
    no_state = int(valid["state"].isna().sum())

    # --- exact-partition audit over the four raw rule masks ----------------
    pc = valid["collision_probability"]
    d = valid["predicted_miss_distance"]
    h = valid["combined_hard_body_radius"]
    masks = {
        "R5_Normal": (pc <= THETA_A) & (d >= h),
        "R6_Attention": (pc > THETA_A) & (pc <= THETA_M) & (d >= h),
        "R7_Warning": ((pc > THETA_M) & (d >= h)) | ((pc <= THETA_M) & (d < h)),
        "R8_Dangerous": (pc > THETA_M) & (d < h),
    }
    mask_frame = pd.DataFrame(masks)
    hits = mask_frame.sum(axis=1)
    overlap = int((hits > 1).sum())
    gap = int((hits == 0).sum())
    # mask counts must equal the classifier's state counts
    mask_count_mismatch = {
        name: int(mask.sum())
        for name, mask in masks.items()
        if int(mask.sum()) != states[name.split("_", 1)[1]]["count"]
    }

    # --- semantic lock against the ESA implementation ----------------------
    cross_check = {"esa_common_found": ESA_COMMON.exists()}
    if ESA_COMMON.exists():
        esa = load_esa_classify()
        cross_check["theta_A_equal"] = bool(esa.THETA_A == THETA_A)
        cross_check["theta_M_equal"] = bool(esa.THETA_M == THETA_M)
        alias = pd.DataFrame({
            "pc": df["collision_probability"],
            "miss_distance_km": df["predicted_miss_distance"],
            "hbr_km": df["combined_hard_body_radius"],
            "preflight_pass": df["preflight_pass"],
        })
        esa_state = esa.classify_states(alias)
        both_na = esa_state.isna() & df["state"].isna()
        equal = ((esa_state == df["state"]) | both_na).all()
        cross_check["states_identical_all_rows"] = bool(equal)
        cross_check["mismatch_rows"] = int((~((esa_state == df["state"]) | both_na)).sum())
    else:
        cross_check.update({"theta_A_equal": None, "theta_M_equal": None,
                            "states_identical_all_rows": None, "mismatch_rows": None})

    partition_ok = (
        no_state == 0 and overlap == 0 and gap == 0 and n_sum == n_valid
        and not mask_count_mismatch
    )
    semantic_ok = (
        cross_check.get("states_identical_all_rows") is True
        and cross_check.get("theta_A_equal") and cross_check.get("theta_M_equal")
    )
    result = {
        "status": "PASS" if partition_ok and semantic_ok else "FAIL",
        "theta_A": THETA_A,
        "theta_M": THETA_M,
        "rows_total": int(len(df)),
        "classified_rows": n_valid,
        "excluded_by_preflight": int((~df["preflight_pass"]).sum()),
        "states": states,
        "state_sum_equals_n": n_sum == n_valid,
        "no_state": no_state,
        "multi_state": overlap,
        "rule_mask_overlap": overlap,
        "rule_mask_gap": gap,
        "mask_count_mismatch": mask_count_mismatch,
        "esa_semantic_cross_check": cross_check,
        "note": "States are TC-SSSAO knowledge-organization states, not "
                "TraCSS/CSieve operational labels. Semantics and thresholds "
                "are frozen and identical to the ESA experiment.",
    }
    save_json(RESULTS / "risk_state_distribution.json", result)
    print(json.dumps({"status": result["status"],
                      "Normal": states["Normal"]["count"],
                      "Attention": states["Attention"]["count"],
                      "Warning": states["Warning"]["count"],
                      "Dangerous": states["Dangerous"]["count"],
                      "overlap": overlap, "gap": gap}, ensure_ascii=False))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
