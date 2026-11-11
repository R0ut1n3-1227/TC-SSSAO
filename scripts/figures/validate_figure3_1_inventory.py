"""图3-1清单与正式本体（ontology/tc_sssao.owl）一致性校验（Final Manuscript-Sync 新增）。

校验内容（只读，不修改任何本体或论文文件）：
1. class_inventory_final_drawing.tsv 中每个类都是本体中的具名类；
2. direct_named_parent 与本体 rdfs:subClassOf 直接父类完全一致
   （CollisionRiskEvent 必须同时记录 RiskEvent 与 SpatialRelationEvent 双重继承）；
3. 必查结构：RocketBody/SpaceDebris ⊑ ArtificialSpaceObject、Satellite ⊑ Spacecraft、
   CausalAssertion 的5个直接子类（Direct/Indirect/Promoting/Inhibiting/MultiCause）；
4. 生成器 CLASS_MODULES / SUBCLASS_EDGES 与 TSV 完全一致（双向）；
5. relation_inventory_final_drawing.tsv 中每个属性都是本体 ObjectProperty，
   owl_domain/owl_range 与本体声明完全一致；
6. leadsToState 的生成依据必须覆盖 R5—R8（而非仅 R5）。

输出 data/current/figure3_1_inventory_validation.json；全部通过退出码 0，否则 1。
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from rdflib import Graph, Namespace, RDF, RDFS, OWL

ROOT = Path(__file__).resolve().parents[2]
OWL_PATH = ROOT / "ontology" / "tc_sssao.owl"
BASE = ROOT / "docs" / "figures" / "sources" / "fig3_1"
CLASS_TSV = BASE / "class_inventory_final_drawing.tsv"
REL_TSV = BASE / "relation_inventory_final_drawing.tsv"
GEN_PATH = BASE / "generate_figure3_1.py"
OUT = ROOT / "data" / "current" / "figure3_1_inventory_validation.json"

TC = Namespace("https://w3id.org/tc-sssao#")

CHECKS: list[dict] = []


def record(name: str, ok: bool, detail: str = ""):
    CHECKS.append({"check": name, "pass": bool(ok), "detail": detail})


def read_tsv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def main() -> int:
    g = Graph()
    g.parse(data=OWL_PATH.read_bytes(), format="xml")

    def owl_parents(cls: str) -> list[str]:
        return sorted(
            str(o).rsplit("#", 1)[-1]
            for o in g.objects(TC[cls], RDFS.subClassOf)
            if str(o).startswith(str(TC))
        )

    # --- 1. class inventory vs OWL ---
    class_rows = read_tsv(CLASS_TSV)
    seen = set()
    tsv_classes = {}
    for row in class_rows:
        cls = row["class"]
        if cls in seen:
            record(f"类清单无重复行: {cls}", False, "重复出现")
            continue
        seen.add(cls)
        tsv_classes[cls] = row

    for cls, row in tsv_classes.items():
        named = (TC[cls], RDF.type, OWL.Class) in g
        record(f"类存在于本体: {cls}", named)
        if not named:
            continue
        want = [] if row["direct_named_parent"] == "-" else sorted(
            p.strip() for p in row["direct_named_parent"].split(",")
        )
        got = owl_parents(cls)
        record(f"直接父类一致: {cls}", want == got,
               f"tsv={row['direct_named_parent']} owl={','.join(got) or '-'}")

    # --- 2. required structure ---
    required = {
        "RocketBody": ["ArtificialSpaceObject"],
        "SpaceDebris": ["ArtificialSpaceObject"],
        "Satellite": ["Spacecraft"],
        "CollisionRiskEvent": ["RiskEvent", "SpatialRelationEvent"],
        "DirectCausalAssertion": ["CausalAssertion"],
        "IndirectCausalAssertion": ["CausalAssertion"],
        "PromotingCausalAssertion": ["CausalAssertion"],
        "InhibitingCausalAssertion": ["CausalAssertion"],
        "MultiCauseAssertion": ["CausalAssertion"],
    }
    for cls, parents in required.items():
        record(f"必查结构: {cls} ⊑ {'+'.join(parents)}",
               owl_parents(cls) == sorted(parents),
               f"owl={','.join(owl_parents(cls)) or '-'}")

    # --- 3. generator constants vs TSV (both directions) ---
    import importlib.util
    spec = importlib.util.spec_from_file_location("gen31", GEN_PATH)
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)

    gen_classes = {c for classes in gen.CLASS_MODULES.values() for c in classes}
    tsv_class_set = set(tsv_classes)
    record("生成器类集合 == TSV类集合", gen_classes == tsv_class_set,
           f"仅生成器={sorted(gen_classes - tsv_class_set)} 仅TSV={sorted(tsv_class_set - gen_classes)}")

    tsv_edges = set()
    for cls, row in tsv_classes.items():
        if "direct parent shown" in row["hierarchy_handling"]:
            for p in row["direct_named_parent"].split(","):
                tsv_edges.add((cls, p.strip()))
    gen_edges = set(gen.SUBCLASS_EDGES)
    record("生成器subClass边 == TSV'parent shown'边", gen_edges == tsv_edges,
           f"仅生成器={sorted(gen_edges - tsv_edges)} 仅TSV={sorted(tsv_edges - gen_edges)}")

    hidden = [(c, r) for c, r in tsv_classes.items() if "hidden" in r["hierarchy_handling"]]
    bad_hidden = [(c, r) for c, r in hidden
                  if any(c == child for child, _ in gen_edges)]
    record("hidden父类行未绘制假subClass边", not bad_hidden, f"违规={bad_hidden}")

    # --- 4. relation inventory vs OWL ---
    for row in read_tsv(REL_TSV):
        prop = row["property"]
        uri = TC[prop]
        is_op = (uri, RDF.type, OWL.ObjectProperty) in g
        record(f"属性为ObjectProperty: {prop}", is_op)
        if not is_op:
            continue
        dom = sorted(str(o).rsplit("#", 1)[-1] for o in g.objects(uri, RDFS.domain))
        rng = sorted(str(o).rsplit("#", 1)[-1] for o in g.objects(uri, RDFS.range))
        record(f"domain一致: {prop}", dom == [row["owl_domain"]],
               f"tsv={row['owl_domain']} owl={','.join(dom)}")
        record(f"range一致: {prop}", rng == [row["owl_range"]],
               f"tsv={row['owl_range']} owl={','.join(rng)}")

    lt_rows = [r for r in read_tsv(REL_TSV) if r["property"] == "leadsToState"]
    record("leadsToState依据覆盖R5—R8",
           bool(lt_rows) and "R5—R8" in lt_rows[0]["basis"],
           f"basis={lt_rows[0]['basis'] if lt_rows else '缺行'}")

    # --- report ---
    n_fail = sum(1 for c in CHECKS if not c["pass"])
    doc = {
        "check": "figure 3-1 inventory vs canonical OWL",
        "overall": "PASS" if n_fail == 0 else "FAIL",
        "total": len(CHECKS),
        "failed": n_fail,
        "checks": CHECKS,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    for c in CHECKS:
        mark = "PASS" if c["pass"] else "FAIL"
        line = f"[{mark}] {c['check']}"
        if not c["pass"] and c["detail"]:
            line += f"  — {c['detail']}"
        print(line)
    print(f"\nOVERALL: {doc['overall']} ({len(CHECKS) - n_fail}/{len(CHECKS)})")
    print(f"输出：{OUT}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
