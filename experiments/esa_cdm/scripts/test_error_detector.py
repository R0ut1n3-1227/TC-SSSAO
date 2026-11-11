"""Synthetic test proving the 10-category (11-counter) error detector catches
all bad edges.

The detector in common.state_evolution_metrics() implements 10 error
categories; category 7 is split into two counters (7a mismatch_predicate,
7b mismatch_predicate2), giving 11 err_* counters.  Each case below injects
exactly one bad edge into a synthetic transitions DataFrame and asserts the
FULL counter vector — not just the target counter — so every firing (and
every non-firing) is pinned.

Some categories are coupled BY CONSTRUCTION (a single bad edge necessarily
violates more than one); these cases document and pin the exact coupled
vector instead of pretending each edge trips exactly one counter:
  - Type 3 (time_direction): adjacency is DEFINED by the time ordering, so
    a time-reversed edge is necessarily non-adjacent → also trips Type 2.
  - Types 4/7a (recovers direction / predicate mismatch): the same
    recoversTo-with-increasing-rank edge violates both wordings.
  - Types 5/7b (degrades-not-2→3): same edge, two wordings.
  - Type 6 (same-rank): built cross-event so rank stays comparable → also
    trips Type 1.
All other cases are surgically single-violation (expected vector has exactly
one counter == 1, everything else == 0).
"""
from __future__ import annotations

import pandas as pd
from pathlib import Path
import sys

# Ensure common.py in the same directory is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import state_evolution_metrics, stable_token, STATE_RANK, RANK_STATE, RESULTS

HERE = Path(__file__).resolve().parent

# The 11 detector counters, in the order returned by state_evolution_metrics()
ERROR_KEYS = [
    "err_cross_event",
    "err_within_non_adjacent",
    "err_time_direction",
    "err_recovers_direction",
    "err_degrades_warning",
    "err_transits_same_rank",
    "err_mismatch_predicate",
    "err_mismatch_predicate2",
    "err_missing_recovers_on_downgrade",
    "err_missing_degrades_on_warning_dangerous",
    "err_direction_field_inconsistent",
]


def vector_of(**kwargs):
    """Full 11-counter vector; unspecified counters default to 0."""
    vector = {k: 0 for k in ERROR_KEYS}
    for key, value in kwargs.items():
        assert key in vector, f"unknown counter {key}"
        vector[key] = value
    return vector


# ---------------------------------------------------------------------------
# Helper: build a minimal source DataFrame with controlled snapshots.
# Required columns for state_evolution_metrics / derive_transitions:
#   event_key, time_to_tca, source_row, preflight_pass, severity_rank, state, snapshot_id
# ---------------------------------------------------------------------------

def make_snapshots(event_key: str, ranks_and_times, base_row=0):
    """Return rows for one event_key.

    ranks_and_times: list of (severity_rank, time_to_tca) in the order they
    appear in the DataFrame (will be sorted by derive_transitions).
    """
    rows = []
    for offset, (rank, tca) in enumerate(ranks_and_times):
        sid = stable_token(event_key, base_row + offset)
        state_map = {0: "Normal", 1: "Attention", 2: "Warning", 3: "Dangerous"}
        rows.append({
            "event_key": event_key,
            "time_to_tca": float(tca),
            "source_row": int(base_row + offset),
            "preflight_pass": True,
            "severity_rank": int(rank),
            "state": state_map[rank],
            "snapshot_id": sid,
        })
    return rows


def build_df(all_rows):
    df = pd.DataFrame(all_rows)
    df["time_to_tca"] = df["time_to_tca"].astype(float)
    df["source_row"] = df["source_row"].astype(int)
    df["preflight_pass"] = df["preflight_pass"].astype(bool)
    df["severity_rank"] = df["severity_rank"].astype(int)
    return df


