"""Shared utilities for the TraCSS IVV dataset adaptation experiment.

Scope and constraints:
- Read-only with respect to the raw TraCSS downloads, the ESA pipeline,
  the TC-SSSAO rule files, and the ontology.
- THETA_A / THETA_M are the frozen formal parameters of R5-R8 and hold
  the identical values as experiments/esa_cdm/scripts/common.py.
  They must not be changed here.
- Field semantics follow the TraCSS Conjunction Screening Testset
  User's Guide (Table 5 and the SFSH Screening Volume Mappings section);
  no meaning is inferred from column names alone.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

# Frozen formal parameters (R5-R8); identical to the ESA experiment.
THETA_A = 1e-7
THETA_M = 1e-4

HERE = Path(__file__).resolve().parent
BASE = HERE.parent                    # experiments/tracss
WORKSPACE = BASE.parents[1]           # project root
DATASET = WORKSPACE / "data" / "tracss" / "raw"       # raw TraCSS downloads (user-provided)
DATA = BASE / "data"                  # adapter output (normalized fields)
RESULTS = BASE / "results"

SFSH_CSV = DATASET / "IVV_Releasable_Dataset_SFSH_DiscreteHBR.csv.gz"
SIZE_CSV = DATASET / "AerospaceIVVDataset_20251009a_Size_ScreeningVolumes.csv.gz"
GUIDE_PDF = DATASET / "Conjunction_Screening_Testset_Users_Guide.pdf"

NORMALIZED_CSV = DATA / "tracss_sfsh_normalized.csv.gz"

# Expected columns per the TraCSS User's Guide, Table 5 (CSieve Conjunction
# Results Output File Specifications).  Verified against the guide, never
# guessed from names.  Notably:
#   min_range  = miss distance in km        (-> predicted_miss_distance)
#   mdistance  = Mahalanobis distance       (NOT a miss distance)
#   prob       = Pc via the Alfano 2004 method
EXPECTED_SFSH_COLUMNS = [
    "run_id", "conj_id", "obj1", "met_criteria1", "obj2", "met_criteria2",
    "min_range", "Vrel", "prob", "dilution", "mdistance", "epoch", "jdate",
    "x1", "y1", "z1", "vx1", "vy1", "vz1",
    "local_x1", "local_y1", "local_z1",
    "c1_11", "c1_12", "c1_13", "c1_22", "c1_23", "c1_33",
    "x2", "y2", "z2", "vx2", "vy2", "vz2",
    "local_x2", "local_y2", "local_z2",
    "c2_11", "c2_12", "c2_13", "c2_22", "c2_23", "c2_33",
    "obj1_filename", "obj2_filename",
]
EXPECTED_SIZE_COLUMNS = ["catalog_num", "HBR", "ScreeningVolume",
                         "U (km)", "V (km)", "W (km)"]

STATE_RANK = {"Normal": 0, "Attention": 1, "Warning": 2, "Dangerous": 3}


def ensure_dirs() -> None:
    for path in (DATA, RESULTS):
        path.mkdir(parents=True, exist_ok=True)


def rel(path: Path) -> str:
    """Workspace-relative POSIX path for provenance fields (no absolute paths
    are ever serialized; workspace hygiene rule H6)."""
    return path.resolve().relative_to(WORKSPACE).as_posix()



def save_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2),
                    encoding="utf-8")


def load_hbr_map() -> pd.DataFrame:
    """Per-object HBR (metres) and SFSH screening volumes.

    The mapping file header carries no unit for HBR; the User's Guide pins
    the spherical run's default HBR to 0.5 m, and the mapping entry for the
    ISS (catalog 25544) is 55.0, which is only physically meaningful in
    metres.  HBR is therefore interpreted as metres (radius per object).
    """
    df = pd.read_csv(SIZE_CSV)
    if list(df.columns) != EXPECTED_SIZE_COLUMNS:
        raise ValueError(f"Size/ScreeningVolume header mismatch: {list(df.columns)}")
    df["catalog_num"] = pd.to_numeric(df["catalog_num"], errors="raise").astype(np.int64)
    df["hbr_m"] = pd.to_numeric(df["HBR"], errors="coerce")
    for col in ("U (km)", "V (km)", "W (km)"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    # The published file repeats some catalog entries verbatim (e.g. objects
    # with several OCMs under one designator).  Identical repeats are dropped;
    # *conflicting* repeats would make the HBR join ambiguous and are fatal.
    n_raw = len(df)
    key_cols = ["catalog_num", "hbr_m", "ScreeningVolume", "U (km)", "V (km)", "W (km)"]
    conflicts = df.groupby("catalog_num")[key_cols[1:]].nunique(dropna=False)
    if (conflicts > 1).any(axis=None):
        bad = conflicts[(conflicts > 1).any(axis=1)].index.tolist()[:10]
        raise ValueError(f"conflicting HBR mapping rows for catalog_num: {bad}")
    df = df.drop_duplicates(subset="catalog_num", keep="first").reset_index(drop=True)
    df.attrs["identical_duplicate_rows_removed"] = n_raw - len(df)
    return df


def load_sfsh() -> pd.DataFrame:
    """Full SFSH DiscreteHBR answer key with parsed types.

    `prob`, `mdistance`, `dilution` may be NULL in the raw file (covariance
    metrics not computable for some rows, per the User's Guide); they are
    parsed to NaN and the rows are kept for auditing.
    """
    raw = pd.read_csv(SFSH_CSV, dtype=str, low_memory=False)
    if list(raw.columns) != EXPECTED_SFSH_COLUMNS:
        raise ValueError(f"SFSH header mismatch: {list(raw.columns)}")
    df = raw.copy()
    for col in ("run_id", "conj_id", "obj1", "obj2"):
        df[col] = pd.to_numeric(df[col], errors="raise").astype(np.int64)
    for col in ("met_criteria1", "met_criteria2"):
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    for col in ("min_range", "Vrel", "prob", "dilution", "mdistance", "jdate"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def classify_states(df: pd.DataFrame) -> pd.Series:
    """R5-R8 state classification, frozen semantics.

    Boolean structure is identical to experiments/esa_cdm classify_states:
      R5 Normal:    pc <= THETA_A and d >= h
      R6 Attention: THETA_A < pc <= THETA_M and d >= h
      R7 Warning:   (pc > THETA_M) xor (d < h)
      R8 Dangerous: pc > THETA_M and d < h
    (d >= h is the negation of d < h, so d == h falls on the R5/R6 side.)
    04_risk_state_eval.py cross-checks this implementation against the ESA
    one on every row.
    """
    state = pd.Series(pd.NA, index=df.index, dtype="string")
    valid = df["preflight_pass"].astype(bool)
    pc = df["collision_probability"]
    high_pc = pc > THETA_M
    close = df["predicted_miss_distance"] < df["combined_hard_body_radius"]
    state.loc[valid & ~high_pc & ~close & (pc <= THETA_A)] = "Normal"
    state.loc[valid & ~high_pc & ~close & (pc > THETA_A)] = "Attention"
    state.loc[valid & (high_pc ^ close)] = "Warning"
    state.loc[valid & high_pc & close] = "Dangerous"
    return state


def load_normalized() -> pd.DataFrame:
    if not NORMALIZED_CSV.exists():
        raise FileNotFoundError(f"Run 02_build_adapter.py first: {NORMALIZED_CSV.name}")
    return pd.read_csv(NORMALIZED_CSV, low_memory=False)
