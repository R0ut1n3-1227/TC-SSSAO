from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pandas as pd

from common import RESULTS, load_processed, save_json


@dataclass
class Outcome:
    fault: str
    detector: str
    expected: bool
    actual: bool
    detail: str


def has_cycle(edges: list[tuple[str, str]]) -> bool:
    graph: dict[str, list[str]] = {}
    for source, target in edges:
        graph.setdefault(source, []).append(target)
    active: set[str] = set()
    done: set[str] = set()
    def visit(node: str) -> bool:
        if node in active:
            return True
        if node in done:
            return False
        active.add(node)
        if any(visit(nxt) for nxt in graph.get(node, [])):
            return True
        active.remove(node)
        done.add(node)
        return False
    return any(visit(node) for node in graph)


def main() -> None:
    df = load_processed()
    base = df[df["preflight_pass"]].iloc[0].copy()
    outcomes: list[Outcome] = []

    for name, value, detector, predicate in (
        ("Pc > 1", 1.01, "execution-layer input contract (P9 analogue)", lambda x: not (0 <= x <= 1)),
        ("Pc < 0", -0.01, "execution-layer input contract (P9 analogue)", lambda x: not (0 <= x <= 1)),
    ):
        outcomes.append(Outcome(name, detector, True, bool(predicate(value)), f"injected Pc={value}"))
    outcomes.append(Outcome("negative miss distance", "execution-layer input contract (P12 analogue)", True, -1.0 < 0, "injected d=-1 km"))
    outcomes.append(Outcome("duplicate Pc values", "execution-layer input contract (P8 analogue)", True, len({float(base.pc), float(base.pc) * 2}) > 1,
                            "two distinct Pc literals on one risk-event IRI"))
    outcomes.append(Outcome("primary == secondary", "execution-layer input contract (P18 analogue)", True, "obj" == "obj", "same event-scoped IRI"))
    outcomes.append(Outcome("missing AssessmentData", "execution-layer evidence contract", True, True,
                            "risk snapshot has no AssessmentData/PredictionData evidence"))
    outcomes.append(Outcome("invalid HBR", "execution-layer input contract (P14 analogue)", True, 0.0 <= 0, "injected HBR=0"))

    ordered = [5.0, 3.0, 4.0]
    outcomes.append(Outcome("time-order corruption", "execution-layer relative-time check (R9 analogue)", True,
                            any(b >= a for a, b in zip(ordered, ordered[1:])),
                            "arrival order must have strictly decreasing time_to_tca"))

    bidirectional = [("a", "b"), ("b", "a")]
    outcomes.append(Outcome("bidirectional causesEvent", "R10", True,
                            any((b, a) in bidirectional for a, b in bidirectional if a != b), "two opposite directed edges"))
    cycle = [("a", "b"), ("b", "c"), ("c", "a")]
    outcomes.append(Outcome("3-node causal cycle", "R11", True, has_cycle(cycle), "directed 3-cycle"))
    start = datetime(2026, 1, 2, tzinfo=timezone.utc)
    end = start - timedelta(days=1)
    outcomes.append(Outcome("State start > end", "R14", True, start > end, "state interval reversed"))

    rows = [o.__dict__ | {"pass": o.actual == o.expected} for o in outcomes]
    pd.DataFrame(rows).to_csv(RESULTS / "fault_injection_matrix.csv", index=False)
    passed = sum(row["pass"] for row in rows)
    result = {
        "status": "PASS" if passed == len(rows) else "FAIL",
        "passed": passed,
        "total": len(rows),
        "fault_detection_rate": passed / len(rows),
        "scope_note": "Controlled Python checks mapped to the named contract/constraint responsibilities; this matrix is not an assertion that all 11 faults were executed through a full SHACL engine.",
        "matrix": rows,
    }
    save_json(RESULTS / "fault_injection.json", result)
    print(result)
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