def make_transition_row(source_sid, target_sid, r1, r2, event_key="evX",
                        degrades_to=False, recovers_to=False):
    """Create a single transition row matching derive_transitions schema."""
    return {
        "event_key": str(event_key),
        "source_snapshot": str(source_sid),
        "target_snapshot": str(target_sid),
        "source_rank": int(r1),
        "target_rank": int(r2),
        "source_state": RANK_STATE[r1],
        "target_state": RANK_STATE[r2],
        "degrades_to": bool(degrades_to),
        "recovers_to": bool(recovers_to),
        "direction": "increase" if r2 > r1 else "decrease",
    }


# ---------------------------------------------------------------------------
# Build base snapshots used across multiple tests
# ---------------------------------------------------------------------------

# evA: Normal(100) -> Attention(50) -> Warning(20) -> Dangerous(10)
EV_A = make_snapshots("evA", [(0, 100.0), (1, 50.0), (2, 20.0), (3, 10.0)], base_row=0)
# Snapshot IDs
EV_A_S0 = EV_A[0]["snapshot_id"]   # Normal@100
EV_A_S1 = EV_A[1]["snapshot_id"]   # Attention@50
EV_A_S2 = EV_A[2]["snapshot_id"]   # Warning@20
EV_A_S3 = EV_A[3]["snapshot_id"]   # Dangerous@10

# evB: Normal(90) -> Attention(40)  [for cross-event test]
EV_B = make_snapshots("evB", [(0, 90.0), (1, 40.0)], base_row=10)
EV_B_S0 = EV_B[0]["snapshot_id"]
EV_B_S1 = EV_B[1]["snapshot_id"]

# evC: Normal(80) -> Attention(30)  [extra event]
EV_C = make_snapshots("evC", [(0, 80.0), (1, 30.0)], base_row=20)
EV_C_S0 = EV_C[0]["snapshot_id"]

# evD: Warning(100) -> Dangerous(50) -> Normal(10)  [genuine recovery event;
# a Dangerous→Normal downgrade edge here is ADJACENT and TIME-CONSISTENT,
# so a missing recovers_to flag is the ONLY thing wrong with it]
EV_D = make_snapshots("evD", [(2, 100.0), (3, 50.0), (0, 10.0)], base_row=30)
EV_D_S1 = EV_D[1]["snapshot_id"]   # Dangerous@50
EV_D_S2 = EV_D[2]["snapshot_id"]   # Normal@10

# Base DataFrame (evA + evB + evC)
DF_BASE = build_df(EV_A + EV_B + EV_C)
DF_D = build_df(EV_D)


# ---------------------------------------------------------------------------
# Test cases — each builds a patched transitions DataFrame plus the FULL
# expected counter vector (target counter == 1 implied by the vector)
# ---------------------------------------------------------------------------

