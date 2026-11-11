from __future__ import annotations

import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
BASE = Path(__file__).resolve().parent
SVG_PATH = BASE / "out" / "figure3_1_concept.svg"
AUDIT_PATH = BASE / "out" / "figure3_1_concept_content.json"

W, H = 5200, 2500
INK = "#161616"
GRAY = "#75818A"
LIGHT_GRAY = "#AEB8BF"
RED = "#B51F2A"
WHITE = "#FFFFFF"

MODULES = {
    "space": {"fill": "#F2F6FA", "stroke": "#91AABD"},
    "observation": {"fill": "#F1F8F8", "stroke": "#8EB5B4"},
    "event": {"fill": "#F3F8F0", "stroke": "#9DB493"},
    "causal": {"fill": "#FCF7EE", "stroke": "#BEAA85"},
    "state": {"fill": "#FCF8EE", "stroke": "#C1AD7C"},
    "security": {"fill": "#F7F3F8", "stroke": "#A99AAF"},
}

CLASS_MODULES = {
    "Space Object / Orbit": ["SpaceObject", "ArtificialSpaceObject", "Spacecraft", "Satellite", "RocketBody", "SpaceDebris", "Orbit", "EarthOrbit"],
    "Observation System / Data": ["ObservationSystem", "Sensor", "RadarSensor", "OpticalSensor", "InfraredSensor", "SensorNetwork", "SSAData", "ObservationData"],
    "Space Event / Temporal Relation": ["SpaceEvent", "ObjectBehaviorEvent", "OrbitalEvent", "SpatialRelationEvent", "RiskEvent", "OrbitManeuverEvent", "ApproachEvent", "CollisionRiskEvent"],
    "Causal Assertion / Event Relation": ["CausalAssertion", "MultiCauseAssertion"],
    "Situation State / State Transition": ["SituationState", "NormalSituationState", "AttentionSituationState", "WarningSituationState", "DangerousSituationState", "StateTransition"],
    "Threat / Risk / Response": ["SecurityThreat", "PhysicalThreat", "EnvironmentalThreat", "SecurityRisk", "CollisionRisk", "DebrisRisk", "ResponseMeasure", "AvoidanceMeasure"],
}

SUBCLASS_EDGES = [
    ("ArtificialSpaceObject", "SpaceObject"), ("Spacecraft", "ArtificialSpaceObject"), ("Satellite", "Spacecraft"),
    ("RocketBody", "ArtificialSpaceObject"), ("SpaceDebris", "ArtificialSpaceObject"), ("EarthOrbit", "Orbit"),
    ("Sensor", "ObservationSystem"), ("RadarSensor", "Sensor"), ("OpticalSensor", "Sensor"), ("InfraredSensor", "Sensor"), ("SensorNetwork", "ObservationSystem"), ("ObservationData", "SSAData"),
    ("ObjectBehaviorEvent", "SpaceEvent"), ("OrbitalEvent", "SpaceEvent"), ("SpatialRelationEvent", "SpaceEvent"), ("RiskEvent", "SpaceEvent"),
    ("OrbitManeuverEvent", "ObjectBehaviorEvent"), ("OrbitManeuverEvent", "OrbitalEvent"),
    ("ApproachEvent", "SpatialRelationEvent"),
    ("CollisionRiskEvent", "RiskEvent"), ("CollisionRiskEvent", "SpatialRelationEvent"),
    ("MultiCauseAssertion", "CausalAssertion"),
    ("NormalSituationState", "SituationState"), ("AttentionSituationState", "SituationState"), ("WarningSituationState", "SituationState"), ("DangerousSituationState", "SituationState"),
    ("PhysicalThreat", "SecurityThreat"), ("EnvironmentalThreat", "SecurityThreat"),
    ("CollisionRisk", "SecurityRisk"), ("DebrisRisk", "SecurityRisk"),
    ("AvoidanceMeasure", "ResponseMeasure"),
]

