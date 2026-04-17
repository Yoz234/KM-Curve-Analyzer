"""
Log-rank test and survival statistics.
Uses the lifelines library for robust computation.
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import List, Dict, Any, Optional

try:
    from lifelines.statistics import logrank_test, multivariate_logrank_test
    from lifelines import KaplanMeierFitter, CoxPHFitter
    LIFELINES_AVAILABLE = True
except ImportError:
    LIFELINES_AVAILABLE = False


def _finite(v):
    """Return float v, or None if nan/inf."""
    try:
        f = float(v)
        return f if np.isfinite(f) else None
    except Exception:
        return None


def compute_logrank(
    ipd_a: pd.DataFrame,
    ipd_b: pd.DataFrame,
    group_a_name: str = "Group A",
    group_b_name: str = "Group B",
) -> Dict[str, Any]:
    """
    Perform log-rank test between two groups.

    Args:
        ipd_a: DataFrame with ['time', 'event'] for group A
        ipd_b: DataFrame with ['time', 'event'] for group B
        group_a_name: Label for group A
        group_b_name: Label for group B

    Returns:
        Dictionary with test results and KM estimates
    """
    if not LIFELINES_AVAILABLE:
        return _manual_logrank(ipd_a, ipd_b, group_a_name, group_b_name)

    result = logrank_test(
        durations_A=ipd_a["time"],
        durations_B=ipd_b["time"],
        event_observed_A=ipd_a["event"],
        event_observed_B=ipd_b["event"],
    )

    hr, hr_lower, hr_upper = compute_hazard_ratio(ipd_a, ipd_b)
    km_a = fit_km(ipd_a, group_a_name)
    km_b = fit_km(ipd_b, group_b_name)

    return {
        "test": "log-rank",
        "p_value": float(result.p_value),
        "test_statistic": float(result.test_statistic),
        "significant": bool(result.p_value < 0.05),
        "hazard_ratio": {
            "value": _finite(round(hr, 4)),
            "ci_lower": _finite(round(hr_lower, 4)),
            "ci_upper": _finite(round(hr_upper, 4)),
            "label": f"HR {hr:.2f} (95% CI {hr_lower:.2f}–{hr_upper:.2f})" if np.isfinite(hr) else "HR not estimable",
        },
        "median_survival": {
            group_a_name: km_a["median"],
            group_b_name: km_b["median"],
        },
        "km_curves": {
            group_a_name: km_a["curve"],
            group_b_name: km_b["curve"],
        },
        "n_patients": {
            group_a_name: int(len(ipd_a)),
            group_b_name: int(len(ipd_b)),
        },
        "n_events": {
            group_a_name: int(ipd_a["event"].sum()),
            group_b_name: int(ipd_b["event"].sum()),
        },
    }


def compute_hazard_ratio(
    ipd_a: pd.DataFrame,
    ipd_b: pd.DataFrame,
) -> tuple:
    """
    Estimate HR(B/A) and 95% CI using Cox PH model.
    Falls back to Mantel-Haenszel estimator if Cox fails.
    """
    try:
        if not LIFELINES_AVAILABLE:
            raise ImportError

        combined = pd.concat([
            ipd_a.assign(group=0),
            ipd_b.assign(group=1),
        ]).reset_index(drop=True)

        cph = CoxPHFitter()
        cph.fit(combined, duration_col="time", event_col="event")
        summary = cph.summary
        coef = float(summary.loc["group", "coef"])
        se = float(summary.loc["group", "se(coef)"])

        hr = np.exp(coef)
        hr_lower = np.exp(coef - 1.96 * se)
        hr_upper = np.exp(coef + 1.96 * se)
        return hr, hr_lower, hr_upper

    except Exception:
        # Mantel-Haenszel fallback
        return _mantel_haenszel_hr(ipd_a, ipd_b)


def _mantel_haenszel_hr(
    ipd_a: pd.DataFrame,
    ipd_b: pd.DataFrame,
) -> tuple:
    """Simplified Mantel-Haenszel HR estimate."""
    all_times = np.sort(np.unique(
        np.concatenate([
            ipd_a[ipd_a["event"] == 1]["time"].values,
            ipd_b[ipd_b["event"] == 1]["time"].values,
        ])
    ))

    numerator = 0.0
    denominator = 0.0
    var_sum = 0.0

    for t in all_times:
        n_a = (ipd_a["time"] >= t).sum()
        n_b = (ipd_b["time"] >= t).sum()
        d_a = ((ipd_a["time"] == t) & (ipd_a["event"] == 1)).sum()
        d_b = ((ipd_b["time"] == t) & (ipd_b["event"] == 1)).sum()
        n = n_a + n_b
        d = d_a + d_b

        if n < 2 or d == 0:
            continue

        numerator += d_a * n_b / n
        denominator += d_b * n_a / n
        var_sum += d_a * d_b * (n_a + n_b - d_a - d_b) / (n * n * (n - 1)) if n > 1 else 0

    if denominator == 0:
        return 1.0, 0.0, float("inf")

    hr = numerator / denominator
    se_log_hr = np.sqrt(var_sum) / (numerator + 1e-9)
    hr_lower = np.exp(np.log(hr) - 1.96 * se_log_hr)
    hr_upper = np.exp(np.log(hr) + 1.96 * se_log_hr)
    return hr, hr_lower, hr_upper


def fit_km(ipd: pd.DataFrame, label: str = "Group") -> Dict[str, Any]:
    """Fit KM estimator and return curve data + median."""
    if LIFELINES_AVAILABLE:
        kmf = KaplanMeierFitter(label=label)
        kmf.fit(ipd["time"], event_observed=ipd["event"])
        timeline = kmf.timeline
        sf = kmf.survival_function_[label].values
        median = float(kmf.median_survival_time_)

        return {
            "median": _finite(median),
            "curve": [
                {"time": float(t), "survival": float(s)}
                for t, s in zip(timeline, sf)
            ],
        }
    else:
        # Manual KM computation
        return _manual_km(ipd, label)


def _manual_km(ipd: pd.DataFrame, label: str) -> Dict[str, Any]:
    """Manual KM computation without lifelines."""
    df = ipd.sort_values("time").reset_index(drop=True)
    times = df["time"].values
    events = df["event"].values
    n = len(df)

    unique_times = np.sort(np.unique(times[events == 1]))
    curve = [{"time": 0.0, "survival": 1.0}]
    s = 1.0

    for t in unique_times:
        at_risk = (times >= t).sum()
        deaths = ((times == t) & (events == 1)).sum()
        s *= 1.0 - deaths / at_risk
        curve.append({"time": float(t), "survival": float(s)})

    # Median: first time S <= 0.5
    median = None
    for pt in curve:
        if pt["survival"] <= 0.5:
            median = pt["time"]
            break

    return {"median": median, "curve": curve}


def _manual_logrank(
    ipd_a: pd.DataFrame,
    ipd_b: pd.DataFrame,
    group_a_name: str,
    group_b_name: str,
) -> Dict[str, Any]:
    """Manual log-rank test without lifelines."""
    event_times = np.sort(np.unique(
        np.concatenate([
            ipd_a[ipd_a["event"] == 1]["time"].values,
            ipd_b[ipd_b["event"] == 1]["time"].values,
        ])
    ))

    O_a, E_a = 0.0, 0.0
    V = 0.0

    for t in event_times:
        n_a = (ipd_a["time"] >= t).sum()
        n_b = (ipd_b["time"] >= t).sum()
        d_a = ((ipd_a["time"] == t) & (ipd_a["event"] == 1)).sum()
        d_b = ((ipd_b["time"] == t) & (ipd_b["event"] == 1)).sum()
        n = n_a + n_b
        d = d_a + d_b

        if n == 0:
            continue

        e_a = d * n_a / n
        O_a += d_a
        E_a += e_a

        if n > 1:
            V += d * n_a * n_b * (n - d) / (n * n * (n - 1))

    if V == 0:
        return {"test": "log-rank", "p_value": 1.0, "test_statistic": 0.0, "significant": False}

    chi2 = (O_a - E_a) ** 2 / V
    p_value = float(1 - stats.chi2.cdf(chi2, df=1))

    hr, hr_lower, hr_upper = _mantel_haenszel_hr(ipd_a, ipd_b)
    km_a = _manual_km(ipd_a, group_a_name)
    km_b = _manual_km(ipd_b, group_b_name)

    return {
        "test": "log-rank",
        "p_value": p_value,
        "test_statistic": float(chi2),
        "significant": bool(p_value < 0.05),
        "hazard_ratio": {
            "value": _finite(round(hr, 4)),
            "ci_lower": _finite(round(hr_lower, 4)),
            "ci_upper": _finite(round(hr_upper, 4)),
            "label": f"HR {hr:.2f} (95% CI {hr_lower:.2f}–{hr_upper:.2f})" if np.isfinite(hr) else "HR not estimable",
        },
        "median_survival": {
            group_a_name: km_a["median"],
            group_b_name: km_b["median"],
        },
        "km_curves": {
            group_a_name: km_a["curve"],
            group_b_name: km_b["curve"],
        },
        "n_patients": {
            group_a_name: int(len(ipd_a)),
            group_b_name: int(len(ipd_b)),
        },
        "n_events": {
            group_a_name: int(ipd_a["event"].sum()),
            group_b_name: int(ipd_b["event"].sum()),
        },
    }
