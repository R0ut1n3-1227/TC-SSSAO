from __future__ import annotations
import pandas as pd
from common import PROCESSED, PROCESSED_CSV, load_train, preprocess_frame, save_json

def main() -> None:
    raw = load_train()
    df = preprocess_frame(raw)
    df.to_csv(PROCESSED_CSV, index=False, compression='gzip', float_format='%.15g')
    summary = {'status': 'PASS', 'rows': len(df), 'events': int(df['event_key'].nunique()), 'risk_transform': 'pc = 10 ** risk', 'distance_transform': 'miss_distance_km = miss_distance_m / 1000', 'hbr_transform': 'hbr_km = (t_span_m + c_span_m) / 2000', 'execution_layer_input_contract_pass': int(df['preflight_pass'].sum()), 'execution_layer_input_contract_reject': int((~df['preflight_pass']).sum()), 'processed_file': PROCESSED_CSV.name}
    save_json(PROCESSED / 'preprocess_summary.json', summary)
    print(summary)
if __name__ == '__main__':
    main()