# Each entry records what is actually visible. Parallel properties sharing the same
# source and target class are drawn as one labelled connection to keep the TBox figure compact.
PROPERTY_EDGES = [
    {"property": "hasOrbit", "source": "SpaceObject", "target": "Orbit", "style": "solid", "display": "arrow"},
    {"property": "generatesData", "source": "ObservationSystem", "target": "ObservationData", "style": "solid", "display": "arrow"},
    {"property": "involvesObject", "source": "SpaceEvent", "target": "SpaceObject", "style": "solid", "display": "arrow"},
    {"property": "occursInOrbit", "source": "SpaceEvent", "target": "Orbit", "style": "solid", "display": "arrow"},
    {"property": "detectedFromData", "source": "SpaceEvent", "target": "SSAData", "style": "solid", "display": "arrow"},
    {"property": "precedesEvent", "source": "SpaceEvent", "target": "SpaceEvent", "style": "text-note", "display": "text-note"},
    {"property": "followsEvent", "source": "SpaceEvent", "target": "SpaceEvent", "style": "text-note", "display": "text-note"},
    {"property": "overlapsWithEvent", "source": "SpaceEvent", "target": "SpaceEvent", "style": "text-note", "display": "text-note"},
    {"property": "hasCause", "source": "CausalAssertion", "target": "SpaceEvent", "style": "solid", "display": "shared-arrow"},
    {"property": "hasEffect", "source": "CausalAssertion", "target": "SpaceEvent", "style": "solid", "display": "shared-arrow"},
    {"property": "hasCausalEvidence", "source": "CausalAssertion", "target": "SSAData", "style": "solid", "display": "arrow"},
    {"property": "causesEvent", "source": "SpaceEvent", "target": "SpaceEvent", "style": "red-text-note", "display": "text-note"},
    {"property": "leadsToState", "source": "SpaceEvent", "target": "SituationState", "style": "dashed", "display": "arrow"},
    {"property": "hasSourceState", "source": "StateTransition", "target": "SituationState", "style": "solid", "display": "shared-arrow"},
    {"property": "hasTargetState", "source": "StateTransition", "target": "SituationState", "style": "solid", "display": "shared-arrow"},
    {"property": "transitsTo", "source": "SituationState", "target": "SituationState", "style": "red-text-note", "display": "text-note"},
    {"property": "degradesTo", "source": "SituationState", "target": "SituationState", "style": "red-text-note", "display": "text-note"},
    {"property": "indicatesThreat", "source": "SpaceEvent", "target": "SecurityThreat", "style": "solid", "display": "arrow"},
    {"property": "producesRisk", "source": "SecurityThreat", "target": "SecurityRisk", "style": "solid", "display": "arrow"},
    {"property": "riskLeadsToState", "source": "SecurityRisk", "target": "SituationState", "style": "solid", "display": "arrow"},
    {"property": "requiresResponseMeasure", "source": "SecurityThreat", "target": "ResponseMeasure", "style": "solid", "display": "arrow"},
    {"property": "mitigatesRisk", "source": "ResponseMeasure", "target": "SecurityRisk", "style": "solid", "display": "arrow"},
]


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def text(x, y, value, size=36, weight=400, anchor="start", fill=INK):
    return (
        f'<text x="{x}" y="{y}" text-anchor="{anchor}" fill="{fill}" '
        'font-family="Microsoft YaHei, Noto Sans CJK SC, SimHei, Arial, sans-serif" '
        f'font-size="{size}" font-weight="{weight}">{esc(value)}</text>'
    )


def rect(x, y, w, h, fill=WHITE, stroke=GRAY, sw=2.0, rx=8, dash=None):
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{dash_attr}/>'


def module(x, y, w, h, key, english, chinese):
    c = MODULES[key]
    return (
        rect(x, y, w, h, fill=c["fill"], stroke=c["stroke"], sw=2.0, rx=12)
        + text(x + 28, y + 56, english, size=45, weight=700)
        + text(x + 28, y + 103, chinese, size=36, weight=500)
    )


def node(x, y, w, h, label, *, bold=False, size=31):
    size = round(size * 1.28)
    return (
        f'<g id="class-{esc(label)}">'
        + rect(x, y, w, h, fill=WHITE, stroke="#66727A", sw=2.8 if bold else 1.7, rx=7)
        + text(x + w / 2, y + h / 2 + size * 0.35, label, size=size, weight=700 if bold else 500, anchor="middle")
        + '</g>'
    )


def path(d, *, color=INK, sw=2.4, dashed=False, marker="arrow-black", arrow=True, id_=None):
    dash = ' stroke-dasharray="13 10"' if dashed else ""
    end = f' marker-end="url(#{marker})"' if arrow else ""
    ident = f' id="edge-{esc(id_)}"' if id_ else ""
    return f'<path{ident} d="{d}" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linejoin="round" stroke-linecap="round"{dash}{end}/>'


def line(x1, y1, x2, y2, **kwargs):
    return path(f"M{x1},{y1} L{x2},{y2}", **kwargs)


