"""06 - Internal ESA vs TraCSS comparison (read-only on the ESA side).

Recomputes the ESA-side quantities from the ESA processed CSV and asserts
they equal the pinned ESA risk_state_distribution.json before comparing,
so a stale or drifted ESA artifact fails loudly instead of silently
entering the comparison.  The comparison table is internal working
material; it is not written into the paper.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from common import (
    RESULTS, THETA_M, WORKSPACE, classify_states, ensure_dirs,
    load_normalized, rel, save_json,
)

ESA_PROCESSED = WORKSPACE / "data" / "esa_cdm" / "processed" / "esa_train_normalized.csv.gz"
ESA_PINNED = WORKSPACE / "experiments" / "esa_cdm" / "results" / "risk_state_distribution.json"


def esa_side() -> dict:
    df = pd.read_csv(ESA_PROCESSED, low_memory=False)
    valid = df[df["preflight_pass"]]
    pc = valid["pc"]
    d = valid["miss_distance_km"]
    h = valid["hbr_km"]
    counts = valid["state"].value_counts()
    recomputed = {name: int(counts.get(name, 0))
                  for name in ("Normal", "Attention", "Warning", "Dangerous")}
    pinned = json.loads(ESA_PINNED.read_text(encoding="utf-8"))
    pinned_counts = {name: int(pinned["states"][name]["count"])
                     for name in recomputed}
    return {
        "samples": int(len(valid)),
        "conjunctions": int(valid["event_key"].nunique()),
        "states": recomputed,
        "d_lt_h": int((d < h).sum()),
        "pc_gt_1e_4": int((pc > THETA_M).sum()),
        "pc_gt_1e_4_and_d_lt_h": int(((pc > THETA_M) & (d < h)).sum()),
        "pinned_state_counts": pinned_counts,
        "recomputed_equals_pinned": recomputed == pinned_counts,
        "source": rel(ESA_PROCESSED),
    }


def tracss_side() -> dict:
    df = load_normalized()
    df = df.assign(state=classify_states(df))
    valid = df[df["preflight_pass"]]
    pc = valid["collision_probability"]
    d = valid["predicted_miss_distance"]
    h = valid["combined_hard_body_radius"]
    counts = valid["state"].value_counts()
    return {
        "samples": int(len(valid)),
        "conjunctions": int(valid["event_id"].nunique()),
        "unique_object_pairs": int(pd.MultiIndex.from_arrays(
            [valid["object1_id"], valid["object2_id"]]).nunique()),
        "unique_objects": int(pd.concat(
            [valid["object1_id"], valid["object2_id"]]).nunique()),
        "states": {name: int(counts.get(name, 0))
                   for name in ("Normal", "Attention", "Warning", "Dangerous")},
        "d_lt_h": int((d < h).sum()),
        "pc_gt_1e_4": int((pc > THETA_M).sum()),
        "pc_gt_1e_4_and_d_lt_h": int(((pc > THETA_M) & (d < h)).sum()),
    }


def main() -> None:
    ensure_dirs()
    esa = esa_side()
    tracss = tracss_side()
    rows = [
        ("samples", esa["samples"], tracss["samples"]),
        ("conjunctions", esa["conjunctions"], tracss["conjunctions"]),
        ("Normal", esa["states"]["Normal"], tracss["states"]["Normal"]),
        ("Attention", esa["states"]["Attention"], tracss["states"]["Attention"]),
        ("Warning", esa["states"]["Warning"], tracss["states"]["Warning"]),
        ("Dangerous", esa["states"]["Dangerous"], tracss["states"]["Dangerous"]),
        ("d_lt_h", esa["d_lt_h"], tracss["d_lt_h"]),
        ("pc_gt_1e_4", esa["pc_gt_1e_4"], tracss["pc_gt_1e_4"]),
        ("pc_gt_1e_4_and_d_lt_h", esa["pc_gt_1e_4_and_d_lt_h"],
         tracss["pc_gt_1e_4_and_d_lt_h"]),
    ]
    table_md = [
        "| Item | ESA | TraCSS |",
        "| --- | ---: | ---: |",
        *[f"| {name} | {a} | {b} |" for name, a, b in rows],
    ]
    result = {
        "status": "PASS" if esa["recomputed_equals_pinned"] else "FAIL",
        "esa": esa,
        "tracss": tracss,
        "table_md": "\n".join(table_md),
        "note": "Internal comparison only; not written into the paper. ESA "
                "samples are CDM snapshots (multiple per event), TraCSS "
                "samples are unique conjunctions (one row per conjunction).",
    }
    save_json(RESULTS / "esa_tracss_comparison.json", result)
    print(json.dumps({"status": result["status"],
                      "esa_recomputed_equals_pinned": esa["recomputed_equals_pinned"]},
                     ensure_ascii=False))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
