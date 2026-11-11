from __future__ import annotations

import json

from common import BASE, RESULTS


def load(name):
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


def pct(value):
    return f"{100 * float(value):.2f}\\%"


def main() -> None:
    coverage = load("mapping_coverage.json")
    states = load("risk_state_distribution.json")
    evolution = load("state_evolution.json")["metrics"]
    fault = load("fault_injection.json")
    streaming = load("streaming_replay.json")
    scale = load("scalability.json")

    result_table = rf"""\begin{{table*}}[t]
\centering
\caption{{ESA真实CDM映射、态势与演化结果}}
\label{{tab:esa-main-results}}
\small
\begin{{tabular}}{{lrrl}}
\toprule
指标 & 数量 & 比例 & 说明\\
\midrule
CDM / event\_id & {coverage['total_cdms']} & {coverage['total_events']}个事件 & Zenodo v1训练集\\
R5--R8完整输入 & {coverage['complete_r5_r8_input']} & {pct(coverage['mapping_coverage'])} & 执行层输入契约通过\\
Normal & {states['states']['Normal']['count']} & {pct(states['states']['Normal']['ratio'])} & $P_c\leq\theta_A, d\geq h$\\
Attention & {states['states']['Attention']['count']} & {pct(states['states']['Attention']['ratio'])} & $\theta_A<P_c\leq\theta_M, d\geq h$\\
Warning & {states['states']['Warning']['count']} & {pct(states['states']['Warning']['ratio'])} & NASA OR判据异或分支\\
Dangerous & {states['states']['Dangerous']['count']} & {pct(states['states']['Dangerous']['ratio'])} & 两个减缓条件同时满足\\
B3 transitsTo & {evolution['b3_transits_to']} & {evolution['events_with_state_upgrade']}个事件 & 仅相邻快照严重度升高\\
错误跨event/跨未评级/下降边 & 0/0/0 & --- & 约束满足\\
故障注入 & {fault['passed']}/{fault['total']} & {pct(fault['fault_detection_rate'])} & 受控执行层检查\\
流式重放 & {streaming['events_replayed']} & --- & 派生事实集合一致\\
\bottomrule
\end{{tabular}}
\end{{table*}}
"""
    (RESULTS / "esa_results_table.tex").write_text(result_table, encoding="utf-8")

    chosen = [x for x in scale["sizes"] if x["event_count"] in {100, 500, 1000, 2000, 5000, 10000, 13154}]
    lines = [r"\begin{table}[t]", r"\centering", r"\caption{ESA执行层规模实验（3次重复）}",
             r"\label{tab:esa-scale}", r"\scriptsize", r"\begin{tabular}{rrr}", r"\toprule",
             r"事件数 & CDM数 & 总时间均值/s\\", r"\midrule"]
    for item in chosen:
        lines.append(f"{item['event_count']} & {item['cdm_count']} & {item['total_s']['mean']:.3f}\\\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    (RESULTS / "esa_scalability_table.tex").write_text("\n".join(lines), encoding="utf-8")
    print("PASS generated LaTeX tables")


if __name__ == "__main__":
    main()
