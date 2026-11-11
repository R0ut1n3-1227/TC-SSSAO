"""生成 SHACL 验证报告"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

def _find_project_root(start: Path) -> Path:
    path = start.resolve()
    for parent in [path, *path.parents]:
        if any((parent / marker).exists() for marker in ("pyproject.toml", "requirements.txt")):
            return parent
    raise RuntimeError(f"Could not find project root from {start}")

BASE = _find_project_root(Path(__file__).parent)
sys.path.insert(0, str(BASE))

from rdflib import Graph

from scripts.utils.shacl_utils import shacl_validate_fixed_point, validate_diagnostic_graph_fixed_point

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

OWL = BASE / "ontology" / "tc_sssao.owl"
RULES = BASE / "rules" / "tc_sssao_rules.ttl"
POS = BASE / "rules" / "tc_sssao_test_positive.ttl"
NEG = BASE / "rules" / "tc_sssao_test_negative.ttl"
REPORT = BASE / "data" / "current" / "shacl_validation_report.md"


def run(data_path: Path, label: str) -> tuple[bool, str, int, list[int]]:
    data = Graph()
    data.parse(str(data_path), format="turtle")
    # Both legacy fixtures are partial schema/SHACL contracts, not formal
    # scenario instances (the positive fixture omits the spatial pair).
    runner = validate_diagnostic_graph_fixed_point
    conforms, _, text, _, iterations, additions = runner(data)
    report_text = text + f"\n\nFixed-point iterations: {iterations}\n"
    report_text += f"Domain triple additions per round: {additions}\n"
    return conforms, report_text, iterations, additions


def main():
    REPORT.parent.mkdir(parents=True, exist_ok=True)

    pos_conforms, pos_report, pos_iter, pos_adds = run(POS, "positive")
    neg_conforms, neg_report, neg_iter, neg_adds = run(NEG, "negative")

    lines = []
    lines.append("# TC-SSSAO SHACL 验证报告")
    lines.append("")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**规则文件**: `{RULES.relative_to(BASE)}`")
    lines.append(f"**推理模式**: `rdfs` + `sh:advanced`，外部迭代至完整数据图同构固定点")
    lines.append("")
    lines.append("固定点说明：第一轮将主本体作为本体图注入工作图，完成 RDFS 展开与 SHACL 规则推导；")
    lines.append("后续轮次复用同一工作图，不再重复注入本体及部署配置。完整图一轮前后同构才判定收敛，")
    lines.append("包括未列入领域计数的谓词及匿名节点结构；忽略单纯空白节点标签重命名。")
    lines.append("每轮新增领域三元组仅作历史口径的诊断统计，不作为停止条件。未收敛达到上限则失败。")
    lines.append("")

    lines.append("## 正例测试数据")
    lines.append("")
    lines.append(f"- **文件**: `{POS.relative_to(BASE)}`")
    lines.append(f"- **预期**: 全部通过")
    lines.append(f"- **结果**: {'通过 ✅' if pos_conforms else '未通过 ❌'}")
    lines.append(f"- **收敛轮数**: {pos_iter}")
    lines.append(f"- **每轮新增领域三元组**: {pos_adds}")
    lines.append("")
    lines.append("```")
    lines.append(pos_report)
    lines.append("```")
    lines.append("")

    lines.append("## 负例测试数据")
    lines.append("")
    lines.append(f"- **文件**: `{NEG.relative_to(BASE)}`")
    lines.append(f"- **预期**: 至少一个 violation")
    lines.append(f"- **结果**: {'未通过（符合预期）✅' if not neg_conforms else '意外通过 ❌'}")
    lines.append(f"- **收敛轮数**: {neg_iter}")
    lines.append(f"- **每轮新增领域三元组**: {neg_adds}")
    lines.append("")
    lines.append("```")
    lines.append(neg_report)
    lines.append("```")
    lines.append("")

    lines.append("## 汇总")
    lines.append("")
    all_ok = pos_conforms and (not neg_conforms)
    lines.append(f"- 正例通过: {'是' if pos_conforms else '否'}")
    lines.append(f"- 负例触发: {'是' if not neg_conforms else '否'}")
    lines.append(f"- **总体**: {'通过 ✅' if all_ok else '未通过 ❌'}")
    lines.append("")

    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"SHACL report saved: {REPORT}")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
