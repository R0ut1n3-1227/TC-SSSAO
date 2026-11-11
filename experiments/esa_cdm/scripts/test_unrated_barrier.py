"""Synthetic test for the unrated-snapshot barrier in streaming replay.

Two production entry points of 10_streaming_replay.py are exercised:

A. event_facts() — the adjacency derivation logic (unit level).
B. main() — the REAL production entry, driven end-to-end with monkeypatched
   load_processed/save_json (no real dataset is read; the result dict is
   captured in memory and results/streaming_replay.json is NOT overwritten).
   If main() ever regresses to the old prefilter-before-groupby logic, the
   discriminator cases B2/B5 fail (mutation-verified, see report §11).

Guard anatomy (why two kinds of "unrated" rows are tested):
    event_facts() skips a pair when EITHER endpoint fails ANY of the two
    independent guards: (1) preflight_pass is False, (2) state is NA.
    In production data both coincide (states are only assigned to valid
    rows), but the guards are independent code paths and each is tested
    in isolation: A1–A3/B2/B3 use preflight_pass=False with a state
    (guard 1); A5/B5 use preflight_pass=True with state=None (guard 2 —
    the "valid but unrated" record).

Why the main()-level discriminator is stale_adjacency_edges_removed:
    Gate outcomes cannot discriminate old vs fixed code, because
    eligible_count == len(prefiltered group) by construction — both select
   /exclude the same events.  What differs is WHICH ROWS reach
    event_facts(): the fixed code keeps unrated rows in the sequence (they
    block adjacency), the old code removed them (edges skip across).  The
    only observable of that difference in main()'s result dict is the
    delayed-recompute probe: chosen = [rows[0], rows[2]] produces an edge
    set "before", then [rows[0], rows[1], rows[2]] produces "after", and
    stale_adjacency_edges_removed counts revoked edges.  With an unrated
    row at position 2 the fixed code yields stale == 0; the old prefilter
    code yields stale > 0.  B1/B3/B4 pin gate and late-arrival behavior;
    B2/B5 are the regression discriminators.

The barrier invariant: any snapshot that fails a guard cannot be skipped
over.  Adjacency is computed on the FULL sorted list; a pair touching an
unrated snapshot is skipped — Normal→Warning is never evaluated across it.
"""
from __future__ import annotations

import sys
import json
import datetime
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from common import stable_token, RESULTS
from importlib import import_module
_streaming_replay = import_module("10_streaming_replay")
event_facts = _streaming_replay.event_facts


def make_row(snapshot_id: str, event_key: str, time_to_tca: float,
             source_row: int, preflight_pass: bool, state: str | None,
             severity_rank: int | None) -> pd.Series:
    return pd.Series({
        "snapshot_id":    snapshot_id,
        "event_key":      event_key,
        "time_to_tca":    time_to_tca,
        "source_row":     source_row,
        "preflight_pass": preflight_pass,
        "state":          state,
        "severity_rank":  severity_rank,
    })


def make_df(rows: list[pd.Series]) -> pd.DataFrame:
    return pd.DataFrame([r.to_dict() for r in rows])


def run_main_with_df(df: pd.DataFrame):
    """Drive the REAL production main() against a synthetic df.

    Returns (result_dict_or_None, SystemExit.code_or_None).  RuntimeError
    propagates to the caller (used by B4).
    """
    captured: dict = {}
    orig_load = _streaming_replay.load_processed
    orig_save = _streaming_replay.save_json
    _streaming_replay.load_processed = lambda: df
    _streaming_replay.save_json = lambda path, value: captured.update(
        {"path": str(path), "value": value})
    exit_code = None
    try:
        _streaming_replay.main()
    except SystemExit as exc:
        exit_code = exc.code
    finally:
        _streaming_replay.load_processed = orig_load
        _streaming_replay.save_json = orig_save
    return captured.get("value"), exit_code


# ---------------------------------------------------------------------------
# Level A: event_facts() unit tests (adjacency derivation)
# ---------------------------------------------------------------------------

def test_A1_unrated_blocks_all_transitions():
    """Normal(rated) → Attention(unrated) → Warning(rated).
    Zero transitions; Normal→Warning is NOT a zip pair."""
    rows = [
        make_row("n",  "TEST_A", 100.0, 0, True,  "Normal",   0),
        make_row("a",  "TEST_A",  50.0, 1, False, "Attention",1),
        make_row("w",  "TEST_A",  10.0, 2, True,  "Warning",  2),
    ]
    facts = event_facts(rows)
    transits = {f for f in facts if f[0] == "transitsTo"}
    assert len(transits) == 0, f"Expected 0 transitsTo, got {transits}"
    n_token = stable_token("n", "Normal")
    w_token = stable_token("w", "Warning")
    assert ("transitsTo", n_token, w_token) not in transits


