"""Shared, deterministic ESA CDM experiment utilities.

The adapter deliberately keeps the TC-SSSAO schema and R1--R18/B1--B5
files unchanged.  Relative CDM order is handled in this execution layer because
the public anonymised ESA data do not contain absolute creation/TCA timestamps.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import statistics
import time
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

SEED = 20260911
THETA_A = 1e-7
THETA_M = 1e-4

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
WORKSPACE = BASE.parents[1]
# 数据目录（2026-09-13 最终工作区整理）：ESA 数据集独立于实验目录，
# 统一存放 data/esa_cdm/；官方 ZIP 即原始数据本体，下载/校验/
# 解包均在 raw/ 层完成（原 download/ 与 raw/ 合并）。
DATA_ESA = WORKSPACE / "data" / "esa_cdm"
DOWNLOAD = DATA_ESA / "raw"
RAW = DATA_ESA / "raw"
PROCESSED = DATA_ESA / "processed"
METADATA = DATA_ESA / "metadata"
RDF_DIR = BASE / "rdf"
RESULTS = BASE / "results"
FIGURES = BASE / "figures"

DATASET_URL = (
    "https://zenodo.org/records/4463683/files/"
    "Collision%20Avoidance%20Challenge%20-%20Dataset.zip?download=1"
)
DATASET_DOI = "10.5281/zenodo.4463683"
ARCHIVE = DOWNLOAD / "Collision Avoidance Challenge - Dataset.zip"
PROCESSED_CSV = PROCESSED / "esa_train_normalized.csv.gz"

STATE_RANK = {"Normal": 0, "Attention": 1, "Warning": 2, "Dangerous": 3}
RANK_STATE = {v: k for k, v in STATE_RANK.items()}


def ensure_dirs() -> None:
    for path in (RAW, PROCESSED, METADATA, RDF_DIR, RESULTS, FIGURES):
        path.mkdir(parents=True, exist_ok=True)



def stable_token(*parts: object, length: int = 24) -> str:
    raw = "|".join(str(p) for p in parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:length]


def save_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def locate_train_csv() -> Path:
    candidates = sorted(RAW.rglob("*.csv"))
    preferred = [p for p in candidates if "train" in p.name.lower() and "label" not in p.name.lower()]
    for path in preferred + candidates:
        try:
            cols = set(pd.read_csv(path, nrows=2).columns)
        except Exception:
            continue
        if {"event_id", "risk", "time_to_tca", "miss_distance", "t_span", "c_span"} <= cols:
            return path
    raise FileNotFoundError("No extracted ESA training CSV with the required columns was found")


def load_train(usecols: list[str] | None = None) -> pd.DataFrame:
    return pd.read_csv(locate_train_csv(), usecols=usecols, low_memory=False)


def _num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def preprocess_frame(raw: pd.DataFrame) -> pd.DataFrame:
    """Normalize official units and preserve source values/provenance.

    ESA risk is log10(Pc); miss distance and both span fields are metres.
    The official data paper identifies t_span as a satellite diameter, and the
    Kelvins description ties x_span to size/diameter.  Thus combined HBR is the
    sum of the two radii: (t_span + c_span) / 2, converted here to kilometres.
    """
    df = pd.DataFrame(index=raw.index)
    df["source_row"] = np.arange(len(raw), dtype=np.int64)
    for col in (
        "event_id", "risk", "time_to_tca", "mission_id", "miss_distance",
        "relative_speed", "t_span", "c_span", "c_object_type",
        "t_obs_available", "c_obs_available", "t_obs_used", "c_obs_used",
        "t_weighted_rms", "c_weighted_rms", "t_actual_od_span", "c_actual_od_span",
        "t_recommended_od_span", "c_recommended_od_span",
    ):
        df[col] = raw[col] if col in raw.columns else np.nan

    for col in df.columns.difference(["c_object_type"]):
        if col != "source_row":
            df[col] = _num(df[col])

    df["pc"] = np.power(10.0, df["risk"].astype(float))
    df["miss_distance_km"] = df["miss_distance"] / 1000.0
    df["hbr_km"] = (df["t_span"] + df["c_span"]) / 2000.0

    df["event_key"] = df["event_id"].map(lambda x: "" if pd.isna(x) else format(float(x), ".15g"))
    df["snapshot_id"] = [stable_token(e, r) for e, r in zip(df["event_key"], df["source_row"])]

    valid_pc = np.isfinite(df["pc"]) & df["pc"].between(0.0, 1.0, inclusive="both")
    valid_distance = np.isfinite(df["miss_distance_km"]) & (df["miss_distance_km"] >= 0)
    valid_hbr = np.isfinite(df["hbr_km"]) & (df["hbr_km"] > 0)
    valid_time = np.isfinite(df["time_to_tca"])
    valid_roles = df["event_key"].str.len() > 0

    duplicate_exact = raw.duplicated(keep=False).to_numpy()
    df["duplicate_exact_row"] = duplicate_exact
    df["valid_pc"] = valid_pc
    df["valid_distance"] = valid_distance
    df["valid_hbr"] = valid_hbr
    df["valid_time"] = valid_time
    df["valid_roles"] = valid_roles
    df["preflight_pass"] = valid_pc & valid_distance & valid_hbr & valid_time & valid_roles & ~duplicate_exact
    df["rejection_reason"] = rejection_reasons(df)
    df["state"] = classify_states(df)
    df["severity_rank"] = df["state"].map(STATE_RANK).astype("Int64")
    return df


def rejection_reasons(df: pd.DataFrame) -> pd.Series:
    reasons: list[str] = []
    for row in df.itertuples(index=False):
        current: list[str] = []
        if not row.valid_pc:
            current.append("missing Pc" if pd.isna(row.pc) else "invalid Pc")
        if not row.valid_distance:
            current.append("missing distance" if pd.isna(row.miss_distance_km) else "invalid distance")
        if not row.valid_hbr:
            current.append("missing HBR" if pd.isna(row.hbr_km) else "invalid HBR")
        if not row.valid_time:
            current.append("missing time_to_tca")
        if not row.valid_roles:
            current.append("object role failure")
        if row.duplicate_exact_row:
            current.append("duplicate row")
        reasons.append("; ".join(current))
    return pd.Series(reasons, index=df.index, dtype="string")


def classify_states(df: pd.DataFrame) -> pd.Series:
    state = pd.Series(pd.NA, index=df.index, dtype="string")
    valid = df["preflight_pass"].astype(bool)
    high_pc = df["pc"] > THETA_M
    close = df["miss_distance_km"] < df["hbr_km"]
    state.loc[valid & ~high_pc & ~close & (df["pc"] <= THETA_A)] = "Normal"
    state.loc[valid & ~high_pc & ~close & (df["pc"] > THETA_A)] = "Attention"
    state.loc[valid & (high_pc ^ close)] = "Warning"
    state.loc[valid & high_pc & close] = "Dangerous"
    return state


def load_processed() -> pd.DataFrame:
    if not PROCESSED_CSV.exists():
        raise FileNotFoundError(f"Run 03_preprocess_cdm.py first: {PROCESSED_CSV}")
    return pd.read_csv(PROCESSED_CSV, low_memory=False)


def select_event_keys(df: pd.DataFrame, count: int, minimum_rows: int = 1) -> list[str]:
    eligible = (
        df.groupby("event_key", sort=True)
        .agg(rows=("source_row", "size"), max_pc=("pc", "max"))
        .query("rows >= @minimum_rows")
        .sort_values(["max_pc", "rows"], kind="mergesort")
    )
    if count >= len(eligible):
        return eligible.index.astype(str).tolist()
    positions = np.linspace(0, len(eligible) - 1, count, dtype=int)
    return eligible.iloc[positions].index.astype(str).tolist()


def subset_events(df: pd.DataFrame, count: int, minimum_rows: int = 1) -> pd.DataFrame:
    keys = set(select_event_keys(df, count, minimum_rows))
    return df[df["event_key"].astype(str).isin(keys)].copy()


def derive_transitions(df: pd.DataFrame) -> pd.DataFrame:
    """B3 execution-layer equivalent over true relative order.

    Handles both severity increases (transitsTo + optional degradesTo)
    and severity decreases (transitsTo + recoversTo).

    All snapshots participate in adjacency.  Therefore an invalid/unrated row
    blocks an edge and can never be skipped over.
    """
    rows: list[dict[str, object]] = []
    for event_key, group in df.groupby("event_key", sort=True):
        ordered = group.sort_values(["time_to_tca", "source_row"], ascending=[False, True], kind="mergesort")
        records = list(ordered.itertuples(index=False))
        for left, right in zip(records, records[1:]):
            if not bool(left.preflight_pass) or not bool(right.preflight_pass):
                continue
            if pd.isna(left.severity_rank) or pd.isna(right.severity_rank):
                continue
            # Strict time direction: earlier snapshot (larger time_to_tca) must come first
            if not (float(left.time_to_tca) > float(right.time_to_tca)):
                continue
            r1, r2 = int(left.severity_rank), int(right.severity_rank)
            if r1 == r2:
                continue  # same severity: no transition
            rows.append({
                "event_key": str(event_key),
                "source_snapshot": left.snapshot_id,
                "target_snapshot": right.snapshot_id,
                "source_rank": r1,
                "target_rank": r2,
                "source_state": RANK_STATE[r1],
                "target_state": RANK_STATE[r2],
                "degrades_to": r1 == 2 and r2 == 3,
                "recovers_to": r1 > r2,  # any severity decrease
                "direction": "increase" if r2 > r1 else "decrease",
            })
    return pd.DataFrame(rows)


def state_evolution_metrics(df: pd.DataFrame, _test_transitions: pd.DataFrame | None = None) -> dict[str, object]:
    counts = df.groupby("event_key").size()
    transitions = _test_transitions if _test_transitions is not None else derive_transitions(df)
    valid_counts = df[df["preflight_pass"]].groupby("event_key").size()
    state_change_events = 0
    upgrade_events: set[str] = set()
    downgrade_events: set[str] = set()
    for _, group in df.groupby("event_key"):
        ordered = group.sort_values(["time_to_tca", "source_row"], ascending=[False, True])
        ranks = ordered.loc[ordered["preflight_pass"], "severity_rank"].dropna().astype(int).tolist()
        if any(a != b for a, b in zip(ranks, ranks[1:])):
            state_change_events += 1
    if not transitions.empty:
        upgrade_events = set(transitions.loc[transitions["direction"] == "increase", "event_key"].astype(str))
        downgrade_events = set(transitions.loc[transitions["direction"] == "decrease", "event_key"].astype(str))

    # ------------------------------------------------------------------
    # P1-4 fix: genuine error-edge detection with per-snapshot indexing.
    # Build: snapshot_id → (event_key, time_to_tca, severity_rank, group_position)
    # Group position = rank of the snapshot within its event_key group
    # sorted by (time_to_tca DESC, source_row ASC), 0-indexed.
    # ------------------------------------------------------------------
    snap_meta: dict[str, dict] = {}
    for event_key, group in df.groupby("event_key", sort=True):
        ordered = group.sort_values(["time_to_tca", "source_row"], ascending=[False, True])
        for pos, (_, row) in enumerate(ordered.iterrows()):
            sid = str(row["snapshot_id"])
            snap_meta[sid] = {
                "event_key": str(event_key),
                "time_to_tca": float(row["time_to_tca"]),
                "severity_rank": int(row["severity_rank"]) if pd.notna(row["severity_rank"]) else None,
                "group_position": pos,
                "preflight_pass": bool(row["preflight_pass"]),
                "state": str(row["state"]) if pd.notna(row["state"]) else None,
            }

    # 10 error categories
    err_cross_event = 0          # Type 1: source and target have different event_key
    err_within_non_adjacent = 0   # Type 2: within-event group position gap ≠ 1
    err_time_direction = 0        # Type 3: time_to_tca does not decrease (wrong order)
    err_recovers_direction = 0    # Type 4: recoversTo present but rank didn't decrease
    err_degrades_warning = 0      # Type 5: degradesTo present but not Warning→Dangerous
    err_transits_same_rank = 0     # Type 6: transitsTo present but rank is the same
    err_mismatch_predicate = 0     # Type 7: transitsTo+recoversTo but direction is increase
    err_mismatch_predicate2 = 0   # Type 7b: transitsTo+degradesTo but rank isn't 2→3
    err_missing_recovers_on_downgrade = 0   # Type 8: r1>r2 but recovers_to=False
    err_missing_degrades_on_warning_dangerous = 0  # Type 9: r1=2,r2=3 but degrades_to=False
    err_direction_field_inconsistent = 0    # Type 10: direction field doesn't match rank change

    error_details: list[dict] = []

    def _record_error(kind: str, detail: str, src: str, tgt: str, relation: str):
        error_details.append({
            "error_type": kind,
            "detail": detail,
            "source_snapshot": src,
            "target_snapshot": tgt,
            "relation": relation,
        })

    for _, row in transitions.iterrows():
        sid1 = str(row["source_snapshot"])
        sid2 = str(row["target_snapshot"])
        meta1 = snap_meta.get(sid1, {})
        meta2 = snap_meta.get(sid2, {})
        ek1 = meta1.get("event_key", "?")
        ek2 = meta2.get("event_key", "?")
        t1 = meta1.get("time_to_tca", float("nan"))
        t2 = meta2.get("time_to_tca", float("nan"))
        r1 = meta1.get("severity_rank")
        r2 = meta2.get("severity_rank")
        pos1 = meta1.get("group_position", -1)
        pos2 = meta2.get("group_position", -1)
        recovers = bool(row.get("recovers_to", False))
        degrades = bool(row.get("degrades_to", False))
        transits = True  # every row in transitions is a transitsTo

        # Type 1: cross-event
        if ek1 != ek2:
            err_cross_event += 1
            _record_error("cross_event", f"{sid1}[{ek1}] → {sid2}[{ek2}]", sid1, sid2, "transitsTo")

        # Type 2: within-event non-adjacent (group position gap must be exactly 1)
        if ek1 == ek2 and pos2 - pos1 != 1:
            err_within_non_adjacent += 1
            _record_error("within_non_adjacent",
                         f"group pos {pos1} → {pos2} (gap {pos2-pos1})", sid1, sid2, "transitsTo")

        # Type 3: time direction (time_to_tca must decrease = later snapshot smaller tca)
        if not (t1 > t2):  # use > since larger time_to_tca = earlier
            err_time_direction += 1
            _record_error("time_order",
                         f"time_to_tca {t1} → {t2} (must decrease)", sid1, sid2, "transitsTo")

        # Type 4: recoversTo but rank didn't decrease
        if recovers:
            if r1 is None or r2 is None or r1 <= r2:
                err_recovers_direction += 1
                _record_error("recovers_direction",
                             f"rank {r1} → {r2} (must decrease)", sid1, sid2, "recoversTo")

        # Type 5: degradesTo but not Warning(2) → Dangerous(3)
        if degrades:
            if r1 != 2 or r2 != 3:
                err_degrades_warning += 1
                _record_error("degrades_warning",
                             f"rank {r1} → {r2} (must be 2→3)", sid1, sid2, "degradesTo")

        # Type 6: transitsTo but rank is the same
        if r1 is not None and r2 is not None and r1 == r2:
            err_transits_same_rank += 1
            _record_error("transits_same_rank",
                         f"rank {r1} → {r2} (must differ)", sid1, sid2, "transitsTo")

        # Type 7a: transitsTo+recoversTo but direction is actually increase (r1 < r2)
        if recovers and r1 is not None and r2 is not None and r1 < r2:
            err_mismatch_predicate += 1
            _record_error("predicate_direction_mismatch",
                         f"recoversTo but rank {r1}→{r2} (increase)", sid1, sid2, "transitsTo+recoversTo")

        # Type 7b: transitsTo+degradesTo but rank isn't 2→3
        if degrades and (r1 != 2 or r2 != 3):
            err_mismatch_predicate2 += 1
            _record_error("degrades_predicate_mismatch",
                         f"degradesTo but rank {r1}→{r2} (not 2→3)", sid1, sid2, "transitsTo+degradesTo")

        # Type 8: downgrade (r1>r2) but recovers_to flag is False
        if r1 is not None and r2 is not None and r1 > r2 and not recovers:
            err_missing_recovers_on_downgrade += 1
            _record_error("missing_recovers_on_downgrade",
                         f"rank {r1}→{r2} but recovers_to=False", sid1, sid2, "transitsTo")

        # Type 9: Warning(2)→Dangerous(3) but degrades_to flag is False
        if r1 == 2 and r2 == 3 and not degrades:
            err_missing_degrades_on_warning_dangerous += 1
            _record_error("missing_degrades_on_warning_dangerous",
                         f"rank 2→3 but degrades_to=False", sid1, sid2, "transitsTo")

        # Type 10: direction field inconsistent with rank change
        direction = row.get("direction")
        if direction is not None and r1 is not None and r2 is not None:
            expected_dir = "increase" if r2 > r1 else "decrease"
            if str(direction) != expected_dir:
                err_direction_field_inconsistent += 1
                _record_error("direction_field_inconsistent",
                             f"direction={direction} but rank {r1}→{r2} (expected {expected_dir})",
                             sid1, sid2, "transitsTo")

    return {
        "event_count": int(df["event_key"].nunique()),
        "mean_cdms_per_event": float(counts.mean()),
        "median_cdms_per_event": float(counts.median()),
        "max_cdms_per_event": int(counts.max()),
        "events_with_at_least_2_valid_snapshots": int((valid_counts >= 2).sum()),
        "events_with_state_change": int(state_change_events),
        "events_with_state_upgrade": int(len(upgrade_events)),
        "events_with_state_recovery": int(len(downgrade_events)),
        "b3_transits_to": int(len(transitions)),
        "warning_to_dangerous_degrades_to": int(transitions.get("degrades_to", pd.Series(dtype=bool)).sum()),
        "severity_decreases_recovered_to": int(transitions.get("recovers_to", pd.Series(dtype=bool)).sum()),
        # P1-4 genuine error counts
        "err_cross_event": err_cross_event,
        "err_within_non_adjacent": err_within_non_adjacent,
        "err_time_direction": err_time_direction,
        "err_recovers_direction": err_recovers_direction,
        "err_degrades_warning": err_degrades_warning,
        "err_transits_same_rank": err_transits_same_rank,
        "err_mismatch_predicate": err_mismatch_predicate,
        "err_mismatch_predicate2": err_mismatch_predicate2,
        "err_missing_recovers_on_downgrade": err_missing_recovers_on_downgrade,
        "err_missing_degrades_on_warning_dangerous": err_missing_degrades_on_warning_dangerous,
        "err_direction_field_inconsistent": err_direction_field_inconsistent,
        "error_details": error_details,
    }


def temporal_agreement(df: pd.DataFrame, windows: Iterable[float] = (7, 5, 3, 2, 1), tolerance: float = 0.5) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    valid = df[df["preflight_pass"] & df["state"].notna()].copy()
    grouped = list(valid.groupby("event_key"))
    for window in windows:
        agreements: list[bool] = []
        for _, group in grouped:
            ordered = group.sort_values(["time_to_tca", "source_row"], ascending=[True, False])
            final_state = str(ordered.iloc[0]["state"])
            distances = (group["time_to_tca"] - float(window)).abs()
            idx = distances.idxmin()
            if float(distances.loc[idx]) <= tolerance:
                agreements.append(str(group.loc[idx, "state"]) == final_state)
        records.append({
            "days_before_tca": float(window),
            "sample_events": len(agreements),
            "agreement_with_final_cdm": float(np.mean(agreements)) if agreements else None,
            "selection_tolerance_days": tolerance,
        })
    return records


def mapping_triple_count(df: pd.DataFrame) -> int:
    """Exact count implied by the documented adapter mapping, without OWL TBox."""
    events = int(df["event_key"].nunique())
    rows = len(df)
    # Encounter: type + primary + secondary (3); objects: 2 types (2).
    # Per row: risk event 7 core triples, observation 2, assessment 8 provenance/
    # values, and two evidence links already included in the risk-event seven.
    optional_quality = sum(int(df[c].notna().sum()) for c in (
        "t_obs_available", "c_obs_available", "t_obs_used", "c_obs_used",
        "t_weighted_rms", "c_weighted_rms", "t_actual_od_span", "c_actual_od_span",
        "t_recommended_od_span", "c_recommended_od_span",
    ) if c in df)
    return events * 5 + rows * 17 + optional_quality


def process_peak_rss_mb() -> float:
    try:
        import psutil
        info = psutil.Process().memory_info()
        peak = getattr(info, "peak_wset", None)
        return float(peak if peak is not None else info.rss) / (1024 * 1024)
    except Exception:
        pass
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        class PMC(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
            ]
        counters = PMC()
        counters.cb = ctypes.sizeof(counters)
        ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb
        )
        return counters.PeakWorkingSetSize / (1024 * 1024)
    try:
        import resource
        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return value / 1024.0
    except Exception:
        return float("nan")


def summarize_timings(values: list[float]) -> dict[str, float]:
    arr = np.asarray(values, dtype=float)
    if len(arr) == 0:
        return {"mean": float("nan"), "median": float("nan"), "std": float("nan"), "p95": float("nan")}
    return {
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "std": float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0,
        "p95": float(np.percentile(arr, 95)),
    }


def timed(callable_):
    start = time.perf_counter()
    value = callable_()
    return value, time.perf_counter() - start
