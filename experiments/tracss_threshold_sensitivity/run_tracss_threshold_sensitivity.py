"""TraCSS R5-R8 threshold sensitivity experiment.

Formal replacement candidate for the earlier ESA-based threshold
sensitivity experiment (experiments/esa_threshold_sensitivity).

Read-only on: the audited TraCSS normalized adapter output
(experiments/tracss/data/tracss_sfsh_normalized.csv.gz), the tracss
adapter pipeline, all ESA experiments, the rules, the ontology, and the
paper.  Thresholds are varied in memory only; the frozen formal baseline
(theta_A=1e-7, theta_M=1e-4) is never modified.  No sample is dropped,
added, or filtered to force any distribution.

Hard gates (abort before any sweep if violated):
  1. normalized data: 283,595 rows, 283,557 preflight-pass rows;
  2. frozen-baseline run reproduces exactly
     Normal=86,585 / Attention=196,666 / Warning=306 / Dangerous=0;
  3. the parameterized in-memory classifier used for the sweeps agrees
     with the tracss adapter's own classify_states on every row at the
     baseline thresholds (semantic lock; that implementation was itself
     verified row-identical to the ESA one).
"""
from __future__ import annotations
import sys
sys.dont_write_bytecode = True
import importlib.util
import json
from pathlib import Path
import numpy as np
import pandas as pd
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TRACSS = ROOT / 'experiments' / 'tracss'
NORMALIZED = TRACSS / 'data' / 'tracss_sfsh_normalized.csv.gz'
TRACSS_COMMON = TRACSS / 'scripts' / 'common.py'
ESA_SENSITIVITY = ROOT / 'experiments' / 'esa_threshold_sensitivity' / 'outputs' / 'threshold_sensitivity_results.json'
RESULTS = HERE / 'results'
THETA_A_BASE = 1e-07
THETA_M_BASE = 0.0001
BASELINE_COUNTS = {'Normal': 86585, 'Attention': 196666, 'Warning': 306, 'Dangerous': 0}
EXPECTED_ROWS = 283595
EXPECTED_VALID = 283557
A_GRID = [1e-09, 1e-08, 1e-07, 1e-06, 1e-05]
B_GRID = [1e-06, 1e-05, 0.0001, 0.001, 0.01]
C_GRID_A = [1e-08, 1e-07, 1e-06]
C_GRID_M = [1e-05, 0.0001, 0.001]
DANGEROUS_GRID = [1e-07, 1e-06, 1e-05, 0.0001, 0.001, 0.01]
STATE_ORDER = ('Normal', 'Attention', 'Warning', 'Dangerous')

def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()

def load_tracss_classify():
    spec = importlib.util.spec_from_file_location('tracss_common', TRACSS_COMMON)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def classify_param(df: pd.DataFrame, ta: float, tm: float) -> pd.Series:
    """Frozen R5-R8 boolean structure; thresholds varied in memory only.

    R5 Normal:    pc <= ta and d >= h
    R6 Attention: ta < pc <= tm and d >= h
    R7 Warning:   (pc > tm) xor (d < h)
    R8 Dangerous: pc > tm and d < h
    """
    state = pd.Series(pd.NA, index=df.index, dtype='string')
    valid = df['preflight_pass'].astype(bool)
    pc = df['collision_probability']
    high = pc > tm
    close = df['predicted_miss_distance'] < df['combined_hard_body_radius']
    state.loc[valid & ~high & ~close & (pc <= ta)] = 'Normal'
    state.loc[valid & ~high & ~close & (pc > ta)] = 'Attention'
    state.loc[valid & (high ^ close)] = 'Warning'
    state.loc[valid & high & close] = 'Dangerous'
    return state

def independent_masks(vdf: pd.DataFrame, ta: float, tm: float) -> dict:
    """Audit masks recomputed independently of the classifier engine."""
    pc = vdf['collision_probability']
    d = vdf['predicted_miss_distance']
    h = vdf['combined_hard_body_radius']
    return {'Normal': (pc <= ta) & (d >= h), 'Attention': (pc > ta) & (pc <= tm) & (d >= h), 'Warning': (pc > tm) & (d >= h) | (pc <= tm) & (d < h), 'Dangerous': (pc > tm) & (d < h)}