def build_test_cases():
    cases = []

    # Type 1: cross_event — source and target have different event_keys
    # evA.Normal@100 -> evB.Attention@40 (cross-event).  Single violation.
    t1 = pd.DataFrame([make_transition_row(EV_A_S0, EV_B_S1, 0, 1, "evA")])
    cases.append(("Type 1: cross_event (different event_keys)", DF_BASE, t1,
                  "err_cross_event",
                  vector_of(err_cross_event=1)))

    # Type 2: within_non_adjacent — group_position gap of 2 (skip)
    # evA.Normal@100 (pos0) -> evA.Warning@20 (pos2), skipping Attention@50.
    # Time direction and everything else consistent.  Single violation.
    t2 = pd.DataFrame([make_transition_row(EV_A_S0, EV_A_S2, 0, 2, "evA")])
    cases.append(("Type 2: within_non_adjacent (group_position gap=2)", DF_BASE, t2,
                  "err_within_non_adjacent",
                  vector_of(err_within_non_adjacent=1)))

    # Type 3: time_direction — time_to_tca doesn't decrease.
    # evA.Normal@100 -> evA.Attention@150 (time INCREASES = wrong order).
    # COUPLED: proper adjacency is defined by the time ordering, so this
    # edge is necessarily non-adjacent (pos1 -> pos0) → also trips Type 2.
    df_t3 = build_df(EV_A + make_snapshots("evA", [(1, 150.0)], base_row=4))
    evA_attn_150 = stable_token("evA", 4)
    t3 = pd.DataFrame([{
        "event_key": "evA",
        "source_snapshot": EV_A_S0,
        "target_snapshot": evA_attn_150,
        "source_rank": 0, "target_rank": 1,
        "source_state": "Normal", "target_state": "Attention",
        "degrades_to": False, "recovers_to": False,
        "direction": "increase",
    }])
    cases.append(("Type 3: time_direction (time doesn't decrease; coupled with non-adjacency)",
                  df_t3, t3, "err_time_direction",
                  vector_of(err_time_direction=1, err_within_non_adjacent=1)))

    # Type 4/7a: recovers_direction + mismatch_predicate — recoversTo=True but
    # r1 < r2 (increase).  evA.Normal@100 -> Attention@50 with recovers_to=True.
    # COUPLED: the same edge violates both counter wordings (4 and 7a); the full
    # vector asserts both.  (A separate 7a case on the identical edge would be a
    # byte-identical duplicate and is intentionally not included.)
    t4 = pd.DataFrame([make_transition_row(EV_A_S0, EV_A_S1, 0, 1, "evA", recovers_to=True)])
    cases.append(("Type 4/7a: recovers_direction + mismatch_predicate (recovers but r1<r2; coupled)",
                  DF_BASE, t4, "err_recovers_direction",
                  vector_of(err_recovers_direction=1, err_mismatch_predicate=1)))

    # Type 5/7b: degrades_warning + mismatch_predicate2 — degradesTo=True but
    # not Warning(2)->Dangerous(3).  evA.Normal@100 -> Attention@50 with
    # degrades_to=True.  COUPLED: same edge, two counter wordings (5 and 7b).
    t5 = pd.DataFrame([make_transition_row(EV_A_S0, EV_A_S1, 0, 1, "evA", degrades_to=True)])
    cases.append(("Type 5/7b: degrades_warning + degrades_predicate_mismatch (degrades but not 2->3; coupled)",
                  DF_BASE, t5, "err_degrades_warning",
                  vector_of(err_degrades_warning=1, err_mismatch_predicate2=1)))

    # Type 6: transits_same_rank — r1 == r2.  Built cross-event
    # (evA.Normal@100 -> evC.Normal@80) so rank stays comparable.
    # COUPLED with Type 1 (cross-event).
    t6 = pd.DataFrame([make_transition_row(EV_A_S0, EV_C_S0, 0, 0, "evA")])
    cases.append(("Type 6: transits_same_rank (r1==r2; coupled with cross_event)",
                  DF_BASE, t6, "err_transits_same_rank",
                  vector_of(err_transits_same_rank=1, err_cross_event=1)))

    # Type 8: missing_recovers_on_downgrade — r1>r2 but recovers_to=False.
    # evD.Dangerous@50 -> evD.Normal@10: ADJACENT (pos1->pos2), time
    # decreases (50 -> 10), direction field consistent ("decrease") — the
    # missing recovers flag is the ONLY defect.  Single violation.
    t8 = pd.DataFrame([make_transition_row(EV_D_S1, EV_D_S2, 3, 0, "evD", recovers_to=False)])
    cases.append(("Type 8: missing_recovers_on_downgrade (r1>r2 but recovers=False; single violation)",
                  DF_D, t8, "err_missing_recovers_on_downgrade",
                  vector_of(err_missing_recovers_on_downgrade=1)))

    # Type 9: missing_degrades_on_warning_dangerous — r1=2,r2=3 but degrades_to=False.
    # evA.Warning@20 -> Dangerous@10: adjacent, time-consistent, direction
    # consistent — the missing degrades flag is the ONLY defect.  Single violation.
    t9 = pd.DataFrame([make_transition_row(EV_A_S2, EV_A_S3, 2, 3, "evA", degrades_to=False)])
    cases.append(("Type 9: missing_degrades_on_warning_dangerous (2->3 but degrades=False; single violation)",
                  DF_BASE, t9, "err_missing_degrades_on_warning_dangerous",
                  vector_of(err_missing_degrades_on_warning_dangerous=1)))

    # Type 10: direction_field_inconsistent — direction field doesn't match
    # rank change.  evA.Normal@100 -> Attention@50 (increase) but
    # direction="decrease".  Single violation.
    t10 = pd.DataFrame([{
        "event_key": "evA",
        "source_snapshot": EV_A_S0,
        "target_snapshot": EV_A_S1,
        "source_rank": 0, "target_rank": 1,
        "source_state": "Normal", "target_state": "Attention",
        "degrades_to": False, "recovers_to": False,
        "direction": "decrease",   # WRONG: should be "increase"
    }])
    cases.append(("Type 10: direction_field_inconsistent (single violation)",
                  DF_BASE, t10, "err_direction_field_inconsistent",
                  vector_of(err_direction_field_inconsistent=1)))

    return cases


