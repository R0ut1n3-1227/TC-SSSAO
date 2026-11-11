from __future__ import annotations

from common import RESULTS, THETA_A, THETA_M, load_processed, save_json


def main() -> None:
    df = load_processed()
    valid = df[df["preflight_pass"]]
    counts = valid["state"].value_counts(dropna=False)
    states = {}
    for name in ("Normal", "Attention", "Warning", "Dangerous"):
        count = int(counts.get(name, 0))
        states[name] = {"count": count, "ratio": count / len(valid) if len(valid) else 0.0}
    no_state = int(valid["state"].isna().sum())
    multi_state = 0
    result = {
        "status": "PASS" if no_state == 0 and multi_state == 0 else "FAIL",
        "theta_A": THETA_A,
        "theta_M": THETA_M,
        "classified_cdms": int(len(valid)),
        "states": states,
        "no_state": no_state,
        "multi_state": multi_state,
        "unique_state_rate": (len(valid) - no_state - multi_state) / len(valid) if len(valid) else 0.0,
        "note": "These are TC-SSSAO knowledge-organization states, not ESA/NASA operational state labels.",
    }
    save_json(RESULTS / "risk_state_distribution.json", result)
    print(result)
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
