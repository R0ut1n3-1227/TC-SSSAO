"""Generate deterministic English figures for the TC-SSSAO paper."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(exist_ok=True)

COLORS = {
    "blue": "#EAF3FA",
    "green": "#ECF6EC",
    "gold": "#FFF5DF",
    "purple": "#F3EEF8",
    "red": "#FCEBEC",
    "line": "#243447",
    "rule": "#C43D3D",
    "state": "#7456A6",
    "muted": "#667789",
}


def setup(width: float, height: float):
    fig, ax = plt.subplots(figsize=(width, height))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    return fig, ax


def panel(ax, x, y, w, h, title, color, edge="#91A4B7"):
    patch = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.45,rounding_size=1.2",
                           facecolor=color, edgecolor=edge, linewidth=1.0)
    ax.add_patch(patch)
    ax.text(x + 1.2, y + h - 2.2, title, ha="left", va="top", fontsize=10.2,
            fontweight="bold", color="#17212B")


def node(ax, x, y, w, h, text, face="white", edge="#536779", fs=8.2, weight="normal"):
    patch = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=0.8",
                           facecolor=face, edgecolor=edge, linewidth=1.0)
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            fontweight=weight, color="#17212B")
    return (x, y, w, h)


def arrow(ax, p1, p2, label="", dashed=False, color=None, rad=0.0, fs=7.2):
    color = color or COLORS["line"]
    style = "dashed" if dashed else "solid"
    arr = FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=10,
                          linewidth=1.15, linestyle=style, color=color,
                          connectionstyle=f"arc3,rad={rad}")
    ax.add_patch(arr)
    if label:
        mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
        ax.text(mx, my + 1.2, label, ha="center", va="bottom", fontsize=fs,
                color=color, bbox=dict(facecolor="white", edgecolor="none", pad=0.4, alpha=0.9))


def figure_core():
    fig, ax = setup(15.2, 7.0)
    # White, paper-like grouping frames. Color is reserved for semantic node types.
    panel(ax, 1, 57, 25, 40, "Core domain concepts", "#FFFFFF", edge="#AAB5BF")
    panel(ax, 28, 57, 43, 40, "SpaceEvent and temporal-causal semantics", "#FFFFFF", edge="#AAB5BF")
    panel(ax, 73, 57, 26, 40, "Observation evidence", "#FFFFFF", edge="#AAB5BF")
    panel(ax, 1, 24, 48, 27, "CausalAssertion and provenance", "#FFFFFF", edge="#AAB5BF")
    panel(ax, 51, 24, 48, 27, "Risk-state classification and adjacent evolution", "#FFFFFF", edge="#AAB5BF")
    panel(ax, 1, 4, 98, 16, "Threat, risk, and response", "#FFFFFF", edge="#AAB5BF")

    # Core domain and event hierarchy
    so = node(ax, 3, 82, 12, 6, "SpaceObject", face="#EAF3FA", weight="bold")
    orbit = node(ax, 3, 68, 12, 5, "Orbit", face="#EAF3FA")
    arrow(ax, (9, 82), (9, 73), "hasOrbit", fs=6.2)
    artificial = node(ax, 17, 82, 7, 6, "ArtificialSpaceObject", face="#EAF3FA", fs=6.2)
    ax.plot([15, 17], [85, 85], color=COLORS["muted"], linewidth=0.9)
    for x, txt, w in [(15.2, "Spacecraft", 3.3), (18.7, "RocketBody", 3.3), (22.0, "SpaceDebris", 3.8)]:
        node(ax, x, 68, w, 5, txt, fs=5.0)
        ax.plot([20.5, x + 1.5], [82, 73], color=COLORS["muted"], linewidth=0.9)
    event = node(ax, 43, 77, 14, 7, "SpaceEvent", face="#FFF1DF", weight="bold", fs=9.0)
    arrow(ax, (15, 85), (43, 85), "participatesIn", fs=6.2)
    event_nodes = [(29, "OrbitManeuverEvent"), (39.5, "ApproachEvent"), (50, "CollisionRiskEvent"), (60.5, "DebrisRiskEvent")]
    for x, txt in event_nodes:
        node(ax, x, 63, 9, 5, txt, face="#FFF1DF", fs=5.7)
        ax.plot([50, x + 4.5], [77, 68], color=COLORS["muted"], linewidth=0.9)

    # Temporal context and causal event association
    temporal = node(ax, 30, 82, 9, 5, "TemporalEntity", face="#EAF3FA", fs=6.2)
    arrow(ax, (43, 80), (39, 84), "hasOccurrenceTime", fs=7.8)
    arrow(ax, (37.8, 67.3), (39.7, 67.3), "R1: precedesEvent", dashed=True, color=COLORS["rule"], rad=0.22, fs=5.6)
    arrow(ax, (37.8, 64.2), (39.7, 64.2), "R3: causesEvent", dashed=True, color=COLORS["rule"], rad=-0.22, fs=5.6)
    arrow(ax, (48.5, 65.5), (50, 65.5), "R4: causesEvent", dashed=True, color=COLORS["rule"], fs=5.8)
    ax.text(51, 55, "temporal order + object roles + observation evidence", ha="center", fontsize=6.8, color=COLORS["rule"])

    # Observation evidence chain
    obs_system = node(ax, 76, 88, 11, 5, "ObservationSystem", face="#EAF3FA", fs=6.4)
    sensor = node(ax, 76, 80, 11, 5, "Sensor", face="#EAF3FA", fs=6.4)
    activity = node(ax, 76, 72, 11, 5, "ObservationActivity", face="#EAF3FA", fs=6.0)
    data = node(ax, 76, 64, 11, 5, "ObservationData", face="#EAF3FA", fs=6.4)
    ax.plot([81.5, 81.5], [88, 85], color=COLORS["muted"], linewidth=0.9)
    ax.plot([81.5, 81.5], [80, 77], color=COLORS["muted"], linewidth=0.9)
    arrow(ax, (81.5, 72), (81.5, 80), "madeBySensor", fs=7.0)
    arrow(ax, (80.5, 72), (80.5, 69), "producesData", fs=6.2, color=COLORS["muted"])
    arrow(ax, (87, 88), (87, 66), "generatesData", fs=7.0)
    arrow(ax, (57, 80), (76, 66.5), "supportedByData", fs=7.0, color=COLORS["muted"])

    # Reified assertion and projection
    ca = node(ax, 4, 38, 13, 6, "CausalAssertion", face="#ECF6EC", weight="bold")
    cause = node(ax, 24, 43, 14, 5, "Cause Event\n(SpaceEvent)", face="#FFF1DF", fs=6.2)
    effect = node(ax, 24, 33, 14, 5, "Effect Event\n(SpaceEvent)", face="#FFF1DF", fs=6.2)
    evidence = node(ax, 4, 27, 13, 5, "SSAData", face="#EAF3FA", fs=6.1)
    arrow(ax, (17, 41), (24, 45.5), "hasCause", fs=6.4)
    arrow(ax, (17, 39), (24, 35.5), "hasEffect", fs=6.4)
    arrow(ax, (10.5, 38), (10.5, 32), "hasCausalEvidence", fs=6.0)
    arrow(ax, (38, 43), (38, 35.5), "causesEvent [derived]", dashed=True, color=COLORS["rule"], fs=6.0)

    # Risk classification separated from adjacent evolution
    snap = node(ax, 54, 38, 13, 5, "CollisionRiskEvent", face="#FFF1DF", fs=6.5)
    state = node(ax, 75, 38, 13, 5, "SituationState", face="#F3EEF8", weight="bold", fs=7.0)
    arrow(ax, (67, 40.5), (75, 40.5), "R5--R8: leadsToState", dashed=True, fs=5.6, color=COLORS["rule"])
    state_names = ["Normal\nSituationState", "Attention\nSituationState", "Warning\nSituationState", "Dangerous\nSituationState"]
    xs = [52, 63, 74, 85]
    for x, name in zip(xs, state_names):
        node(ax, x, 27, 9, 5, name, face="#F3EEF8", edge="#7456A6", fs=5.4)
        ax.plot([81.5, x + 4.5], [38, 32], color=COLORS["muted"], linewidth=0.9)
    for x1, x2 in zip(xs[:-1], xs[1:]):
        label = "transitsTo" if x1 < 74 else "transitsTo + degradesTo"
        arrow(ax, (x1 + 9, 29.5), (x2, 29.5), label, dashed=True, color=COLORS["rule"], fs=5.0)
    ax.text(74, 25.0, "representative increasing transitions", ha="center", fontsize=5.8, color=COLORS["muted"])

    # Threat, risk, response
    evt = node(ax, 9, 9, 13, 5, "DebrisRiskEvent", face="#FFF1DF", fs=6.5)
    threat = node(ax, 32, 9, 13, 5, "SecurityThreat", face="#F3EEF8", weight="bold", fs=6.5)
    srisk = node(ax, 55, 9, 13, 5, "SecurityRisk", face="#F3EEF8", weight="bold", fs=6.5)
    resp = node(ax, 78, 9, 14, 5, "ResponseMeasure", face="#ECF6EC", edge="#2D8761", weight="bold", fs=6.5)
    arrow(ax, (22, 11.5), (32, 11.5), "indicatesThreat", dashed=True, color=COLORS["rule"], fs=5.3)
    arrow(ax, (45, 11.5), (55, 11.5), "producesRisk", dashed=True, color=COLORS["rule"], fs=5.3)
    ax.plot([38.5, 38.5, 85, 85], [9, 5.8, 5.8, 9], color=COLORS["rule"], linewidth=1.0, linestyle="--")
    arrow(ax, (85, 5.8), (85, 9), "requiresResponseMeasure", dashed=True, color=COLORS["rule"], fs=6.2)

    ax.text(50, 1.4, "Solid -- schema or asserted relation     Red dashed -- rule-derived relation",
            ha="center", fontsize=8.6, color=COLORS["muted"])
    fig.tight_layout(pad=0.3)
    fig.savefig(OUT / "fig1_core_concepts.png", dpi=320, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def figure_ontology():
    fig, ax = setup(15.2, 6.1)
    modules = [
        (1, 53, 22, 43, "Space object / orbit", COLORS["blue"]),
        (1, 5, 22, 43, "Observation / data", "#ECF7F8"),
        (26, 30, 26, 66, "Space event / time", COLORS["green"]),
        (55, 30, 21, 66, "Situation / transition", COLORS["gold"]),
        (79, 30, 20, 66, "Threat / risk / response", COLORS["purple"]),
        (26, 5, 73, 20, "Causal assertion and evidence", "#FAF3E6"),
    ]
    for spec in modules:
        panel(ax, *spec)

    node(ax, 5, 82, 14, 6, "SpaceObject", weight="bold")
    node(ax, 5, 70, 14, 6, "ArtificialSpaceObject")
    node(ax, 2, 58, 6, 6, "Spacecraft", fs=6.5)
    node(ax, 9, 58, 6, 6, "RocketBody", fs=6.2)
    node(ax, 16, 58, 6, 6, "SpaceDebris", fs=6.2)
    arrow(ax, (12, 82), (12, 76), "subClassOf", color=COLORS["muted"], fs=6.4)

    node(ax, 4, 38, 16, 6, "ObservationSystem", weight="bold")
    node(ax, 4, 29, 16, 6, "Sensor")
    node(ax, 4, 20, 16, 6, "ObservationActivity")
    node(ax, 4, 11, 16, 6, "ObservationData /\nRiskAssessmentData", fs=6.8)
    arrow(ax, (12, 20), (12, 17), "generatesData", fs=6.2)

    node(ax, 31, 82, 16, 7, "SpaceEvent", weight="bold")
    node(ax, 28, 66, 13, 7, "OrbitManeuverEvent", fs=6.7)
    node(ax, 42, 66, 9, 7, "ApproachEvent", fs=6.7)
    node(ax, 30, 49, 19, 7, "CollisionRiskEvent", fs=7.5)
    arrow(ax, (39, 82), (34.5, 73), "subClassOf", color=COLORS["muted"], fs=6.3)
    arrow(ax, (39, 82), (45.5, 73), "subClassOf", color=COLORS["muted"], fs=6.3)
    arrow(ax, (34.5, 66), (40, 66), "causesEvent", dashed=True, color=COLORS["rule"], fs=6.4)
    arrow(ax, (45.5, 66), (39.5, 56), "causesEvent", dashed=True, color=COLORS["rule"], fs=6.4)
    ax.text(39, 38, "precedesEvent / followsEvent\noverlapsWithEvent", ha="center", fontsize=7.7)

    node(ax, 58, 82, 15, 7, "SituationState", weight="bold")
    for x, y, lab in [(56, 66, "NormalSituationState"), (66, 66, "AttentionSituationState"),
                      (56, 53, "WarningSituationState"), (66, 53, "DangerousSituationState")]:
        node(ax, x, y, 9, 6, lab, fs=5.5)
    node(ax, 58, 37, 15, 7, "StateTransition", weight="bold")
    arrow(ax, (65.5, 44), (65.5, 53), "hasSourceState / hasTargetState", fs=5.8)

    node(ax, 82, 82, 14, 7, "SecurityThreat", weight="bold")
    node(ax, 82, 61, 14, 7, "SecurityRisk", weight="bold")
    node(ax, 81, 39, 16, 7, "ResponseMeasure", weight="bold")
    arrow(ax, (89, 82), (89, 68), "producesRisk")

    node(ax, 31, 11, 16, 7, "CausalAssertion", weight="bold")
    node(ax, 56, 11, 15, 7, "cause / effect")
    node(ax, 79, 11, 15, 7, "supporting evidence")
    arrow(ax, (47, 14.5), (56, 14.5), "hasCause / hasEffect")
    arrow(ax, (71, 14.5), (79, 14.5), "hasCausalEvidence")

    arrow(ax, (23, 74), (31, 85), "involvesObject", rad=0.1)
    arrow(ax, (23, 32), (31, 85), "supportedByData", rad=-0.15)
    arrow(ax, (49, 52), (58, 85), "R5--R8: leadsToState", dashed=True, color=COLORS["rule"], rad=0.15)
    arrow(ax, (49, 52), (82, 84), "B4 (debris risk): indicatesThreat", dashed=True,
          color=COLORS["rule"], rad=-0.2, fs=6.2)
    arrow(ax, (81, 42), (49, 52), "respondsToEvent", rad=-0.16)
    arrow(ax, (89, 46), (89, 61), "mitigatesRisk")
    fig.tight_layout(pad=0.25)
    fig.savefig(OUT / "fig2_ontology_graph.png", dpi=320, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def figure_cz6a():
    fig, ax = setup(15.2, 5.5)
    panel(ax, 1, 9, 26, 83, "Source-grounded instances", COLORS["blue"])
    panel(ax, 31, 9, 37, 83, "Event and inference layer", COLORS["gold"])
    panel(ax, 72, 9, 27, 83, "Derived security knowledge", COLORS["purple"])

    upper = node(ax, 5, 70, 18, 8, "CZ-6A upper stage", weight="bold")
    nasa = node(ax, 5, 51, 18, 8, "NASA tracking report")
    study = node(ax, 5, 31, 18, 8, "Debris-risk assessment")
    measure = node(ax, 5, 14, 18, 8, "Continuous tracking", face="#E7F7EE", edge="#2D8761")

    frag = node(ax, 36, 72, 27, 9, "FragmentationEvent\n(2022-151B)", face="#FFF1DF", weight="bold")
    track = node(ax, 36, 51, 27, 9, "TrackingEvent\n(2023 debris tracking)", face="#FFF1DF", weight="bold")
    drisk = node(ax, 36, 28, 27, 9, "DebrisRiskEvent", face="#FFF1DF", weight="bold")
    ca = node(ax, 39, 13, 21, 8, "CausalAssertion")

    threat = node(ax, 77, 69, 17, 8, "PhysicalThreat", weight="bold")
    risk = node(ax, 77, 47, 17, 8, "DebrisRisk", weight="bold")
    response = node(ax, 76, 24, 19, 8, "ResponseMeasure", face="#E7F7EE", edge="#2D8761", weight="bold")
    query = node(ax, 77, 12, 17, 7, "Queryable graph", face="white", edge="#7456A6", weight="bold")

    arrow(ax, (23, 74), (36, 76), "identifies object")
    arrow(ax, (23, 55), (36, 55), "supports events")
    arrow(ax, (23, 35), (36, 32), "supports risk")
    arrow(ax, (23, 18), (76, 28), "instantiates response measure", rad=-0.06)
    arrow(ax, (49.5, 72), (49.5, 60), "R1: precedesEvent", dashed=True, color=COLORS["rule"])
    arrow(ax, (49.5, 51), (49.5, 37), "tracked debris")
    arrow(ax, (39, 17), (36, 76), "hasCause", rad=-0.34)
    arrow(ax, (60, 17), (63, 32), "hasEffect", rad=0.12)
    arrow(ax, (63, 76), (63, 32), "B1: causesEvent", dashed=True, color=COLORS["rule"], rad=-0.12)

    arrow(ax, (63, 32), (77, 73), "B4: indicatesThreat", dashed=True, color=COLORS["rule"], rad=0.18)
    arrow(ax, (63, 32), (77, 51), "B4: producesRisk", dashed=True, color=COLORS["rule"])
    arrow(ax, (76, 28), (63, 32), "B5: respondsToEvent", dashed=True, color=COLORS["rule"], rad=-0.12)
    arrow(ax, (76, 28), (77, 51), "B5: mitigatesRisk", dashed=True, color=COLORS["rule"])
    arrow(ax, (77, 73), (76, 28), "B5: requiresResponseMeasure", dashed=True,
          color=COLORS["rule"], rad=0.22, fs=6.6)
    arrow(ax, (85.5, 24), (85.5, 19), "SPARQL")
    arrow(ax, (85.5, 69), (85.5, 55), "producesRisk")

    ax.text(50, 3.3, "136 explicit case triples  →  3 fixed-point rounds  →  367 case triples (231 derived)  |  SHACL: conforms",
            ha="center", fontsize=9.0, fontweight="bold", color="#263646")
    fig.tight_layout(pad=0.25)
    fig.savefig(OUT / "fig3_cz6a_reasoning_results.png", dpi=320, bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    figure_core()
    figure_ontology()
    figure_cz6a()
    print("PASS generated three English paper figures")