def label(x, y, value, *, color=INK, size=27, width=None):
    size = round(size * 1.25)
    width = (width * 1.22) if width else max(175, len(value) * size * 0.58)
    return (
        f'<rect x="{x-width/2}" y="{y-size-5}" width="{width}" height="{size+12}" rx="4" fill="#FFFFFF" fill-opacity="0.96"/>'
        + text(x, y, value, size=size, weight=600, anchor="middle", fill=color)
    )


def subclass(d):
    return path(d, color=GRAY, sw=1.9, marker="arrow-gray")


def generate_svg() -> str:
    s = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        '<title>图3-1 TC-SSSAO的上层概念体系</title>',
        '<desc>依据tc_sssao.owl核验的49个类绘制的论文级概念体系图；非Protégé插件原始截图。</desc>',
        '<defs>',
        f'<marker id="arrow-black" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker>',
        f'<marker id="arrow-red" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L10,5 L0,10 z" fill="{RED}"/></marker>',
        f'<marker id="arrow-gray" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L9,4.5 L0,9 z" fill="{GRAY}"/></marker>',
        '</defs>',
        f'<rect width="{W}" height="{H}" fill="{WHITE}"/>',
    ]

    # Small four-item legend. It reads as a figure key rather than a title banner.
    s += [
        line(360, 92, 480, 92), text(505, 105, "实线箭头：模式层/显式语义关系", size=34),
        line(1530, 92, 1650, 92, color=RED, dashed=True, marker="arrow-red"), text(1675, 105, "红色虚线箭头：规则可生成的实例关系", size=34, fill=RED),
        line(3200, 92, 3320, 92, color=GRAY, sw=1.9, marker="arrow-gray"), text(3345, 105, "细实线：subClassOf", size=34, fill="#526069"),
        rect(4120, 68, 58, 38, fill=MODULES["event"]["fill"], stroke=MODULES["event"]["stroke"], sw=1.5, rx=2),
        text(4200, 105, "不同底色：不同知识模块", size=34),
    ]

    # Six functional modules. Different heights reflect content density.
    s += [
        module(40, 180, 1100, 980, "space", "Space Object / Orbit", "空间目标与轨道"),
        module(40, 1210, 1100, 1250, "observation", "Observation System / Data", "观测系统与数据"),
        module(1200, 180, 1300, 1370, "event", "Space Event / Temporal Relation", "空间事件与时间"),
        module(1200, 1600, 1300, 860, "causal", "Causal Assertion / Event Relation", "因果断言与事件关系"),
        module(2560, 360, 1200, 2100, "state", "Situation State / State Transition", "态势状态与状态转移"),
        module(3820, 180, 1340, 2280, "security", "Threat / Risk / Response", "安全威胁、风险与响应"),
    ]

    # 1. Space Object / Orbit (8 classes).
    s += [
        node(130, 340, 430, 82, "SpaceObject", bold=True, size=34),
        node(680, 340, 330, 82, "Orbit", bold=True, size=34),
        node(110, 555, 650, 78, "ArtificialSpaceObject", size=29),
        node(120, 745, 280, 74, "Spacecraft", size=30),
        node(430, 745, 300, 74, "RocketBody", size=30),
        node(770, 745, 330, 74, "SpaceDebris", size=29),
        node(140, 905, 300, 74, "Satellite", size=30),
        node(800, 555, 330, 78, "EarthOrbit", size=31),
        subclass("M360,555 L345,422"), subclass("M260,745 L330,633"), subclass("M580,745 L560,633"),
        subclass("M935,745 L720,633"), subclass("M290,905 L270,819"), subclass("M965,555 L870,422"),
        line(560, 381, 680, 381, id_="hasOrbit"), label(620, 350, "hasOrbit", size=25, width=145),
    ]

    # 2. Observation System / Data (8 classes).
    s += [
        node(110, 1380, 520, 82, "ObservationSystem", bold=True, size=32),
        node(730, 1380, 320, 82, "SSAData", bold=True, size=34),
        node(170, 1620, 320, 78, "Sensor", size=32),
        node(700, 1620, 390, 78, "ObservationData", size=30),
        node(70, 1880, 310, 76, "RadarSensor", size=28),
        node(410, 1880, 320, 76, "OpticalSensor", size=28),
        node(760, 1880, 340, 76, "InfraredSensor", size=27),
        node(170, 2160, 400, 78, "SensorNetwork", size=29),
        subclass("M330,1620 L350,1462"), subclass("M225,1880 L290,1698"), subclass("M570,1880 L350,1698"), subclass("M930,1880 L410,1698"),
        subclass("M370,2160 L210,1462"), subclass("M895,1620 L890,1462"),
        path("M630,1421 L670,1421 L670,1659 L700,1659", id_="generatesData"), label(670, 1550, "generatesData", size=25, width=190),
    ]

    # 3. Space Event / Temporal Relation (8 classes). Representative events keep their true
    #    direct parents; CollisionRiskEvent shows dual inheritance (RiskEvent + SpatialRelationEvent).
    s += [
        node(1600, 340, 500, 86, "SpaceEvent", bold=True, size=36),
        node(1235, 540, 350, 66, "ObjectBehaviorEvent", size=24),
        node(1610, 540, 280, 66, "OrbitalEvent", size=25),
        node(2100, 540, 280, 66, "RiskEvent", size=26),
        node(1600, 650, 460, 64, "SpatialRelationEvent", size=23),
        node(1235, 790, 390, 74, "OrbitManeuverEvent", size=27),
        node(1655, 790, 350, 74, "ApproachEvent", size=29),
        node(2035, 790, 420, 74, "CollisionRiskEvent", size=26),
        subclass("M1410,540 L1660,430"), subclass("M1750,540 L1800,430"),
        subclass("M2240,540 L2040,430"), subclass("M1950,650 L1950,430"),
        subclass("M1430,790 L1415,606"), subclass("M1520,790 L1700,606"),
        subclass("M1830,790 L1830,714"),
        subclass("M2245,790 L2240,606"), subclass("M2140,790 L2000,714"),
        text(1850, 905, "仅示代表性事件类，其余事件子类省略", size=32, weight=400, anchor="middle", fill="#59645C"),
        line(1450, 965, 1530, 965, color=RED, sw=2.2, dashed=True, marker="arrow-red", arrow=False),
        text(1550, 976, "事件关系：", size=31, weight=500, fill="#4D5550"),
        text(1722, 976, "causesEvent", size=31, weight=600, fill=RED),
        text(1850, 1080, "时间关系：precedesEvent / followsEvent / overlapsWithEvent", size=33, weight=500, anchor="middle", fill="#4D5550"),
    ]

    # 4. Causal Assertion / Event Relation (6 classes).
    s += [
        node(1600, 1850, 500, 86, "CausalAssertion", bold=True, size=35),
        node(1290, 2100, 540, 74, "MultiCauseAssertion", size=28),
        # MultiCauseAssertion directly under CausalAssertion.
        subclass("M1560,2100 L1560,1920"), subclass("M1560,1920 L1700,1920 L1700,1871"),
        text(1892, 2100, "多原因联合", size=26, weight=500, fill="#526069"),
    ]

    # 5. Situation State / State Transition (6 classes, no ComprehensiveSituationState).
    s += [
        node(2860, 535, 600, 84, "SituationState", bold=True, size=35),
        node(2600, 815, 530, 78, "NormalSituationState", size=28),
        node(3170, 815, 550, 78, "AttentionSituationState", size=27),
        node(2600, 1060, 530, 78, "WarningSituationState", size=28),
        node(3170, 1060, 550, 78, "DangerousSituationState", size=27),
        node(2860, 2230, 600, 84, "StateTransition", bold=True, size=34),
        # Four situation states directly under SituationState.
        subclass("M2865,815 L2865,577"), subclass("M3170,815 L3170,577"),
        subclass("M2865,1060 L2865,577"), subclass("M3170,1060 L3170,577"),
        # Trunk hugs the module left edge.
        path("M2860,2272 L2580,2272 L2580,577 L2860,577", id_="hasSourceState_hasTargetState"),
        label(2580, 2030, "hasSourceState / hasTargetState", size=24, width=390),
        line(2760, 720, 2835, 720, color=RED, sw=2.2, dashed=True, marker="arrow-red", arrow=False),
        text(2860, 731, "状态关系：", size=30, weight=500, fill="#4D5550"),
        text(3030, 731, "transitsTo / degradesTo", size=30, weight=600, fill=RED),
    ]

    # 6. Threat / Risk / Response (7 classes, Extension subtypes removed).
    s += [
        node(4240, 340, 500, 84, "SecurityThreat", bold=True, size=34),
        node(3845, 610, 390, 76, "PhysicalThreat", size=27),
        node(4690, 610, 440, 76, "EnvironmentalThreat", size=26),
        node(4240, 960, 500, 84, "SecurityRisk", bold=True, size=34),
        node(3845, 1230, 390, 76, "CollisionRisk", size=27),
        node(4690, 1230, 440, 76, "DebrisRisk", size=28),
        node(4240, 1640, 500, 84, "ResponseMeasure", bold=True, size=33),
        node(3845, 1910, 390, 76, "AvoidanceMeasure", size=26),
        subclass("M4040,610 L4330,424"), subclass("M4910,610 L4650,424"),
        subclass("M4040,1230 L4330,1044"), subclass("M4910,1230 L4650,1044"),
        subclass("M4040,1910 L4330,1724"),
        # producesRisk: direct corridor right of EnvironmentalThreat.
        path("M4740,382 L5145,382 L5145,1682 L4740,1682", id_="requiresResponseMeasure"), label(4942, 1665, "requiresResponseMeasure", size=24, width=315),
        path("M4240,1682 L3788,1682 L3788,1002 L4240,1002", id_="mitigatesRisk"), label(3906, 1500, "mitigatesRisk", size=24, width=185),
    ]

    # Cross-module semantics use reserved corridors and orthogonal routes.
    s += [
        # SpaceEvent to spatial context, split above and below the SpaceObject hierarchy.
        path("M1600,365 L1165,365 L1165,300 L345,300 L345,340", id_="involvesObject"), label(980, 285, "involvesObject", size=25, width=195),
        path("M1600,405 L1215,405 L1215,381 L1010,381", id_="occursInOrbit"), label(1195, 365, "occursInOrbit", size=25, width=190),
        # Event and causal evidence use the narrow gutter between left and centre modules.
        path("M1600,426 L1168,426 L1168,1330 L890,1330 L890,1380", id_="detectedFromData"), label(1030, 1313, "detectedFromData", size=25, width=225),
        path("M1600,1818 L1175,1818 L1175,1510 L890,1510 L890,1462", id_="hasCausalEvidence"), label(1175, 1745, "hasCausalEvidence", size=24, width=245),
        # CausalAssertion has two parallel semantic roles with the same class target.
        # The vertical run stays left of the OrbitManeuverEvent box and the temporal-relation note.
        path("M1850,1785 L1850,1500 L1215,1500 L1215,426 L1600,426", id_="hasCause_hasEffect"), label(1650, 1483, "hasCause / hasEffect", size=25, width=275),
        # Event to state: a short cross-module rule-generated link.
        path("M2100,383 L2525,383 L2525,577 L2860,577", color=RED, sw=2.5, dashed=True, marker="arrow-red", id_="leadsToState"),
        label(2525, 365, "leadsToState", color=RED, size=25, width=185),
        # Event to threat through the free top corridor.
        path("M2100,340 L2100,145 L4780,145 L4780,382 L4740,382", id_="indicatesThreat"), label(3310, 135, "indicatesThreat", size=25, width=195),
        # SecurityRisk to SituationState via their shared gutter.
        path("M4240,1002 L3788,1002 L3788,577 L3460,577", id_="riskLeadsToState"), label(3788, 965, "riskLeadsToState", size=24, width=215),
    ]

    s.append('</svg>')
    return "\n".join(s)


