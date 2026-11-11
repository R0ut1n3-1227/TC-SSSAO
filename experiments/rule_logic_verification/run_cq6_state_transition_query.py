"""CQ6 端到端 SPARQL 查询：B3 规则场景状态转移关系（人工构造数据，非真实历史事件）。

在通用规则逻辑验证场景（experiments/rule_logic_verification）的既有输出图上
执行 queries/query_state_transition.rq：
- graph_before.ttl  = 推理前图（仅原始输入，不声明任何
  transitsTo/degradesTo/recoversTo）；
- graph_after_full.ttl = 固定点推理后图（含 B2/B3 桥接规则产物）。

本脚本只读图执行查询，不重新运行规则推理；请先运行
experiments/rule_logic_verification/run_rule_scenario.py 生成两图。

每条返回三元组的归因按图结构如实判定：
- 若推理前图已含该三元组 → explicit；
- 若图中存在 StateTransition 实例以同一源/目标为 hasSourceState/hasTargetState
  → B2（显式转换投影）；
- 否则 → B3（相邻同目标对快照演化桥接）。
本场景输入不含 StateTransition 实例（B3 不创建 StateTransition），
因此预期全部归因为 B3，但该结论由图结构计算得出，不硬编码。

输出（experiments/rule_logic_verification/outputs/）：
- cq6_state_transition_query_results.csv：query_name, graph_stage,
  sourceState, relation, targetState, attribution, row_count（该阶段总行数）
- cq6_state_transition_query_results.json：查询名、两阶段图路径、
  before/after 行数、分关系计数（transitsTo/degradesTo/recoversTo）、
  全部绑定与归因。
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from rdflib import Graph, Namespace, URIRef


def find_project_root(start: Path) -> Path:
    for p in [start.resolve(), *start.resolve().parents]:
        if (p / "ontology" / "tc_sssao.owl").exists():
            return p
    raise RuntimeError("未找到TC-SSSAO工程根目录。")


BASE = find_project_root(Path(__file__).parent)
EXP = Path(__file__).resolve().parent
OUT = EXP / "outputs"
QUERY_FILE = EXP / "queries" / "query_state_transition.rq"
BEFORE = OUT / "graph_before.ttl"
AFTER = OUT / "graph_after_full.ttl"

ONTO = Namespace("https://w3id.org/tc-sssao#")
RELATIONS = (ONTO.transitsTo, ONTO.degradesTo, ONTO.recoversTo)
QUERY_NAME = "query_state_transition"


def attribution(graph: Graph, s: URIRef, p: URIRef, o: URIRef,
                before_graph: Graph) -> str:
    """按图结构判定单条结果三元组的来源（不硬编码）。"""
    if (s, p, o) in before_graph:
        return "explicit"
    # B2：存在显式 StateTransition 实例桥接同一源/目标
    for trans in graph.subjects(ONTO.hasSourceState, s):
        if (trans, ONTO.hasTargetState, o) in graph:
            return "B2"
    return "B3"


def run_stage(graph: Graph, query_text: str) -> list[tuple[URIRef, URIRef, URIRef]]:
    rows = []
    for row in graph.query(query_text):
        rows.append((row[0], row[1], row[2]))
    return rows


def main() -> int:
    for path, hint in ((QUERY_FILE, "缺少 CQ6 查询文件"),
                       (BEFORE, "缺少推理前图，请先运行 run_rule_scenario.py"),
                       (AFTER, "缺少推理后图，请先运行 run_rule_scenario.py")):
        if not path.exists():
            print(f"{hint}：{path}", file=sys.stderr)
            return 2

    query_text = QUERY_FILE.read_text(encoding="utf-8")
    g_before = Graph(); g_before.parse(BEFORE, format="turtle")
    g_after = Graph(); g_after.parse(AFTER, format="turtle")

    before_rows = run_stage(g_before, query_text)
    after_rows = run_stage(g_after, query_text)

    counts = {str(rel): sum(1 for _, p, _ in after_rows if p == rel)
              for rel in RELATIONS}

    csv_path = OUT / "cq6_state_transition_query_results.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["query_name", "graph_stage", "sourceState",
                         "relation", "targetState", "attribution", "row_count"])
        for s, p, o in before_rows:
            writer.writerow([QUERY_NAME, "before_reasoning", str(s), str(p),
                             str(o), "explicit", len(before_rows)])
        for s, p, o in after_rows:
            writer.writerow([QUERY_NAME, "after_reasoning", str(s), str(p),
                             str(o),
                             attribution(g_after, s, p, o, g_before),
                             len(after_rows)])

    doc = {
        "query_name": QUERY_NAME,
        "query_file": str(QUERY_FILE.relative_to(BASE)),
        "graph_before": str(BEFORE.relative_to(BASE)),
        "graph_after": str(AFTER.relative_to(BASE)),
        "before_count": len(before_rows),
        "after_count": len(after_rows),
        "transitsTo_count": counts[str(ONTO.transitsTo)],
        "degradesTo_count": counts[str(ONTO.degradesTo)],
        "recoversTo_count": counts[str(ONTO.recoversTo)],
        "before_rows": [
            {"sourceState": str(s), "relation": str(p), "targetState": str(o)}
            for s, p, o in before_rows],
        "after_rows": [
            {"sourceState": str(s), "relation": str(p), "targetState": str(o),
             "attribution": attribution(g_after, s, p, o, g_before)}
            for s, p, o in after_rows],
    }
    json_path = OUT / "cq6_state_transition_query_results.json"
    json_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                         encoding="utf-8")

    print(f"查询：{QUERY_FILE}")
    print(f"推理前图：{BEFORE}（{len(g_before)} 三元组）→ {len(before_rows)} 行")
    print(f"推理后图：{AFTER}（{len(g_after)} 三元组）→ {len(after_rows)} 行")
    print(f"  transitsTo={counts[str(ONTO.transitsTo)]} "
          f"degradesTo={counts[str(ONTO.degradesTo)]} "
          f"recoversTo={counts[str(ONTO.recoversTo)]}")
    for row in doc["after_rows"]:
        print(f"  [{row['attribution']}] {row['sourceState']} -{row['relation']}-> {row['targetState']}")
    print(f"CSV：{csv_path}")
    print(f"JSON：{json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