def test_A2_leading_unrated_does_not_poison_downstream_pair():
    """Barrier is PAIR-LOCAL, not event-global: an unrated record at the
    sequence boundary blocks only its own pair.  The downstream rated pair
    Normal→Warning must still generate exactly one transition."""
    rows = [
        make_row("u",  "TEST_G", 100.0, 0, False, "Attention", 1),
        make_row("n",  "TEST_G",  50.0, 1, True,  "Normal",    0),
        make_row("w",  "TEST_G",  10.0, 2, True,  "Warning",   2),
    ]
    facts = event_facts(rows)
    transits = {f for f in facts if f[0] == "transitsTo"}
    n_token = stable_token("n", "Normal")
    w_token = stable_token("w", "Warning")
    assert transits == {("transitsTo", n_token, w_token)}, \
        f"Exactly one transition (Normal→Warning) must survive, got {transits}"
    assert not any(f[1] == "u" or (len(f) > 2 and f[2] == "u") for f in facts), \
        "No fact may mention the unrated snapshot"


def test_A3_pair_rated_unrated_no_transition():
    """Normal(rated) → Attention(unrated) — no transition."""
    rows = [
        make_row("n2", "TEST_B", 100.0, 0, True,  "Normal",   0),
        make_row("a2", "TEST_B",  50.0, 1, False, "Attention",1),
    ]
    facts = event_facts(rows)
    transits = {f for f in facts if f[0] == "transitsTo"}
    assert len(transits) == 0, f"Expected 0 transitsTo, got {transits}"


def test_A4_rated_pair_generates_transition():
    """Normal(rated) → Warning(rated) — positive control."""
    rows = [
        make_row("n3", "TEST_C", 100.0, 0, True, "Normal",  0),
        make_row("w3", "TEST_C",  50.0, 1, True, "Warning", 2),
    ]
    facts = event_facts(rows)
    transits = {f for f in facts if f[0] == "transitsTo"}
    n_token = stable_token("n3", "Normal")
    w_token = stable_token("w3", "Warning")
    assert ("transitsTo", n_token, w_token) in transits


def test_A5_valid_but_unrated_blocks_adjacency():
    """Guard 2 in isolation: middle row has preflight_pass=True but
    state=None / severity_rank=None (valid record, no risk level).
    Both pairs touching it are skipped by the state-NA guard (its
    preflight_pass check PASSES — only the isna(state) guard fires);
    no edge may cross it, and it yields no state fact."""
    rows = [
        make_row("n5", "TEST_D", 100.0, 0, True, "Normal",  0),
        make_row("x5", "TEST_D",  50.0, 1, True, None,      None),
        make_row("w5", "TEST_D",  10.0, 2, True, "Warning", 2),
    ]
    facts = event_facts(rows)
    transits = {f for f in facts if f[0] == "transitsTo"}
    assert len(transits) == 0, f"Expected 0 transitsTo, got {transits}"
    n_token = stable_token("n5", "Normal")
    w_token = stable_token("w5", "Warning")
    assert ("transitsTo", n_token, w_token) not in transits, \
        "No edge may cross the valid-but-unrated snapshot"
    state_facts = {f for f in facts if f[0] == "state"}
    assert ("state", "x5", "None") not in state_facts
    assert not any(f[1] == "x5" for f in state_facts), \
        "Valid-but-unrated snapshot must not produce a state fact"
    assert {f[1] for f in state_facts} == {"n5", "w5"}