def run_combo(df: pd.DataFrame, baseline_state: pd.Series, ta: float, tm: float) -> dict:
    state = classify_param(df, ta, tm)
    valid_mask = df['preflight_pass'].astype(bool)
    n_valid = int(valid_mask.sum())
    vstate = state[valid_mask]
    bstate = baseline_state[valid_mask]
    counts = {s: int((vstate == s).sum()) for s in STATE_ORDER}
    changed = int((vstate != bstate).sum())
    transitions = {}
    for s_from in STATE_ORDER:
        for s_to in STATE_ORDER:
            key = f'{s_from}->{s_to}'
            transitions[key] = int(((bstate == s_from) & (vstate == s_to)).sum())
    v = df[valid_mask]
    masks = independent_masks(v, ta, tm)
    mask_frame = pd.DataFrame(masks)
    hits = mask_frame.sum(axis=1)
    mask_counts = {k: int(m.sum()) for k, m in masks.items()}
    audit = {'no_state': int(vstate.isna().sum()), 'multi_state': int((hits > 1).sum()), 'overlap': int((hits > 1).sum()), 'gap': int((hits == 0).sum()), 'state_sum': int(sum(counts.values())), 'n_valid': n_valid, 'sum_equals_n': bool(sum(counts.values()) == n_valid), 'theta_A_lt_theta_M': bool(ta < tm), 'engine_counts_equal_mask_counts': counts == mask_counts}
    return {'theta_A': ta, 'theta_M': tm, 'counts': counts, 'delta_vs_baseline': {s: counts[s] - BASELINE_COUNTS[s] for s in STATE_ORDER}, 'changed_samples': changed, 'changed_pct': changed / n_valid * 100.0, 'transitions': transitions, 'audit': audit}

def fmt_combo(rec: dict) -> dict:
    c = rec['counts']
    return {'ta': rec['theta_A'], 'tm': rec['theta_M'], 'N': c['Normal'], 'A': c['Attention'], 'W': c['Warning'], 'D': c['Dangerous'], 'changed': rec['changed_samples'], 'pct': round(rec['changed_pct'], 3)}

