from __future__ import annotations

from common import RESULTS, derive_transitions, load_processed, save_json, state_evolution_metrics, temporal_agreement


def main() -> None:
    df = load_processed()
    transitions = derive_transitions(df)
    transitions.to_csv(RESULTS / "b3_transitions.csv", index=False)
    metrics = state_evolution_metrics(df)
    agreement = temporal_agreement(df)
    result = {
        "status": "PASS" if (
            metrics["err_cross_event"] == 0
            and metrics["err_within_non_adjacent"] == 0
            and metrics["err_time_direction"] == 0
            and metrics["err_recovers_direction"] == 0
            and metrics["err_degrades_warning"] == 0
            and metrics["err_transits_same_rank"] == 0
            and metrics["err_mismatch_predicate"] == 0
            and metrics["err_mismatch_predicate2"] == 0
            and metrics["err_missing_recovers_on_downgrade"] == 0
            and metrics["err_missing_degrades_on_warning_dangerous"] == 0
            and metrics["err_direction_field_inconsistent"] == 0
        ) else "FAIL",
        "metrics": metrics,
        "temporal_state_agreement": agreement,
        "final_cdm_semantics": "best available knowledge, not absolute collision ground truth",
        "ordering": "within event_id, descending time_to_tca (larger means earlier CDM)",
    }
    save_json(RESULTS / "state_evolution.json", result)
    print(result)
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