def test_A6_late_unrated_revokes_recovery_edge():
    """Incremental late arrival (event_facts level): with only the two
    rated endpoints present, a Dangerous→Normal recovery edge EXISTS;
    inserting the late unrated middle record must REVOKE it.

    before = {state d, state n, transitsTo(d,n), recoversTo(d,n)}
    after  = {state d, state n}                      (both pairs blocked)
    revoked = before - after = exactly the two edge facts."""
    d = make_row("d6", "TEST_E", 100.0, 0, True,  "Dangerous", 3)
    a = make_row("a6", "TEST_E",  50.0, 1, False, "Attention", 1)
    n = make_row("n6", "TEST_E",  10.0, 2, True,  "Normal",    0)

    before = event_facts([d, n])
    d_token = stable_token("d6", "Dangerous")
    n_token = stable_token("n6", "Normal")
    edge_t = ("transitsTo", d_token, n_token)
    edge_r = ("recoversTo", d_token, n_token)
    assert edge_t in before and edge_r in before, \
        "Recovery edge must exist before the late record arrives"

    after = event_facts([d, a, n])
    transits_after = {f for f in after if f[0] == "transitsTo"}
    recovers_after = {f for f in after if f[0] == "recoversTo"}
    assert len(transits_after) == 0 and len(recovers_after) == 0, \
        f"Late unrated record must block all edges, got {transits_after | recovers_after}"

    revoked = before - after
    assert revoked == {edge_t, edge_r}, \
        f"Revoked set must be exactly the recovery edge pair, got {revoked}"


def test_A7_late_rated_replaces_recovery_edge():
    """Incremental late arrival of a RATED middle record: the direct
    Dangerous→Normal edge is revoked and replaced by the two-step
    recovery Dangerous→Warning and Warning→Normal (delete-and-recompute
    replacement, not mere deletion)."""
    d = make_row("d7", "TEST_F", 100.0, 0, True, "Dangerous", 3)
    w = make_row("w7", "TEST_F",  50.0, 1, True, "Warning",   2)
    n = make_row("n7", "TEST_F",  10.0, 2, True, "Normal",    0)

    before = event_facts([d, n])
    d_tok = stable_token("d7", "Dangerous")
    w_tok = stable_token("w7", "Warning")
    n_tok = stable_token("n7", "Normal")

    after = event_facts([d, w, n])
    revoked = before - after
    assert revoked == {("transitsTo", d_tok, n_tok), ("recoversTo", d_tok, n_tok)}, \
        f"Direct edge must be revoked, got {revoked}"
    assert ("transitsTo", d_tok, w_tok) in after
    assert ("recoversTo", d_tok, w_tok) in after
    assert ("transitsTo", w_tok, n_tok) in after
    assert ("recoversTo", w_tok, n_tok) in after
    assert ("transitsTo", d_tok, n_tok) not in after


# ---------------------------------------------------------------------------
# Level B: production main() entry tests (real entry point, synthetic df)
# ---------------------------------------------------------------------------

def test_B1_main_gate_excludes_two_eligible_event():
    """Gate behavior via the real main(): event X has 3 snapshots but only
    2 preflight-passing (eligible_count=2 < 3) → excluded; event Y has 3
    rated → selected.  events_replayed must be exactly 1.

    (Gate outcomes cannot discriminate old vs fixed code — eligible_count
    equals the prefiltered group size by construction — so this pins the
    gate contract itself: exclusion by eligible count, selection at ≥ 3.)
    Y's delayed probe revokes one legitimately superseded edge (Normal→
    Warning replaced when the rated middle arrives), so stale == 1."""
    df = make_df([
        make_row("nx", "MAIN_X", 100.0, 0, True,  "Normal",    0),
        make_row("ax", "MAIN_X",  50.0, 1, False, "Attention", 1),
        make_row("wx", "MAIN_X",  10.0, 2, True,  "Warning",   2),
        make_row("ny", "MAIN_Y", 100.0, 3, True,  "Normal",    0),
        make_row("ay", "MAIN_Y",  50.0, 4, True,  "Attention", 1),
        make_row("wy", "MAIN_Y",  10.0, 5, True,  "Warning",   2),
    ])
    result, exit_code = run_main_with_df(df)
    assert result is not None, f"main() raised SystemExit({exit_code}) without a result"
    assert exit_code is None, f"main() reported FAIL: {result}"
    assert result["status"] == "PASS", result
    assert result["events_replayed"] == 1, \
        f"2-eligible event must be excluded, 3-eligible selected: {result}"
    assert result["stale_adjacency_edges_removed"] == 1, result
    assert result["in_order_derived_fact_sets_equal"] is True
    assert result["delayed_recompute_derived_fact_sets_equal"] is True


