"""01 - Field audit of the raw TraCSS IVV files.

Verifies that actual file headers match the User's Guide Table 5 and the
SFSH Screening Volume Mappings description, then measures coverage needed
by the TC-SSSAO field mapping (Pc / miss distance / per-object HBR).
No semantics are inferred from column names; every mapping decision cites
the guide.
"""
from __future__ import annotations
import json
import numpy as np
import pandas as pd
from common import EXPECTED_SFSH_COLUMNS, EXPECTED_SIZE_COLUMNS, RESULTS, SFSH_CSV, SIZE_CSV, GUIDE_PDF, ensure_dirs, load_hbr_map, load_sfsh, rel, save_json
FIELD_MAPPING = [{'tc_sssao_field': 'Event ID', 'tracss_source': 'conj_id', 'unit': '-', 'direct': True, 'computed': False, 'guide_evidence': "Table 5: 'conj_id - Unique ID for Conjunction'"}, {'tc_sssao_field': 'Object 1', 'tracss_source': 'obj1', 'unit': 'Sat ID', 'direct': True, 'computed': False, 'guide_evidence': "Table 5: 'obj1 - Sat ID of first object'; spec states obj2 > obj1, so obj1 is the lower Sat ID, not necessarily the screening primary"}, {'tc_sssao_field': 'Object 2', 'tracss_source': 'obj2', 'unit': 'Sat ID', 'direct': True, 'computed': False, 'guide_evidence': "Table 5: 'obj2 - Sat ID of second object, obj2 > obj1'"}, {'tc_sssao_field': 'TCA', 'tracss_source': 'epoch (cross-check: jdate)', 'unit': 'UTC', 'direct': True, 'computed': False, 'guide_evidence': "Table 5: 'epoch - TCA in UTC time system'"}, {'tc_sssao_field': 'Collision probability Pc', 'tracss_source': 'prob', 'unit': 'dimensionless', 'direct': True, 'computed': False, 'guide_evidence': "Table 5: 'prob - Pc via Alfano 2004 method'; NULL when covariance metrics not computable"}, {'tc_sssao_field': 'Miss distance d', 'tracss_source': 'min_range', 'unit': 'km', 'direct': True, 'computed': False, 'guide_evidence': "Table 5: 'min_range - Miss distance in km'. NOT 'mdistance': that column is the Mahalanobis distance and must not be mapped to d"}, {'tc_sssao_field': 'Object size/HBR', 'tracss_source': 'AerospaceIVVDataset_20251009a_Size_ScreeningVolumes .csv.gz: HBR per catalog_num', 'unit': 'm (per-object radius)', 'direct': True, 'computed': False, 'guide_evidence': "SFSH Screening Volume Mappings section: 'per-object hard-body radius (HBR) values'; unit pinned to metres by the guide's 0.5 m default HBR and by the ISS (25544) entry of 55.0"}, {'tc_sssao_field': 'Combined HBR h(e)', 'tracss_source': 'HBR[obj1] + HBR[obj2]', 'unit': 'computed in km', 'direct': False, 'computed': True, 'guide_evidence': 'Derived: sum of the two per-object radii, matching the combined hard-body convention of the ESA adapter h(e) = (t_span + c_span) / 2'}]

