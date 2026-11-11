from __future__ import annotations
import json
from datetime import date
import pandas as pd
from common import ARCHIVE, DATASET_DOI, DATASET_URL, METADATA, RAW, WORKSPACE, locate_train_csv, save_json

def audit_csv(path):
    df = pd.read_csv(path, low_memory=False)
    event_count = int(df['event_id'].nunique(dropna=True)) if 'event_id' in df else None
    duplicates = int(df.duplicated().sum())
    duplicate_event_time = int(df.duplicated(['event_id', 'time_to_tca']).sum()) if {'event_id', 'time_to_tca'} <= set(df.columns) else None
    return {'file': path.name, 'bytes': path.stat().st_size, 'rows': int(len(df)), 'unique_events': event_count, 'columns': int(len(df.columns)), 'exact_duplicate_rows': duplicates, 'duplicate_event_time_rows': duplicate_event_time, 'missing_values': {str(k): int(v) for k, v in df.isna().sum().items()}}

def main() -> None:
    csvs = sorted(RAW.glob('*.csv'))
    if not csvs:
        raise FileNotFoundError('Run 01_download_or_verify.py first')
    audits = [audit_csv(path) for path in csvs]
    train = locate_train_csv()
    train_audit = next((item for item in audits if item['file'] == train.name))
    expected = {'training_rows': 162634, 'training_unique_events': 13154, 'columns': 103, 'testing_rows': 24484, 'testing_unique_events': 2167}
    checks = {'training_rows': train_audit['rows'] == expected['training_rows'], 'training_unique_events': train_audit['unique_events'] == expected['training_unique_events'], 'training_columns': train_audit['columns'] == expected['columns']}
    status = 'PASS' if all(checks.values()) else 'DATASET_IDENTITY_MISMATCH_STOP'
    output = {'status': status, 'dataset': 'ESA Collision Avoidance Challenge dataset', 'version': 'Zenodo v1', 'doi': DATASET_DOI, 'source': DATASET_URL, 'download_date': str(date.today()), 'official_claims': expected, 'checks': checks, 'files': audits}
    save_json(METADATA / 'DATASET_AUDIT.json', output)
    lines = ['# DATASET_AUDIT', '', f'- Status: **{status}**', '- Dataset: ESA Collision Avoidance Challenge dataset', '- Version: Zenodo v1 (published 2021-01-25)', f'- DOI: `{DATASET_DOI}`', f'- Source: {DATASET_URL}', f'- Download date: {date.today()}', '', '## Official-count verification', '', '| Claim | Official | Actual | Result |', '|---|---:|---:|---|', f"| Training rows | 162634 | {train_audit['rows']} | {('PASS' if checks['training_rows'] else 'FAIL')} |", f"| Training unique events | 13154 | {train_audit['unique_events']} | {('PASS' if checks['training_unique_events'] else 'FAIL')} |", f"| Columns | 103 | {train_audit['columns']} | {('PASS' if checks['training_columns'] else 'FAIL')} |", '', '## File inventory', '', '| File | Rows | Events | Columns | Exact duplicates | Duplicate event/time |', '|---|---:|---:|---:|---:|---:|']
    for item in audits:
        lines.append(f"| {item['file']} | {item['rows']} | {item['unique_events']} | {item['columns']} | {item['exact_duplicate_rows']} | {item['duplicate_event_time_rows']} |")
    lines += ['', '## Missing-value statistics', '']
    for item in audits:
        lines += [f"### {item['file']}", '', '| Column | Missing |', '|---|---:|']
        lines += [f'| {col} | {count} |' for col, count in item['missing_values'].items()]
        lines.append('')
    (WORKSPACE / 'docs' / 'esa_cdm' / 'DATASET_AUDIT.md').write_text('\n'.join(lines), encoding='utf-8')
    print(status)
    if status != 'PASS':
        raise SystemExit(2)
if __name__ == '__main__':
    main()
