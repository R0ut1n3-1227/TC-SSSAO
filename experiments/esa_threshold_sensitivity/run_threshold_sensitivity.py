"""Threshold sensitivity experiment for the R5--R8 risk-state rules (read-only).

Purpose
-------
Vary ONLY the two deployment threshold parameters of the collision-risk
situation rules and measure how the four-state distribution reacts:

  theta_A  (onto:attentionPcThreshold,  baseline 1E-7)
  theta_M  (onto:mitigationPcThreshold, baseline 1E-4)

Fidelity guarantees
-------------------
* No existing project file is modified.  All outputs go to
  experiments/esa_threshold_sensitivity/outputs/.
* The classification engine is the project's own execution-layer
  implementation, ``experiments/esa_cdm/scripts/common.py::classify_states``,
  used verbatim.  Only the two module-level deployment constants
  ``common.THETA_A`` / ``common.THETA_M`` are overridden *in memory* per run
  (they are deployment configuration parameters by design; they mirror
  onto:attentionPcThreshold / onto:mitigationPcThreshold in
  rules/tc_sssao_rule_config.ttl, which is likewise meant to be set at
  deployment time).  The original values are restored after every run.
* The baseline run is cross-validated against the locked official result
  experiments/esa_cdm/results/risk_state_distribution.json; the experiment
  aborts if the reproduction differs.
* Every parameter combination is additionally checked with an *independent*
  mask-based partition audit (overlap / gap / multi-assignment /
  unclassified), recomputed from scratch rather than via the engine.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ESA_SCRIPTS = HERE.parent / "esa_cdm" / "scripts"
sys.path.insert(0, str(ESA_SCRIPTS))

import common  # noqa: E402  (project execution layer, used unchanged)

OUT = HERE / "outputs"
STATES = ("Normal", "Attention", "Warning", "Dangerous")
BASELINE_JSON = common.RESULTS / "risk_state_distribution.json"
BASE_TA, BASE_TM = 1e-7, 1e-4

EXP_A_THETA_A = [1e-9, 1e-8, 1e-7, 1e-6, 1e-5]           # theta_M fixed at 1e-4
EXP_B_THETA_M = [1e-6, 1e-5, 1e-4, 1e-3, 1e-2]           # theta_A fixed at 1e-7
EXP_C_THETA_A = [1e-8, 1e-7, 1e-6]
EXP_C_THETA_M = [1e-5, 1e-4, 1e-3]


def fmt(x: float) -> str:
    return f"{x:.0e}"


def classify_with(df: pd.DataFrame, ta: float, tm: float) -> pd.Series:
    """Official execution-layer classifier with deployment thresholds overridden in memory."""
    orig_a, orig_m = common.THETA_A, common.THETA_M
    try:
        common.THETA_A = float(ta)
        common.THETA_M = float(tm)
        return common.classify_states(df)
    finally:
        common.THETA_A, common.THETA_M = orig_a, orig_m


def independent_partition_audit(df: pd.DataFrame, ta: float, tm: float) -> dict:
    """Recompute the four masks from scratch and check the partition property."""
    valid = df["preflight_pass"].astype(bool).to_numpy()
    pc = df["pc"].to_numpy(dtype=float)
    d = df["miss_distance_km"].to_numpy(dtype=float)
    h = df["hbr_km"].to_numpy(dtype=float)
    far = d >= h
    masks = {
        "Normal": valid & (pc <= ta) & far,
        "Attention": valid & (pc > ta) & (pc <= tm) & far,
        "Warning": valid & (((pc > tm) & far) | ((pc <= tm) & ~far)),
        "Dangerous": valid & (pc > tm) & ~far,
    }
    keys = list(masks)
    overlap = 0
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            overlap += int((masks[keys[i]] & masks[keys[j]]).sum())
    union = masks["Normal"] | masks["Attention"] | masks["Warning"] | masks["Dangerous"]
    return {
        "counts": {k: int(v.sum()) for k, v in masks.items()},
        "valid_total": int(valid.sum()),
        "union_covered": int(union.sum()),
        "uncovered_valid": int((valid & ~union).sum()),
        "pairwise_overlap_assignments": overlap,
    }


def run_combo(df: pd.DataFrame, ta: float, tm: float, base_states: pd.Series,
              base_counts: dict[str, int]) -> dict:
    states = classify_with(df, ta, tm)
    valid = df["preflight_pass"].astype(bool)
    vc = states[valid].value_counts()
    counts = {name: int(vc.get(name, 0)) for name in STATES}
    total = int(valid.sum())
    audit = independent_partition_audit(df, ta, tm)
    changed = (states[valid].astype("string") != base_states[valid].astype("string")).to_numpy()
    event_keys = df.loc[valid, "event_key"].astype(str).to_numpy()
    return {
        "theta_A": ta,
        "theta_M": tm,
        "total_valid_cdms": total,
        "counts": counts,
        "ratios": {k: (counts[k] / total if total else 0.0) for k in STATES},
        "delta_vs_baseline": {k: counts[k] - base_counts[k] for k in STATES},
        "changed_cdms_vs_baseline": int(changed.sum()),
        "changed_cdm_ratio_vs_baseline": float(changed.sum() / total) if total else 0.0,
        "changed_events_vs_baseline": int(pd.unique(event_keys[changed]).size),
        "audit": {
            "no_state_engine": int(states[valid].isna().sum()),
            "sum_states_equals_total": int(sum(counts.values())) == total,
            "engine_matches_independent_audit": audit["counts"] == counts,
            "uncovered_valid": audit["uncovered_valid"],
            "pairwise_overlap_assignments": audit["pairwise_overlap_assignments"],
            "theta_order_ok": bool(ta < tm),
        },
    }


def pc_diagnosis(df: pd.DataFrame) -> dict:
    valid = df["preflight_pass"].astype(bool)
    v = df.loc[valid]
    pc = v["pc"].astype(float)
    d = v["miss_distance_km"].astype(float)
    h = v["hbr_km"].astype(float)
    close = d < h
    high = pc > BASE_TM
    out = {
        "valid_cdms": int(valid.sum()),
        "valid_events": int(v["event_key"].astype(str).nunique()),
        "pc_min": float(pc.min()),
        "pc_max": float(pc.max()),
        "pc_median": float(pc.median()),
        "pc_mean": float(pc.mean()),
        "pc_p90": float(pc.quantile(0.90)),
        "pc_p95": float(pc.quantile(0.95)),
        "pc_p99": float(pc.quantile(0.99)),
    }
    for thr in (1e-7, 1e-6, 1e-5, 1e-4, 1e-3):
        out[f"count_pc_gt_{fmt(thr)}"] = int((pc > thr).sum())
    out["count_close_d_lt_h"] = int(close.sum())
    out["ratio_close_d_lt_h"] = float(close.mean())
    out["joint_pc_gt_1e-04_and_close"] = int((high & close).sum())
    out["pc_gt_1e-04_and_not_close"] = int((high & ~close).sum())
    out["pc_le_1e-04_and_close"] = int((~high & close).sum())
    out["max_pc_among_close"] = float(pc[close].max()) if bool(close.any()) else None
    out["max_pc_among_not_close"] = float(pc[~close].max()) if bool((~close).any()) else None
    if bool(high.any()):
        margin = (d - h)[high.to_numpy()]
        out["min_distance_margin_km_among_pc_gt_1e-04"] = float(margin.min())
        out["min_d_over_h_among_pc_gt_1e-04"] = float((d / h)[high.to_numpy()].min())
    # Dangerous count as a pure function of theta_M (theta_A plays no role in R8)
    out["dangerous_count_vs_thetaM"] = {
        fmt(tm): int(((pc > tm) & close).sum())
        for tm in [1e-7, 1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1]
    }
    return out


def float_semantics_probe() -> dict:
    """Document the numeric semantics of the SHACL engine used by the 50-event RDF gate."""
    from rdflib import Literal
    from rdflib.namespace import XSD

    lit = Literal("1.0E-7", datatype=XSD.float)
    val = lit.toPython()
    return {
        "rdflib_xsd_float_toPython_type": type(val).__name__,
        "rdflib_xsd_float_value_repr": repr(val),
        "note": (
            "rdflib maps xsd:float literals and xsd:float() casts to Python float "
            "(IEEE 754 double), so the SHACL gate in 04_build_rdf.py and the pandas "
            "execution layer both evaluate the R5--R8 comparisons in float64."
        ),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = common.load_processed()

    # --- sanity: imported constants are the official deployment values -------
    assert common.THETA_A == BASE_TA and common.THETA_M == BASE_TM, (
        f"common.py constants changed: THETA_A={common.THETA_A}, THETA_M={common.THETA_M}"
    )

    # --- baseline reproduction + cross-validation against the locked JSON ----
    base_states = classify_with(df, BASE_TA, BASE_TM)
    valid = df["preflight_pass"].astype(bool)
    vc = base_states[valid].value_counts()
    base_counts = {name: int(vc.get(name, 0)) for name in STATES}
    official = json.loads(BASELINE_JSON.read_text(encoding="utf-8"))
    official_counts = {k: int(v["count"]) for k, v in official["states"].items()}
    stored_vc = df.loc[valid, "state"].value_counts()
    stored_counts = {name: int(stored_vc.get(name, 0)) for name in STATES}
    baseline_check = {
        "recomputed_counts": base_counts,
        "official_json_counts": official_counts,
        "stored_state_column_counts": stored_counts,
        "matches_official_json": base_counts == official_counts,
        "matches_state_column": base_counts == stored_counts,
        "official_theta_A": official["theta_A"],
        "official_theta_M": official["theta_M"],
    }
    if not (baseline_check["matches_official_json"] and baseline_check["matches_state_column"]):
        save = OUT / "threshold_sensitivity_results.json"
        save.write_text(json.dumps({"baseline_check": baseline_check}, indent=2), encoding="utf-8")
        raise SystemExit(f"Baseline reproduction mismatch, aborting. See {save}")

    # --- experiment runs ------------------------------------------------------
    combos: dict[tuple[float, float], dict] = {}

    def ensure(ta: float, tm: float) -> dict:
        key = (float(ta), float(tm))
        if key not in combos:
            combos[key] = run_combo(df, ta, tm, base_states, base_counts)
        return combos[key]

    exp_a = [ensure(ta, BASE_TM) for ta in EXP_A_THETA_A]
    exp_b = [ensure(BASE_TA, tm) for tm in EXP_B_THETA_M]
    exp_c = [ensure(ta, tm) for ta in EXP_C_THETA_A for tm in EXP_C_THETA_M]

    results = {
        "experiment": "R5-R8 risk-state threshold sensitivity (theta_A, theta_M)",
        "dataset": {
            "processed_csv": common.PROCESSED_CSV.relative_to(ROOT).as_posix(),
            "rows": int(len(df)),
            "valid_cdms": int(valid.sum()),
            "events": int(df["event_key"].astype(str).nunique()),
        },
        "engine": {
            "module": "experiments/esa_cdm/scripts/common.py::classify_states",
            "official_constants": {"THETA_A": BASE_TA, "THETA_M": BASE_TM},
            "override": "in-memory only; no project file modified",
            "float_semantics": float_semantics_probe(),
        },
        "baseline_check": baseline_check,
        "baseline": ensure(BASE_TA, BASE_TM),
        "experiment_A_theta_A_sweep": exp_a,
        "experiment_B_theta_M_sweep": exp_b,
        "experiment_C_joint_grid": exp_c,
        "pc_distance_diagnosis": pc_diagnosis(df),
        "unique_combos_run": len(combos),
    }
    out_json = OUT / "threshold_sensitivity_results.json"
    out_json.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    # compact stdout summary
    def row(r: dict) -> str:
        c = r["counts"]
        return (f"thetaA={fmt(r['theta_A']):>6} thetaM={fmt(r['theta_M']):>6} | "
                f"N={c['Normal']:>7} A={c['Attention']:>7} W={c['Warning']:>5} D={c['Dangerous']:>4} | "
                f"changed={r['changed_cdms_vs_baseline']:>7} "
                f"({100.0 * r['changed_cdm_ratio_vs_baseline']:6.3f}%)")

    print("BASELINE CHECK:", baseline_check["matches_official_json"], baseline_check["matches_state_column"])
    print("== A: theta_A sweep (theta_M=1e-4) ==")
    for r in exp_a:
        print(row(r))
    print("== B: theta_M sweep (theta_A=1e-7) ==")
    for r in exp_b:
        print(row(r))
    print("== C: joint 3x3 ==")
    for r in exp_c:
        print(row(r))
    print("== diagnosis ==")
    print(json.dumps(results["pc_distance_diagnosis"], indent=2))
    print(f"Wrote {out_json}")


if __name__ == "__main__":
    main()