def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(NORMALIZED, low_memory=False)
    n_rows = int(len(df))
    n_valid = int(df['preflight_pass'].sum())
    data_identity = {'normalized_csv': rel(NORMALIZED), 'rows_total': n_rows, 'rows_valid': n_valid}
    if n_rows != EXPECTED_ROWS or n_valid != EXPECTED_VALID:
        payload = {'status': 'ABORT', 'reason': 'row/valid counts differ from the audited TraCSS baseline; sweep not executed', 'data_identity': data_identity}
        (RESULTS / 'tracss_threshold_sensitivity_results.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(payload, ensure_ascii=False))
        raise SystemExit(1)
    tracss_common = load_tracss_classify()
    baseline_state = tracss_common.classify_states(df)
    baseline_counts = {s: int((baseline_state == s).sum()) for s in STATE_ORDER}
    engine_state = classify_param(df, THETA_A_BASE, THETA_M_BASE)
    both_na = baseline_state.isna() & engine_state.isna()
    engine_lock_rows = int((~((baseline_state == engine_state) | both_na)).sum())
    baseline_ok = baseline_counts == BASELINE_COUNTS and engine_lock_rows == 0
    if not baseline_ok:
        payload = {'status': 'ABORT', 'reason': 'frozen baseline not reproduced; sweep not executed', 'expected': BASELINE_COUNTS, 'actual': baseline_counts, 'engine_lock_mismatch_rows': engine_lock_rows}
        (RESULTS / 'tracss_threshold_sensitivity_results.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(payload, ensure_ascii=False))
        raise SystemExit(1)
    valid = df[df['preflight_pass']]
    exp_a = [run_combo(df, baseline_state, ta, THETA_M_BASE) for ta in A_GRID]
    exp_b = [run_combo(df, baseline_state, THETA_A_BASE, tm) for tm in B_GRID]
    exp_c = [run_combo(df, baseline_state, ta, tm) for ta in C_GRID_A for tm in C_GRID_M]
    pc_v = valid['collision_probability']
    d_v = valid['predicted_miss_distance']
    h_v = valid['combined_hard_body_radius']
    close_mask = d_v < h_v
    close_rows = valid[close_mask]
    close_samples = [{'event_id': int(r.event_id), 'pc': float(r.collision_probability), 'd_km': float(r.predicted_miss_distance), 'h_km': float(r.combined_hard_body_radius), 'd_over_h': float(r.predicted_miss_distance / r.combined_hard_body_radius)} for r in close_rows.itertuples(index=False)]
    dangerous_scan = []
    for tm in DANGEROUS_GRID:
        state = classify_param(df, THETA_A_BASE, tm)
        vstate = state[df['preflight_pass'].astype(bool)]
        n_dangerous = int((vstate == 'Dangerous').sum())
        n_pc_gt_and_close = int(((pc_v > tm) & close_mask).sum())
        sample_states = {str(s['event_id']): str(vstate[valid['event_id'] == s['event_id']].iloc[0]) for s in close_samples}
        masks = independent_masks(valid, THETA_A_BASE, tm)
        mask_frame = pd.DataFrame(masks)
        hits = mask_frame.sum(axis=1)
        mask_counts = {k: int(m.sum()) for k, m in masks.items()}
        engine_counts = {s: int((vstate == s).sum()) for s in STATE_ORDER}
        dangerous_scan.append({'theta_M': tm, 'theta_A': THETA_A_BASE, 'pc_gt_theta_M_and_d_lt_h_count': n_pc_gt_and_close, 'dangerous_count': n_dangerous, 'close_sample_states': sample_states, 'theta_A_lt_theta_M': bool(THETA_A_BASE < tm), 'audit': {'no_state': int(vstate.isna().sum()), 'multi_state': int((hits > 1).sum()), 'overlap': int((hits > 1).sum()), 'gap': int((hits == 0).sum()), 'sum_equals_n': bool(sum(engine_counts.values()) == int(len(vstate))), 'engine_counts_equal_mask_counts': engine_counts == mask_counts, 'counts': engine_counts}})
    triggered = [r['theta_M'] for r in dangerous_scan if r['dangerous_count'] > 0]
    boundary_pc = max((s['pc'] for s in close_samples), default=None)
    a_normals = [r['counts']['Normal'] for r in exp_a]
    a_warnings = [r['counts']['Warning'] for r in exp_a]
    a_dangerous = [r['counts']['Dangerous'] for r in exp_a]
    b_warnings = [r['counts']['Warning'] for r in exp_b]
    b_normals = [r['counts']['Normal'] for r in exp_b]
    analysis = {'A_normal_monotonic_nondecreasing': bool(all((x <= y for x, y in zip(a_normals, a_normals[1:])))), 'A_warning_constant': len(set(a_warnings)) == 1, 'A_dangerous_constant': len(set(a_dangerous)) == 1, 'A_max_changed_pct': max((r['changed_pct'] for r in exp_a)), 'A_max_adjacent_normal_jump': max((abs(y - x) for x, y in zip(a_normals, a_normals[1:])), default=0), 'B_warning_monotonic_nonincreasing': bool(all((x >= y for x, y in zip(b_warnings, b_warnings[1:])))), 'B_normal_constant': len(set(b_normals)) == 1, 'B_max_changed_pct': max((r['changed_pct'] for r in exp_b)), 'B_warning_range': [min(b_warnings), max(b_warnings)], 'C_normal_depends_only_on_theta_A': all((len({r['counts']['Normal'] for r in exp_c if r['theta_A'] == ta}) == 1 for ta in C_GRID_A)), 'C_warning_depends_only_on_theta_M': all((len({r['counts']['Warning'] for r in exp_c if r['theta_M'] == tm}) == 1 for tm in C_GRID_M)), 'C_dangerous_values': sorted({r['counts']['Dangerous'] for r in exp_c})}
    all_combos = [('A', r) for r in exp_a] + [('B', r) for r in exp_b] + [('C', r) for r in exp_c] + [('DANGEROUS_SCAN', None)] * 0
    coverage = []
    for label, rec in all_combos:
        a = rec['audit']
        coverage.append({'experiment': label, 'theta_A': rec['theta_A'], 'theta_M': rec['theta_M'], 'no_state': a['no_state'], 'multi_state': a['multi_state'], 'overlap': a['overlap'], 'gap': a['gap'], 'sum_equals_n': a['sum_equals_n'], 'theta_A_lt_theta_M': a['theta_A_lt_theta_M'], 'engine_counts_equal_mask_counts': a['engine_counts_equal_mask_counts']})
    scan_audit_ok = all((r['dangerous_count'] == r['pc_gt_theta_M_and_d_lt_h_count'] for r in dangerous_scan))
    scan_coverage_ok = all((r['audit']['no_state'] == 0 and r['audit']['overlap'] == 0 and (r['audit']['gap'] == 0) and r['audit']['sum_equals_n'] and r['audit']['engine_counts_equal_mask_counts'] for r in dangerous_scan))
    coverage_summary = {'combos_checked': len(coverage), 'all_no_state_zero': all((c['no_state'] == 0 for c in coverage)), 'all_multi_state_zero': all((c['multi_state'] == 0 for c in coverage)), 'all_overlap_zero': all((c['overlap'] == 0 for c in coverage)), 'all_gap_zero': all((c['gap'] == 0 for c in coverage)), 'all_sum_equals_n': all((c['sum_equals_n'] for c in coverage)), 'all_engine_eq_mask': all((c['engine_counts_equal_mask_counts'] for c in coverage)), 'combos_with_theta_A_not_lt_theta_M': [{'experiment': c['experiment'], 'theta_A': c['theta_A'], 'theta_M': c['theta_M']} for c in coverage if not c['theta_A_lt_theta_M']], 'dangerous_scan_count_equals_classifier': bool(scan_audit_ok), 'dangerous_scan_coverage_all_ok': bool(scan_coverage_ok), 'dangerous_scan_theta_boundary_points': [r['theta_M'] for r in dangerous_scan if not r['theta_A_lt_theta_M']]}
    esa_ref = {'available': ESA_SENSITIVITY.exists()}
    if ESA_SENSITIVITY.exists():
        esa = json.loads(ESA_SENSITIVITY.read_text(encoding='utf-8'))
        esa_ref.update({'valid_samples': esa['dataset']['valid_cdms'], 'baseline_counts': esa['baseline']['counts'] if 'counts' in esa.get('baseline', {}) else None, 'A_max_changed_ratio': max((r['changed_cdm_ratio_vs_baseline'] for r in esa['experiment_A_theta_A_sweep'])), 'B_warning_counts': {str(r['theta_M']): r['counts']['Warning'] for r in esa['experiment_B_theta_M_sweep']}, 'dangerous_always_zero_in_grid': all((r['counts']['Dangerous'] == 0 for r in esa['experiment_A_theta_A_sweep'] + esa['experiment_B_theta_M_sweep'] + esa['experiment_C_joint_grid'])), 'close_d_lt_h_count': esa['pc_distance_diagnosis']['count_close_d_lt_h'], 'note': "ESA reference extracted from the earlier experiment's outputs; numeric fields only; ESA experiment untouched"})
    result = {'status': 'PASS', 'experiment': 'R5-R8 threshold sensitivity on the audited TraCSS normalized adapter output', 'frozen_baseline': {'theta_A': THETA_A_BASE, 'theta_M': THETA_M_BASE}, 'data_identity': data_identity, 'baseline_reproduction': {'expected': BASELINE_COUNTS, 'actual': baseline_counts, 'matches': True, 'engine_lock_mismatch_rows_vs_tracss_classify': engine_lock_rows}, 'experiment_A_theta_A_sweep': exp_a, 'experiment_B_theta_M_sweep': exp_b, 'experiment_C_joint_grid': exp_c, 'dangerous_special': {'close_samples_d_lt_h': close_samples, 'scan': dangerous_scan, 'dangerous_triggered_at_theta_M': triggered, 'first_trigger_in_grid_descending': max(triggered) if triggered else None, 'exact_boundary': boundary_pc, 'boundary_rule': 'Dangerous for the close sample iff theta_M < its Pc (strict inequality); theta_M equal to Pc keeps it Warning'}, 'structural_analysis': analysis, 'rule_coverage_summary': coverage_summary, 'rule_coverage_per_combo': coverage, 'esa_reference': esa_ref}
    out = RESULTS / 'tracss_threshold_sensitivity_results.json'
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'status': 'PASS', 'baseline': baseline_counts, 'A': [fmt_combo(r) for r in exp_a], 'B': [fmt_combo(r) for r in exp_b], 'dangerous_triggered_at_theta_M': triggered, 'coverage_all_ok': all([coverage_summary['all_no_state_zero'], coverage_summary['all_overlap_zero'], coverage_summary['all_gap_zero'], coverage_summary['all_sum_equals_n'], coverage_summary['all_engine_eq_mask']])}, ensure_ascii=False))
if __name__ == '__main__':
    main()
