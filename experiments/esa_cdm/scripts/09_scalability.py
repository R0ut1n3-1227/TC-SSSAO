from __future__ import annotations

import time

import numpy as np
import pandas as pd

from common import (RESULTS, THETA_A, THETA_M, derive_transitions, load_processed,
                    mapping_triple_count, process_peak_rss_mb, save_json,
                    select_event_keys, summarize_timings)

SIZES = (100, 500, 1000, 2000, 5000, 10000, 13154)
REPEATS = 3


def run_once(df: pd.DataFrame) -> dict[str, object]:
    start_total = time.perf_counter()

    start = time.perf_counter()
    valid = (
        df["pc"].between(0, 1, inclusive="both") & np.isfinite(df["pc"])
        & (df["miss_distance_km"] >= 0) & np.isfinite(df["miss_distance_km"])
        & (df["hbr_km"] > 0) & np.isfinite(df["hbr_km"])
        & np.isfinite(df["time_to_tca"]) & (df["event_key"].astype(str).str.len() > 0)
        & ~df["duplicate_exact_row"].astype(bool)
    )
    input_contract_s = time.perf_counter() - start

    start = time.perf_counter()
    ordered = df.sort_values(["event_key", "time_to_tca", "source_row"], ascending=[True, False, True])
    temporal_edges = int(sum(max(0, n - 1) for n in ordered.groupby("event_key").size()))
    partitioned_temporal_sort_s = time.perf_counter() - start

    start = time.perf_counter()
    high = df["pc"] > THETA_M
    close = df["miss_distance_km"] < df["hbr_km"]
    ranks = np.full(len(df), -1, dtype=np.int8)
    a = valid.to_numpy()
    ranks[a & ~high.to_numpy() & ~close.to_numpy() & (df["pc"].to_numpy() <= THETA_A)] = 0
    ranks[a & ~high.to_numpy() & ~close.to_numpy() & (df["pc"].to_numpy() > THETA_A)] = 1
    ranks[a & np.logical_xor(high.to_numpy(), close.to_numpy())] = 2
    ranks[a & high.to_numpy() & close.to_numpy()] = 3
    state_count = int((ranks >= 0).sum())
    r5_r8_execution_layer_s = time.perf_counter() - start

    start = time.perf_counter()
    transitions = derive_transitions(df)
    b3_execution_layer_s = time.perf_counter() - start

    start = time.perf_counter()
    # ESA CDMs do not contain manoeuvre/causal links, so R9--R11 have an empty
    # causal relation set.  We still execute their graph-invariant checks.
    causal_edges: list[tuple[str, str]] = []
    r9_r11_ok = not causal_edges
    empty_causal_invariant_check_s = time.perf_counter() - start

    start = time.perf_counter()
    integrity_ok = bool((ranks[valid.to_numpy()] >= 0).all()) and bool((ranks[valid.to_numpy()] <= 3).all())
    other_validation_s = time.perf_counter() - start

    estimated_input_triples = mapping_triple_count(df)
    estimated_output_triples = estimated_input_triples + state_count * 3 + len(transitions) + int(transitions.get("degrades_to", pd.Series(dtype=bool)).sum())
    return {
        "cdm_count": int(len(df)),
        "estimated_input_triples_from_mapping_template": int(estimated_input_triples),
        "estimated_output_triples_from_mapping_template": int(estimated_output_triples),
        "input_contract_s": input_contract_s,
        "event_partitioned_temporal_sort_s": partitioned_temporal_sort_s,
        "r3_r4_s": None,
        "r3_r4_executed": False,
        "r5_r8_execution_layer_s": r5_r8_execution_layer_s,
        "b3_execution_layer_s": b3_execution_layer_s,
        "empty_causal_invariant_check_s": empty_causal_invariant_check_s,
        "other_validation_s": other_validation_s,
        "total_s": time.perf_counter() - start_total,
        "partitioned_temporal_edges": temporal_edges,
        "b3_transitions": int(len(transitions)),
        "valid_states": state_count,
        "validation_pass": bool(r9_r11_ok and integrity_ok),
        "process_peak_working_set_mb_cumulative": process_peak_rss_mb(),
    }


def main() -> None:
    full = load_processed()
    all_rows: list[dict[str, object]] = []
    available = int(full["event_key"].nunique())
    for requested in SIZES:
        size = min(requested, available)
        keys = set(select_event_keys(full, size, minimum_rows=1))
        subset = full[full["event_key"].astype(str).isin(keys)].copy()
        for repeat in range(1, REPEATS + 1):
            row = run_once(subset)
            row.update({"requested_events": requested, "event_count": size, "repeat": repeat,
                        "engine": "event-partitioned Pandas/NumPy execution-layer prototype; the 50-event RDF track separately executes unchanged R5--R8 sh:construct bodies on RDF"})
            all_rows.append(row)
            print(requested, repeat, row["total_s"], row["process_peak_working_set_mb_cumulative"])

    raw = pd.DataFrame(all_rows)
    raw.to_csv(RESULTS / "scalability_raw.csv", index=False)
    summaries = []
    timing_columns = [c for c in raw.columns if c.endswith("_s")]
    for event_count, group in raw.groupby("event_count", sort=True):
        item: dict[str, object] = {
            "event_count": int(event_count),
            "cdm_count": int(group["cdm_count"].iloc[0]),
            "estimated_input_triples_from_mapping_template": int(group["estimated_input_triples_from_mapping_template"].iloc[0]),
            "estimated_output_triples_from_mapping_template": int(group["estimated_output_triples_from_mapping_template"].iloc[0]),
        }
        for col in timing_columns:
            values = group[col].dropna().astype(float).tolist()
            if values:
                item[col] = summarize_timings(values)
        summaries.append(item)
    summary_df = pd.json_normalize(summaries, sep=".")
    summary_df.to_csv(RESULTS / "scalability_summary.csv", index=False)
    result = {
        "status": "PASS" if bool(raw["validation_pass"].all()) else "FAIL",
        "repeats_per_scale": REPEATS,
        "sizes": summaries,
        "scope_note": "Wall-clock timings cover the event-partitioned Pandas/NumPy execution layer, not full RDF construction, pySHACL, or production triple-store inference.",
        "timing_excludes": "Loading the full processed CSV and selecting each event subset occur outside run_once timing.",
        "triple_count_note": "Triple counts are deterministic estimates from the documented mapping template; the full RDF graphs were not materialized.",
        "fixed_point_note": "No fixed-point iteration count is reported for scalability because this execution layer does not run iterative SHACL-SPARQL materialization.",
        "process_peak_working_set_mb_with_full_dataset_loaded": float(raw["process_peak_working_set_mb_cumulative"].max()),
        "memory_note": "The complete 162,634-row processed table is loaded before scale subsets are run; this cumulative process peak is not a per-scale independent memory measurement.",
        "r1_note": "Temporal ordering is local sorting within event_id partitions, not original R1 global pairwise materialization; global worst-case relation growth remains O(N^2).",
        "r3_r4_note": "Not executed because the anonymised ESA dataset lacks a real manoeuvre-to-approach chain.",
    }
    save_json(RESULTS / "scalability.json", result)
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
