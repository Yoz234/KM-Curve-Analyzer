"""
Individual Patient Data (IPD) Reconstruction
Based on: Guyot et al. (2012) Enhanced secondary analysis of survival data.
BMC Medical Research Methodology, 12:9.

Algorithm:
  Given digitized KM curve coordinates + at-risk table,
  reconstruct synthetic individual-level (time, event) pairs.
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Optional


def reconstruct_ipd(
    curve_points: List[Tuple[float, float]],
    at_risk_table: Optional[List[Tuple[float, int]]] = None,
    n_total: int = None,
    t_max: Optional[float] = None,
) -> pd.DataFrame:
    """
    Reconstruct IPD from KM curve points and at-risk table.

    Args:
        curve_points: List of (time, survival) tuples from digitized curve.
                      Must include (0, 1.0) as first point.
        at_risk_table: List of (time, n_at_risk) tuples from risk table.
                       If None, estimated from curve alone.
        n_total: Total number of patients. Required if at_risk_table is None.
        t_max: Maximum follow-up time. Defaults to last curve point time.

    Returns:
        DataFrame with columns ['time', 'event']
        event=1 means event occurred, event=0 means censored.
    """
    # Sort and validate curve points
    pts = sorted(curve_points, key=lambda x: x[0])
    if pts[0][0] != 0.0:
        pts = [(0.0, 1.0)] + pts

    times = np.array([p[0] for p in pts])
    surv = np.array([p[1] for p in pts])

    # Clip survival to [0,1]
    surv = np.clip(surv, 0.0, 1.0)

    if t_max is None:
        t_max = times[-1]

    # Build at-risk map keyed by interval start time
    if at_risk_table:
        risk_times = np.array([r[0] for r in sorted(at_risk_table)])
        risk_counts = np.array([r[1] for r in sorted(at_risk_table)])
        n_total_est = int(risk_counts[0])
    else:
        if n_total is None:
            raise ValueError("Either at_risk_table or n_total must be provided.")
        n_total_est = n_total
        # Approximate at-risk as n * S(t)
        risk_times = times
        risk_counts = np.round(n_total_est * surv).astype(int)

    ipd_rows = []

    # Iterate over intervals between consecutive curve points
    for i in range(len(times) - 1):
        t_start = times[i]
        t_end = times[i + 1]
        s_start = surv[i]
        s_end = surv[i + 1]

        # Estimate n_at_risk at t_start
        n_at_risk = _interpolate_at_risk(t_start, risk_times, risk_counts)

        if n_at_risk <= 0:
            continue

        # Number of events in this interval
        # Using KM relation: S(t_end) = S(t_start) * (1 - d/n)
        # => d = n * (1 - S(t_end)/S(t_start))
        if s_start > 0:
            n_events = max(0, round(n_at_risk * (1.0 - s_end / s_start)))
        else:
            n_events = 0

        # Number of censorings in this interval
        # n_at_risk_next = n_at_risk - n_events - n_censored
        n_at_risk_next = _interpolate_at_risk(t_end, risk_times, risk_counts)
        n_censored = max(0, n_at_risk - n_events - n_at_risk_next)

        # Generate event times (uniformly spread in interval)
        if n_events > 0:
            event_times = np.linspace(t_start, t_end, n_events + 2)[1:-1]
            for t in event_times:
                ipd_rows.append({"time": round(float(t), 4), "event": 1})

        # Generate censoring times (uniformly spread in interval)
        if n_censored > 0:
            censor_times = np.linspace(t_start, t_end, n_censored + 2)[1:-1]
            for t in censor_times:
                ipd_rows.append({"time": round(float(t), 4), "event": 0})

    # Handle last time point: remaining patients are censored at t_max
    n_final = _interpolate_at_risk(times[-1], risk_times, risk_counts)
    if n_final > 0:
        for _ in range(int(n_final)):
            ipd_rows.append({"time": round(float(t_max), 4), "event": 0})

    df = pd.DataFrame(ipd_rows, columns=["time", "event"])
    df = df.sort_values("time").reset_index(drop=True)
    return df


def _interpolate_at_risk(
    t: float,
    risk_times: np.ndarray,
    risk_counts: np.ndarray,
) -> int:
    """Return at-risk count at time t using step-function interpolation."""
    if t <= risk_times[0]:
        return int(risk_counts[0])
    if t >= risk_times[-1]:
        return int(risk_counts[-1])
    # Find last risk_time <= t
    idx = np.searchsorted(risk_times, t, side="right") - 1
    return int(risk_counts[idx])


def validate_curve_points(points: List[Tuple[float, float]]) -> List[str]:
    """Return list of validation warnings for curve points."""
    warnings = []
    if not points:
        warnings.append("No curve points provided.")
        return warnings

    times = [p[0] for p in points]
    survs = [p[1] for p in points]

    if times[0] != 0.0:
        warnings.append("First time point is not 0; will prepend (0, 1.0).")

    if any(s > 1.0 or s < 0.0 for s in survs):
        warnings.append("Some survival values outside [0,1]; will be clipped.")

    # Check monotonicity
    for i in range(1, len(survs)):
        if survs[i] > survs[i - 1] + 0.01:
            warnings.append(
                f"Survival increases at t={times[i]:.2f} (non-monotone). "
                "Consider re-digitizing."
            )

    return warnings
