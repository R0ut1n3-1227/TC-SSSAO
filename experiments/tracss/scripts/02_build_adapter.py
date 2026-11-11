"""02 - Build the TraCSS -> TC-SSSAO standard-field adapter output.

Reads the raw SFSH DiscreteHBR answer key and the per-object HBR mapping,
then emits one normalized row per conjunction with the standard fields:

    event_id                    <- conj_id
    object1_id                  <- obj1
    object2_id                  <- obj2
    tca                         <- epoch (UTC, as published)
    collision_probability       <- prob        (dimensionless, 1:1)
    predicted_miss_distance     <- min_range   (km, 1:1)
    combined_hard_body_radius   <- (HBR[obj1] + HBR[obj2]) / 1000  (km)

Every unit transformation is explicit and recorded in adapter_summary.json.
Raw files are never modified.  The output gzip uses mtime=0 for deterministic compressed output.
"""
from __future__ import annotations
import gzip
import json
import numpy as np
import pandas as pd
from common import DATA, NORMALIZED_CSV, RESULTS, SFSH_CSV, SIZE_CSV, ensure_dirs, load_hbr_map, load_sfsh, rel, save_json
UNIT_TRANSFORMS = {'collision_probability': "prob, dimensionless, copied 1:1 (no log transform; the ESA 'risk' column needed pc = 10**risk, TraCSS does not)", 'predicted_miss_distance': "min_range, already in km per the User's Guide Table 5, copied 1:1", 'combined_hard_body_radius': '(HBR[obj1] + HBR[obj2]) / 1000; per-object HBR is in metres (radius), combined h(e) is expressed in km to match min_range', 'tca': 'epoch, UTC string, copied 1:1 (jdate retained for cross-check)'}

def main() -> None:
    ensure_dirs()
    sfsh = load_sfsh()
    hbr = load_hbr_map()
    hbr_lookup = hbr.set_index('catalog_num')['hbr_m']
    df = pd.DataFrame(index=sfsh.index)
    df['event_id'] = sfsh['conj_id']
    df['object1_id'] = sfsh['obj1']
    df['object2_id'] = sfsh['obj2']
    df['tca'] = sfsh['epoch']
    df['collision_probability'] = sfsh['prob']
    df['predicted_miss_distance'] = sfsh['min_range']
    df['hbr1_m'] = sfsh['obj1'].map(hbr_lookup)
    df['hbr2_m'] = sfsh['obj2'].map(hbr_lookup)
    df['combined_hard_body_radius'] = (df['hbr1_m'] + df['hbr2_m']) / 1000.0
    df['run_id'] = sfsh['run_id']
    df['met_criteria1'] = sfsh['met_criteria1']
    df['met_criteria2'] = sfsh['met_criteria2']
    df['dilution'] = sfsh['dilution']
    df['mahalanobis_distance'] = sfsh['mdistance']
    df['vrel_km_s'] = sfsh['Vrel']
    df['jdate'] = sfsh['jdate']
    df['obj1_filename'] = sfsh['obj1_filename']
    df['obj2_filename'] = sfsh['obj2_filename']
    df['valid_pc'] = np.isfinite(df['collision_probability']) & df['collision_probability'].between(0.0, 1.0, inclusive='both')
    df['valid_distance'] = np.isfinite(df['predicted_miss_distance']) & (df['predicted_miss_distance'] >= 0)
    df['valid_hbr'] = np.isfinite(df['combined_hard_body_radius']) & (df['combined_hard_body_radius'] > 0)
    epoch = pd.to_datetime(df['tca'], format='%Y-%m-%d %H:%M:%S.%f', errors='coerce')
    df['valid_time'] = epoch.notna().to_numpy()
    df['valid_roles'] = (df['object1_id'] > 0) & (df['object2_id'] > df['object1_id'])
    df['duplicate_exact_row'] = sfsh.duplicated(keep=False).to_numpy()
    df['preflight_pass'] = df['valid_pc'] & df['valid_distance'] & df['valid_hbr'] & df['valid_time'] & df['valid_roles'] & ~df['duplicate_exact_row']
    reasons = []
    for row in df.itertuples(index=False):
        current = []
        if not row.valid_pc:
            current.append('missing Pc (NULL prob)' if pd.isna(row.collision_probability) else 'invalid Pc')
        if not row.valid_distance:
            current.append('missing distance' if pd.isna(row.predicted_miss_distance) else 'invalid distance')
        if not row.valid_hbr:
            current.append('missing HBR mapping' if pd.isna(row.combined_hard_body_radius) else 'invalid HBR')
        if not row.valid_time:
            current.append('missing/unparseable TCA')
        if not row.valid_roles:
            current.append('object role failure')
        if row.duplicate_exact_row:
            current.append('duplicate row')
        reasons.append('; '.join(current))
    df['rejection_reason'] = pd.Series(reasons, index=df.index, dtype='string')
    with open(NORMALIZED_CSV, 'wb') as fh, gzip.GzipFile(filename='', mode='wb', fileobj=fh, mtime=0) as gz:
        df.to_csv(gz, index=False, float_format='%.15g')
    summary = {'status': 'PASS', 'rows': int(len(df)), 'unique_conjunctions': int(df['event_id'].nunique()), 'unique_object_pairs': int(pd.MultiIndex.from_arrays([df['object1_id'], df['object2_id']]).nunique()), 'unique_objects': int(pd.concat([df['object1_id'], df['object2_id']]).nunique()), 'unit_transforms': UNIT_TRANSFORMS, 'preflight_pass': int(df['preflight_pass'].sum()), 'preflight_reject': int((~df['preflight_pass']).sum()), 'rejection_reason_counts': {str(k): int(v) for k, v in df.loc[~df['preflight_pass'], 'rejection_reason'].value_counts().items()}, 'inputs': {'sfsh_csv': {'path': rel(SFSH_CSV)}, 'size_csv': {'path': rel(SIZE_CSV)}}, 'output': {'path': rel(NORMALIZED_CSV), 'standard_fields': ['event_id', 'object1_id', 'object2_id', 'tca', 'collision_probability', 'predicted_miss_distance', 'combined_hard_body_radius']}}
    save_json(RESULTS / 'adapter_summary.json', summary)
    print(json.dumps({'status': 'PASS', 'rows': summary['rows'], 'preflight_pass': summary['preflight_pass'], 'preflight_reject': summary['preflight_reject']}, ensure_ascii=False))
if __name__ == '__main__':
    main()