def main() -> None:
    ensure_dirs()
    sfsh = load_sfsh()
    hbr = load_hbr_map()
    header_sfsh = list(pd.read_csv(SFSH_CSV, nrows=0).columns)
    header_size = list(pd.read_csv(SIZE_CSV, nrows=0).columns)
    structure = {'sfsh_header_matches_guide_table5': header_sfsh == EXPECTED_SFSH_COLUMNS, 'size_header_matches_guide': header_size == EXPECTED_SIZE_COLUMNS}
    epoch = pd.to_datetime(sfsh['epoch'], format='%Y-%m-%d %H:%M:%S.%f', errors='coerce')
    obj1 = sfsh['obj1']
    obj2 = sfsh['obj2']
    facts = {'rows': int(len(sfsh)), 'unique_conj_id': int(sfsh['conj_id'].nunique()), 'run_ids': sorted((int(v) for v in sfsh['run_id'].unique())), 'obj2_gt_obj1_violations': int((obj2 <= obj1).sum()), 'unique_object_pairs': int(pd.MultiIndex.from_arrays([obj1, obj2]).nunique()), 'unique_objects': int(pd.concat([obj1, obj2]).nunique()), 'obj_id_min': int(min(obj1.min(), obj2.min())), 'obj_id_max': int(max(obj1.max(), obj2.max())), 'epoch_min_utc': str(epoch.min()), 'epoch_max_utc': str(epoch.max()), 'epoch_unparseable': int(epoch.isna().sum()), 'screening_window_guide_utc': ['2025-01-01 12:00:00', '2025-01-08 12:00:00'], 'null_counts': {'prob': int(sfsh['prob'].isna().sum()), 'mdistance': int(sfsh['mdistance'].isna().sum()), 'dilution': int(sfsh['dilution'].isna().sum()), 'min_range': int(sfsh['min_range'].isna().sum()), 'epoch': int(sfsh['epoch'].isna().sum())}, 'met_criteria_combinations': {str(k): int(v) for k, v in sfsh.groupby(['met_criteria1', 'met_criteria2'], dropna=False).size().items()}, 'dilution_value_counts': {str(k): int(v) for k, v in sfsh['dilution'].value_counts(dropna=False).items()}, 'min_range_km': {'min': float(sfsh['min_range'].min()), 'max': float(sfsh['min_range'].max())}, 'prob_range_raw': {'min': float(sfsh['prob'].min()), 'max': float(sfsh['prob'].max())}}
    iss = hbr.loc[hbr['catalog_num'] == 25544, 'hbr_m']
    hbr_facts = {'rows': int(len(hbr)), 'identical_duplicate_rows_removed': int(hbr.attrs.get('identical_duplicate_rows_removed', 0)), 'hbr_m': {'min': float(hbr['hbr_m'].min()), 'median': float(hbr['hbr_m'].median()), 'max': float(hbr['hbr_m'].max())}, 'iss_25544_hbr': float(iss.iloc[0]) if len(iss) else None, 'unit_evidence': "Guide: spherical run uses 'a default HBR of 0.5m'; ISS (25544) maps to 55.0, meaningful only in metres", 'screening_volume_categories': int(hbr['ScreeningVolume'].nunique()), 'objects_without_hbr': int(hbr['hbr_m'].isna().sum())}
    mapped = set(hbr['catalog_num'])
    obj1_mapped = obj1.isin(mapped)
    obj2_mapped = obj2.isin(mapped)
    coverage = {'rows_obj1_in_hbr_map': int(obj1_mapped.sum()), 'rows_obj2_in_hbr_map': int(obj2_mapped.sum()), 'rows_both_objects_in_hbr_map': int((obj1_mapped & obj2_mapped).sum()), 'rows_missing_any_hbr': int((~obj1_mapped | ~obj2_mapped).sum()), 'distinct_obj1_missing': sorted((int(v) for v in obj1[~obj1_mapped].unique()))[:20], 'distinct_obj2_missing_count': int(obj2[~obj2_mapped].nunique())}
    result = {'status': 'PASS' if all(structure.values()) else 'FAIL', 'inputs': {'sfsh_csv': {'path': rel(SFSH_CSV)}, 'size_csv': {'path': rel(SIZE_CSV)}, 'guide_pdf': {'path': rel(GUIDE_PDF)}}, 'structure': structure, 'field_mapping': FIELD_MAPPING, 'sfsh_facts': facts, 'hbr_mapping_facts': hbr_facts, 'hbr_join_coverage': coverage, 'notes': ["prob is the collision probability itself (Alfano 2004); unlike the ESA file, which stores log10(Pc) in 'risk', no log transform applies.", 'min_range is already in km; no unit conversion is needed for d.', 'h(e) requires the per-object HBR join and a m->km conversion.', 'The guide warns that Pc comparison across tools requires the same Pc method; this experiment consumes the answer key as-is and does not recompute Pc.']}
    save_json(RESULTS / 'field_audit.json', result)
    print(json.dumps({'status': result['status'], 'rows': facts['rows'], 'null_prob': facts['null_counts']['prob'], 'hbr_full_coverage_rows': coverage['rows_both_objects_in_hbr_map']}, ensure_ascii=False))
    if result['status'] != 'PASS':
        raise SystemExit(1)
if __name__ == '__main__':
    main()