# ---------------------------------------------------------------------------
# Run tests
# ---------------------------------------------------------------------------

def test_error_detector():
    """Returns (all_passed, per_case_records)."""
    cases = build_test_cases()
    records = []

    print("=" * 70)
    print(f"10-Category / {len(ERROR_KEYS)}-Counter Error Detector — Synthetic Test")
    print("=" * 70)
    print()

    for label, df, transitions_patch, error_key, expected_vector in cases:
        result = state_evolution_metrics(df, _test_transitions=transitions_patch)
        observed_vector = {k: result[k] for k in ERROR_KEYS}
        details_count = len(result.get("error_details", []))
        # Exactly 1 bad edge is injected per case: the target counter must be
        # exactly 1, the FULL vector must match the documented expectation
        # (coupled categories pinned explicitly), and error_details must
        # account for every counted error.
        passed = (observed_vector == expected_vector
                  and details_count == sum(expected_vector.values()))
        fired = {k: v for k, v in observed_vector.items() if v}
        records.append({
            "label": label,
            "target_counter": error_key,
            "observed_target": observed_vector[error_key],
            "observed_vector": observed_vector,
            "expected_vector": expected_vector,
            "error_details_count": details_count,
            "passed": bool(passed),
        })
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {label}")
        print(f"       fired counters: {fired}")
        if not passed:
            print(f"       expected vector: {expected_vector}")
            print(f"       error_details ({details_count}): {result.get('error_details', [])}")
        print()

    all_passed = all(r["passed"] for r in records)
    n_pass = sum(1 for r in records if r["passed"])
    print("=" * 70)
    print(f"{n_pass}/{len(records)} CASES PASSED "
          f"(full 11-counter vector asserted per case)")
    print("=" * 70)

    return all_passed, records


if __name__ == "__main__":
    success, records = test_error_detector()
    # Save result for traceability (experiments/esa_cdm/results/ — the
    # esa_cdm results directory; data/current/ is wiped by the final
    # verification's §17 cleanup, which is why the earlier copies there
    # kept disappearing).
    import json, datetime
    out_path = RESULTS / "error_detector_test_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "test": "error_detector_bad_edge_injection",
        "date": datetime.datetime.now().isoformat(),
        "passed": success,
        "case_count": len(records),
        "counter_count": len(ERROR_KEYS),
        "assertion": ("full 11-counter vector == documented expectation per case "
                      "(target counter == 1 implied); error_details length == total "
                      "counted errors; coupled categories pinned explicitly"),
        "coupled_categories": {
            "Type 3": "time-reversed edge is necessarily non-adjacent (also Type 2)",
            "Type 4/7a": "same recovers-with-increase edge, two counter wordings",
            "Type 5/7b": "same degrades-not-2->3 edge, two counter wordings",
            "Type 6": "same-rank edge built cross-event (also Type 1)",
        },
        "cases": records,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResult saved to {out_path}")
    sys.exit(0 if success else 1)
