from __future__ import annotations

import json

import matplotlib.pyplot as plt
import numpy as np

from common import FIGURES, RESULTS, STATE_RANK, load_processed


def workflow_figure() -> None:
    labels = ["CDM / orbit\nassessment", "Normalization\nlog10(risk) -> Pc", "TC-SSSAO\nAssessmentData", "Input\nPreflight",
              "R5-R8\nrisk state", "B3\nevolution", "Risk / response\nknowledge", "Operator /\nplanning system"]
    fig, ax = plt.subplots(figsize=(12, 2.15))
    ax.set_xlim(-0.4, len(labels) - 0.6); ax.set_ylim(-0.6, 0.8); ax.axis("off")
    colors = ["#d9eaf7", "#d9eaf7", "#e8e0f4", "#f8e3bd", "#f5c6c6", "#f5c6c6", "#dff0d8", "#dff0d8"]
    for i, (label, color) in enumerate(zip(labels, colors)):
        ax.text(i, 0, label, ha="center", va="center", fontsize=9,
                bbox=dict(boxstyle="round,pad=0.45", facecolor=color, edgecolor="#3f4f5f", linewidth=1.0))
        if i + 1 < len(labels):
            ax.annotate("", xy=(i + 0.66, 0), xytext=(i + 0.34, 0), arrowprops=dict(arrowstyle="->", lw=1.2, color="#333333"))
    ax.text(3.5, -0.52, "Semantic backbone: consumes external risk results; does not compute orbits, Pc, or avoidance control",
            ha="center", fontsize=8, color="#555555")
    fig.tight_layout()
    fig.savefig(FIGURES / "cdm_tc_sssao_workflow.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def evidence_figure() -> None:
    df = load_processed()
    candidates = []
    for event_key, group in df[df["preflight_pass"] & df["state"].notna()].groupby("event_key"):
        ordered = group.sort_values(["time_to_tca", "source_row"], ascending=[False, True])
        ranks = ordered["state"].map(STATE_RANK).astype(int).to_numpy()
        changes = int(np.sum(ranks[1:] != ranks[:-1])) if len(ranks) > 1 else 0
        if len(ranks) >= 3:
            candidates.append((changes, len(ranks), str(event_key), ordered))
    _, _, event_key, example = max(candidates, key=lambda x: (x[0], x[1], x[2]))
    scale = json.loads((RESULTS / "scalability.json").read_text(encoding="utf-8"))
    sizes = np.array([x["event_count"] for x in scale["sizes"]])
    times = np.array([x["total_s"]["mean"] for x in scale["sizes"]])

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.4))
    axes[0].step(example["time_to_tca"], example["state"].map(STATE_RANK), where="mid", color="#b2182b", lw=1.8)
    axes[0].scatter(example["time_to_tca"], example["state"].map(STATE_RANK), s=18, color="#2166ac", zorder=3)
    axes[0].invert_xaxis(); axes[0].set_yticks([0, 1, 2, 3], ["Normal", "Attention", "Warning", "Dangerous"])
    axes[0].set_xlabel("Time to TCA (days; later updates to the right)"); axes[0].set_title(f"(a) Real event {event_key}")
    axes[0].grid(alpha=.25)
    axes[1].plot(sizes, times, "o-", color="#2166ac", lw=1.8, ms=4)
    axes[1].set_xlabel("Events"); axes[1].set_ylabel("Mean runtime (s)"); axes[1].set_title("(b) Partitioned prototype scaling")
    axes[1].grid(alpha=.25)
    fig.tight_layout()
    fig.savefig(FIGURES / "esa_evolution_and_scalability.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    (RESULTS / "figure_example_event.json").write_text(json.dumps({"event_key": event_key, "cdms": len(example)}, indent=2), encoding="utf-8")


def main() -> None:
    workflow_figure()
    evidence_figure()
    print("PASS generated figures")


if __name__ == "__main__":
    main()