def test_B2_main_unrated_at_probe_position_stale_zero():
    """REGRESSION DISCRIMINATOR (guard 1) via the real main().
    Event: Dangerous(100, rated) → Warning(50, rated) → Attention(10,
    UNRATED) → Normal(5, rated).  The unrated snapshot sits at delayed-
    probe position rows[2], so chosen=[rows[0], rows[2]] contains no
    ratable pair and 'before' has no edge to revoke: stale must be 0.

    Under the old prefilter-before-groupby code the unrated row would be
    removed, chosen would become [Dangerous, Normal], a spurious recovery
    edge would be produced and later revoked: stale == 2 → this test
    FAILS.  Mutation-verified 2026-10-11 (report §11)."""
    df = make_df([
        make_row("d", "MAIN_B2", 100.0, 0, True,  "Dangerous", 3),
        make_row("w", "MAIN_B2",  50.0, 1, True,  "Warning",   2),
        make_row("a", "MAIN_B2",  10.0, 2, False, "Attention", 1),
        make_row("n", "MAIN_B2",   5.0, 3, True,  "Normal",    0),
    ])
    result, exit_code = run_main_with_df(df)
    assert result is not None and exit_code is None, \
        f"main() failed on fixed code: exit={exit_code} result={result}"
    assert result["status"] == "PASS", result
    assert result["events_replayed"] == 1, result
    assert result["stale_adjacency_edges_removed"] == 0, \
        f"Unrated row at probe position must yield stale == 0; got {result} " \
        "(stale > 0 indicates the old prefilter-before-groupby regression)"


def test_B3_main_late_unrated_revokes_recovery_end_to_end():
    """Late-arrival scenario through the real main() delayed-recompute
    probe: chosen = [Dangerous(100), Normal(10)] first PRODUCES the
    recovery edge (transitsTo + recoversTo); the late unrated
    Attention(50) is then inserted and the probe's full recompute
    REVOKES both edges: stale_adjacency_edges_removed must be exactly 2,
    and the delayed incremental set must still equal the batch set."""
    df = make_df([
        make_row("d",  "MAIN_B3", 100.0, 0, True,  "Dangerous", 3),
        make_row("a",  "MAIN_B3",  50.0, 1, False, "Attention", 1),
        make_row("n",  "MAIN_B3",  10.0, 2, True,  "Normal",    0),
        make_row("n2", "MAIN_B3",   5.0, 3, True,  "Normal",    0),
    ])
    result, exit_code = run_main_with_df(df)
    assert result is not None and exit_code is None, \
        f"main() failed: exit={exit_code} result={result}"
    assert result["status"] == "PASS", result
    assert result["stale_adjacency_edges_removed"] == 2, \
        f"Recovery edge (transitsTo+recoversTo) must be produced then revoked: {result}"
    assert result["delayed_recompute_derived_fact_sets_equal"] is True
    assert result["in_order_derived_fact_sets_equal"] is True


def test_B4_main_no_eligible_group_raises():
    """No event reaches eligible_count >= 3 → the real main() must raise
    RuntimeError (no silent empty replay)."""
    df = make_df([
        make_row("n", "MAIN_B4", 100.0, 0, True,  "Normal",    0),
        make_row("a", "MAIN_B4",  50.0, 1, False, "Attention", 1),
        make_row("w", "MAIN_B4",  10.0, 2, True,  "Warning",   2),
    ])
    try:
        run_main_with_df(df)
    except RuntimeError as exc:
        assert "at least three valid CDMs" in str(exc), f"Unexpected message: {exc}"
        return
    raise AssertionError("main() must raise RuntimeError when no group is eligible")


def test_B5_main_valid_but_unrated_stale_zero():
    """REGRESSION DISCRIMINATOR (guard 2) via the real main().
    Event: Normal(100, rated) → Warning(50, rated) → X(20, preflight_pass=
    True but state=None / severity_rank=None) → Dangerous(10, rated).
    X counts toward eligible_count (the gate is preflight-based, so the
    group IS selected with 4 ≥ 3), yet X blocks adjacency via the
    state-NA guard.  X sits at probe position rows[2]: chosen=[Normal, X]
    produces no edge, so stale must be 0.

    Under the old prefilter (which also required state.notna()) X would be
    removed, chosen would become [Normal, Dangerous], a spurious edge
    would be produced and revoked: stale == 1 → this test FAILS."""
    df = make_df([
        make_row("n", "MAIN_B5", 100.0, 0, True, "Normal",    0),
        make_row("w", "MAIN_B5",  50.0, 1, True, "Warning",   2),
        make_row("x", "MAIN_B5",  20.0, 2, True, None,        None),
        make_row("d", "MAIN_B5",  10.0, 3, True, "Dangerous", 3),
    ])
    result, exit_code = run_main_with_df(df)
    assert result is not None and exit_code is None, \
        f"main() failed on fixed code: exit={exit_code} result={result}"
    assert result["status"] == "PASS", result
    assert result["events_replayed"] == 1, result
    assert result["stale_adjacency_edges_removed"] == 0, \
        f"Valid-but-unrated row at probe position must yield stale == 0; got {result} " \
        "(stale > 0 indicates the old prefilter-before-groupby regression)"