def main() -> None:
    SVG_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SVG_PATH.write_text(generate_svg(), encoding="utf-8")
    content = {
        "figure": "图3-1 TC-SSSAO的上层概念体系",
        "figure": "figure3_1_concept",
        "nature": "publication-layout vector redraw based on audited OWL content; not a Protégé/OntoGraf raw export",
        "sources": [
            "ontology/tc_sssao.owl",
            "paper/Chinese/sections/chapter3_ontology.tex",
            "docs/figures/sources/fig3_1/class_inventory_final_drawing.tsv",
            "docs/figures/sources/fig3_1/relation_inventory_final_drawing.tsv",
        ],
        "canvas": {"width": W, "height": H},
        "class_modules": CLASS_MODULES,
        "subclass_edges": [{"child": child, "parent": parent, "direction": "child-to-parent"} for child, parent in SUBCLASS_EDGES],
        "property_edges": PROPERTY_EDGES,
        "representative_descendants_without_subclass_edges": [],
        "legend": [
            "实线箭头：模式层/显式语义关系",
            "红色虚线箭头：规则可生成的实例关系",
            "细实线：subClassOf",
            "不同底色：不同知识模块",
        ],
    }
    AUDIT_PATH.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    print(SVG_PATH)
    print(AUDIT_PATH)


if __name__ == "__main__":
    main()
