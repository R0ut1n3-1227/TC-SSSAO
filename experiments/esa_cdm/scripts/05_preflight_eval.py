from __future__ import annotations

from collections import Counter

from common import BASE, RESULTS, load_processed, save_json


def main() -> None:
    df = load_processed()
    reasons = Counter()
    for value in df.loc[~df["preflight_pass"], "rejection_reason"].fillna(""):
        for reason in str(value).split("; "):
            if reason:
                reasons[reason] += 1
    total = len(df)
    passed = int(df["preflight_pass"].sum())
    result = {
        "status": "PASS",
        "total_cdms": total,
        "total_events": int(df["event_key"].nunique()),
        "valid_pc": int(df["valid_pc"].sum()),
        "valid_miss_distance": int(df["valid_distance"].sum()),
        "valid_hbr": int(df["valid_hbr"].sum()),
        "complete_r5_r8_input": passed,
        "mapping_coverage": passed / total,
        "execution_layer_input_contract_pass": passed,
        "execution_layer_input_contract_reject": total - passed,
        "execution_layer_input_contract_pass_rate": passed / total,
        "formal_rdf_preflight_executed_on_full_esa_dataset": False,
        "scope_note": "Pandas execution-layer checks equivalent to the R5--R8 numeric/role input contract; not the formal RDF Input Preflight program.",
        "rejection_reasons": dict(sorted(reasons.items())),
    }
    save_json(RESULTS / "mapping_coverage.json", result)
    print(result)


if __name__ == "__main__":
    main()