# ---------------------------------------------------------------------------
# Registry-driven runner: counts are DERIVED, never hardcoded
# ---------------------------------------------------------------------------

TESTS = [
    ("A1 event_facts: unrated blocks all transitions", test_A1_unrated_blocks_all_transitions),
    ("A2 event_facts: leading unrated does not poison downstream pair", test_A2_leading_unrated_does_not_poison_downstream_pair),
    ("A3 event_facts: rated→unrated pair, no transition", test_A3_pair_rated_unrated_no_transition),
    ("A4 event_facts: rated pair generates transition (positive control)", test_A4_rated_pair_generates_transition),
    ("A5 event_facts: valid-but-unrated (pass/NA) blocks adjacency", test_A5_valid_but_unrated_blocks_adjacency),
    ("A6 event_facts: late unrated revokes pre-existing recovery edge", test_A6_late_unrated_revokes_recovery_edge),
    ("A7 event_facts: late rated middle replaces recovery edge", test_A7_late_rated_replaces_recovery_edge),
    ("B1 main(): gate excludes 2-eligible event, selects 3-eligible", test_B1_main_gate_excludes_two_eligible_event),
    ("B2 main(): DISCRIMINATOR — unrated at probe position ⇒ stale == 0", test_B2_main_unrated_at_probe_position_stale_zero),
    ("B3 main(): late unrated produces then revokes recovery edge (stale == 2)", test_B3_main_late_unrated_revokes_recovery_end_to_end),
    ("B4 main(): no eligible group raises RuntimeError", test_B4_main_no_eligible_group_raises),
    ("B5 main(): DISCRIMINATOR — valid-but-unrated at probe position ⇒ stale == 0", test_B5_main_valid_but_unrated_stale_zero),
]


def main() -> bool:
    print("=" * 70)
    print("Unrated-Snapshot Barrier — Synthetic Test Suite")
    print("Levels: A = event_facts() unit | B = production main() entry")
    print("=" * 70)
    print()

    results = []
    for name, fn in TESTS:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 — aggregate all failures
            results.append({"name": name, "status": "FAIL",
                            "error": f"{type(exc).__name__}: {exc}"})
            print(f"FAIL: {name}\n      {type(exc).__name__}: {exc}")
        else:
            results.append({"name": name, "status": "PASS"})
            print(f"PASS: {name}")

    n_pass = sum(1 for r in results if r["status"] == "PASS")
    all_passed = n_pass == len(results)
    level_a = sum(1 for r in results if r["name"].startswith("A"))
    level_b = len(results) - level_a

    print()
    print("=" * 70)
    print(f"{n_pass}/{len(results)} PASSED "
          f"({level_a} event_facts unit + {level_b} production main entry)")
    print("=" * 70)

    out_path = RESULTS / "unrated_barrier_test_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "test": "unrated_snapshot_barrier",
        "date": datetime.datetime.now().isoformat(),
        "passed": all_passed,
        "case_count": len(results),
        "passed_count": n_pass,
        "cases": results,
        "levels": {"event_facts_unit": level_a, "production_main_entry": level_b},
        "assertion": ("unrated blocks adjacency at both event_facts() and the real "
                      "production main() level; both guards (preflight_pass=False and "
                      "state=NA) tested in isolation; late-arrival revocation tested "
                      "incrementally (A6/A7) and through main()'s delayed probe (B3); "
                      "B2/B5 discriminate the old prefilter regression via "
                      "stale_adjacency_edges_removed == 0"),
        "entry_points_tested": [
            "event_facts() — production adjacency derivation",
            "main() — real production entry (monkeypatched load_processed/save_json; "
            "no dataset read, streaming_replay.json not overwritten)",
        ],
        "old_bug": ("prefilter removed unrated rows before groupby; gate outcomes are "
                    "provably identical (eligible_count == prefiltered group size), so "
                    "main()-level discrimination uses the delayed-recompute stale "
                    "counter with the unrated row at probe position rows[2]"),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResult saved to {out_path}")
    return all_passed


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
