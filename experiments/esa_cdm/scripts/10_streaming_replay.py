from __future__ import annotations

from collections import defaultdict

import pandas as pd

from common import RESULTS, STATE_RANK, load_processed, save_json, stable_token


def state_fact(row) -> tuple[str, str, str]:
    return ("state", str(row.snapshot_id), str(row.state))


def event_facts(rows: list) -> set[tuple[str, ...]]:
    ordered = sorted(rows, key=lambda r: (-float(r.time_to_tca), int(r.source_row)))
    facts: set[tuple[str, ...]] = {state_fact(row) for row in ordered if bool(row.preflight_pass) and pd.notna(row.state)}
    for left, right in zip(ordered, ordered[1:]):
        if not bool(left.preflight_pass) or not bool(right.preflight_pass) or pd.isna(left.state) or pd.isna(right.state):
            continue
        # Strict time direction: earlier snapshot (larger time_to_tca) must come first
        if not (float(left.time_to_tca) > float(right.time_to_tca)):
            continue
        r1, r2 = STATE_RANK[str(left.state)], STATE_RANK[str(right.state)]
        if r1 == r2:
            continue  # same severity: no transition
        s1 = stable_token(left.snapshot_id, left.state)
        s2 = stable_token(right.snapshot_id, right.state)
        facts.add(("transitsTo", s1, s2))
        if r1 == 2 and r2 == 3:
            facts.add(("degradesTo", s1, s2))
        elif r1 > r2:
            facts.add(("recoversTo", s1, s2))
    return facts


def main() -> None:
    df = load_processed()
    # P1-3 fix: groupby on full df (not eligible) so unrated snapshots
    # participate in adjacency blocking.  Only the per-group eligible count
    # (>=3) gates replay selection; event_facts() itself correctly skips
    # pairs where either endpoint has preflight_pass=False or state=NA.
    groups = []
    for event_key, group in df.groupby("event_key", sort=True):
        eligible_count = int(group["preflight_pass"].sum())
        if eligible_count >= 3:
            rows = list(group.sort_values(["time_to_tca", "source_row"], ascending=[False, True]).itertuples(index=False))
            groups.append((str(event_key), rows))
    groups = groups[:100]
    if not groups:
        raise RuntimeError("No event has at least three valid CDMs")

    batch: set[tuple[str, ...]] = set()
    incremental: set[tuple[str, ...]] = set()
    for _, rows in groups:
        batch |= event_facts(rows)
        arrived = []
        for row in rows:
            arrived.append(row)
            # Event-local recompute: remove only facts mentioning this event's
            # stable snapshot/state identifiers, then derive current adjacency.
            snapshot_ids = {str(r.snapshot_id) for r in rows}
            state_ids = {stable_token(r.snapshot_id, r.state) for r in rows}
            incremental = {fact for fact in incremental if not any(x in snapshot_ids or x in state_ids for x in fact[1:])}
            incremental |= event_facts(arrived)

    in_order_equal = batch == incremental

    delayed_batch: set[tuple[str, ...]] = set()
    delayed_incremental: set[tuple[str, ...]] = set()
    stale_removed = 0
    for _, rows in groups:
        chosen = [rows[0], rows[2]]
        before = event_facts(chosen)
        delayed_incremental |= before
        after = event_facts([rows[0], rows[1], rows[2]])
        stale_removed += len({fact for fact in before - after if fact[0] in {"transitsTo", "degradesTo", "recoversTo"}})
        ids = {str(r.snapshot_id) for r in rows[:3]}
        state_ids = {stable_token(r.snapshot_id, r.state) for r in rows[:3]}
        delayed_incremental = {fact for fact in delayed_incremental if not any(x in ids or x in state_ids for x in fact[1:])}
        delayed_incremental |= after
        delayed_batch |= after
    delayed_equal = delayed_batch == delayed_incremental

    result = {
        "status": "PASS" if in_order_equal and delayed_equal else "FAIL",
        "events_replayed": len(groups),
        "comparison_level": "derived state and B3 fact tuples; no RDF graph isomorphism test",
        "in_order_derived_fact_sets_equal": in_order_equal,
        "delayed_recompute_derived_fact_sets_equal": delayed_equal,
        "stale_adjacency_edges_removed": stale_removed,
        "stable_iri_policy": "SHA-256 of event-scoped snapshot identity and state",
        "late_snapshot_policy": "delete and recompute B3-derived edges only for the affected event_id",
        "truth_maintenance_claim": False,
    }
    save_json(RESULTS / "streaming_replay.json", result)
    print(result)
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
