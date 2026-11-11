from __future__ import annotations
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from common import ARCHIVE, METADATA, PROCESSED, RESULTS, WORKSPACE, save_json
STEPS = ['01_download_or_verify.py', '02_dataset_audit.py', '03_preprocess_cdm.py', '04_build_rdf.py', '05_preflight_eval.py', '06_risk_state_eval.py', '07_state_evolution_eval.py', '08_fault_injection.py', '09_scalability.py', '10_streaming_replay.py', '11_ablation.py', '12_generate_tables.py', '13_generate_figures.py']

def flatten(prefix: str, value, out: list[dict[str, object]], source: str, script: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            flatten(f'{prefix}.{key}' if prefix else str(key), item, out, source, script)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            flatten(f'{prefix}[{index}]', item, out, source, script)
    elif isinstance(value, (int, float, bool)) or value is None:
        out.append({'metric': prefix, 'value': value, 'source_file': source, 'script': script, 'timestamp': datetime.now(timezone.utc).isoformat()})

def main() -> None:
    manifest_only = '--manifest-only' in sys.argv
    logs = []
    if not manifest_only:
        for step in STEPS:
            completed = subprocess.run([sys.executable, str(Path(__file__).parent / step)], text=True, capture_output=True, encoding='utf-8', errors='replace')
            logs.append({'step': step, 'returncode': completed.returncode, 'stdout_tail': completed.stdout[-4000:], 'stderr_tail': completed.stderr[-4000:]})
            print('PASS' if completed.returncode == 0 else 'FAIL', step)
            if completed.returncode != 0:
                save_json(RESULTS / 'pipeline_log.json', {'status': 'FAIL', 'steps': logs})
                raise SystemExit(completed.returncode)
    metrics: list[dict[str, object]] = []
    source_map = {METADATA / 'download_verification.json': '01_download_or_verify.py', METADATA / 'DATASET_AUDIT.json': '02_dataset_audit.py', PROCESSED / 'preprocess_summary.json': '03_preprocess_cdm.py', RESULTS / 'rdf_50event_report.json': '04_build_rdf.py', RESULTS / 'mapping_coverage.json': '05_preflight_eval.py', RESULTS / 'risk_state_distribution.json': '06_risk_state_eval.py', RESULTS / 'state_evolution.json': '07_state_evolution_eval.py', RESULTS / 'fault_injection.json': '08_fault_injection.py', RESULTS / 'scalability.json': '09_scalability.py', RESULTS / 'streaming_replay.json': '10_streaming_replay.py', RESULTS / 'esa_ablation.json': '11_ablation.py', RESULTS / 'figure_example_event.json': '13_generate_figures.py'}
    for path, script in source_map.items():
        value = json.loads(path.read_text(encoding='utf-8'))
        relative = path.relative_to(WORKSPACE).as_posix()
        flatten('', value, metrics, relative, script)
    save_json(RESULTS / 'results_manifest.json', {'status': 'PASS', 'generated_at': datetime.now(timezone.utc).isoformat(), 'metrics': metrics})
    if not manifest_only:
        save_json(RESULTS / 'pipeline_log.json', {'status': 'PASS', 'steps': logs})
    else:
        previous = json.loads((RESULTS / 'pipeline_log.json').read_text(encoding='utf-8'))
        core_steps = [row for row in previous.get('steps', []) if row.get('step') in STEPS]
        save_json(RESULTS / 'pipeline_log.json', {'status': 'PASS', 'mode': 'manifest-only after completed core pipeline', 'steps': core_steps})
    print(f'ALL PASS; metrics={len(metrics)}')
if __name__ == '__main__':
    main()
