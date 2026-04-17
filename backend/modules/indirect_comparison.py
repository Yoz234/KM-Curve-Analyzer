"""
Indirect Treatment Comparison using the Bucher method.

Reference: Bucher HC et al. (1997) The results of direct and indirect
treatment comparisons in meta-analysis of randomized controlled trials.
J Clin Epidemiol, 50(6):683-691.

Assumption: A common comparator arm B is used in two trials:
  Trial 1: A vs B  ->  ln(HR_AB), SE_AB
  Trial 2: B vs C  ->  ln(HR_BC), SE_BC

Indirect estimate for A vs C:
  ln(HR_AC) = ln(HR_AB) - ln(HR_BC)      [i.e., ln(HR_AB/HR_BC)]
  Var(ln(HR_AC)) = Var(ln(HR_AB)) + Var(ln(HR_BC))
  SE_AC = sqrt(SE_AB^2 + SE_BC^2)

Note: HR convention used throughout is HR(treatment / reference).
"""

import numpy as np
from scipy import stats
from typing import Dict, Any, Optional


def bucher_indirect_comparison(
    hr_ab: float,
    ci_lower_ab: float,
    ci_upper_ab: float,
    hr_bc: float,
    ci_lower_bc: float,
    ci_upper_bc: float,
    alpha: float = 0.05,
    label_a: str = "A",
    label_b: str = "B",
    label_c: str = "C",
) -> Dict[str, Any]:
    """
    Bucher indirect comparison: estimate HR for A vs C via common comparator B.

    HR convention: HR_AB = hazard(A) / hazard(B)
                   HR_BC = hazard(B) / hazard(C)
    Therefore:     HR_AC = HR_AB * HR_BC  (chain rule on log scale)

    Args:
        hr_ab:        Point estimate HR(A vs B)
        ci_lower_ab:  Lower 95% CI bound for HR_AB
        ci_upper_ab:  Upper 95% CI bound for HR_AB
        hr_bc:        Point estimate HR(B vs C)
        ci_lower_bc:  Lower 95% CI bound for HR_BC
        ci_upper_bc:  Upper 95% CI bound for HR_BC
        alpha:        Significance level (default 0.05)
        label_a/b/c:  Treatment labels for reporting

    Returns:
        Dictionary with indirect HR_AC estimate, CI, p-value, and summary text
    """
    z_crit = stats.norm.ppf(1 - alpha / 2)  # 1.96 for alpha=0.05

    # Recover SE from CI: CI = exp(ln(HR) ± z * SE)
    # => SE = (ln(upper) - ln(lower)) / (2 * z)
    ln_hr_ab = np.log(hr_ab)
    se_ab = (np.log(ci_upper_ab) - np.log(ci_lower_ab)) / (2 * z_crit)

    ln_hr_bc = np.log(hr_bc)
    se_bc = (np.log(ci_upper_bc) - np.log(ci_lower_bc)) / (2 * z_crit)

    # Indirect estimate: ln(HR_AC) = ln(HR_AB) + ln(HR_BC)
    # (A vs B treatment, B vs C treatment -> A vs C: multiply HRs)
    ln_hr_ac = ln_hr_ab + ln_hr_bc
    se_ac = np.sqrt(se_ab**2 + se_bc**2)

    hr_ac = float(np.exp(ln_hr_ac))
    hr_ac_lower = float(np.exp(ln_hr_ac - z_crit * se_ac))
    hr_ac_upper = float(np.exp(ln_hr_ac + z_crit * se_ac))

    # Two-sided p-value for H0: HR_AC = 1
    z_stat = ln_hr_ac / se_ac
    p_value = float(2 * (1 - stats.norm.cdf(abs(z_stat))))

    return {
        "method": "Bucher indirect comparison",
        "comparison": f"{label_a} vs {label_c} (via {label_b})",
        "inputs": {
            f"{label_a}_vs_{label_b}": {
                "hr": round(hr_ab, 4),
                "ci_lower": round(ci_lower_ab, 4),
                "ci_upper": round(ci_upper_ab, 4),
                "se_log_hr": round(se_ab, 4),
            },
            f"{label_b}_vs_{label_c}": {
                "hr": round(hr_bc, 4),
                "ci_lower": round(ci_lower_bc, 4),
                "ci_upper": round(ci_upper_bc, 4),
                "se_log_hr": round(se_bc, 4),
            },
        },
        "result": {
            "hr": round(hr_ac, 4),
            "ci_lower": round(hr_ac_lower, 4),
            "ci_upper": round(hr_ac_upper, 4),
            "se_log_hr": round(se_ac, 4),
            "z_statistic": round(z_stat, 4),
            "p_value": round(p_value, 4),
            "significant": p_value < alpha,
            "alpha": alpha,
            "label": (
                f"Indirect HR ({label_a} vs {label_c}) = "
                f"{hr_ac:.2f} "
                f"(95% CI {hr_ac_lower:.2f}–{hr_ac_upper:.2f}), "
                f"p = {p_value:.4f}"
            ),
        },
        "assumptions": [
            f"Common comparator: {label_b}",
            "Trials are sufficiently similar (exchangeability assumption)",
            "No effect modification across trials",
            "HR estimates are on the same scale and direction",
        ],
    }


def extract_hr_from_logrank_result(result: Dict[str, Any]) -> Dict[str, float]:
    """
    Convenience: pull HR + CI from compute_logrank() output.

    Returns dict: {'hr', 'ci_lower', 'ci_upper'}
    """
    hr_info = result.get("hazard_ratio", {})
    return {
        "hr": hr_info.get("value", 1.0),
        "ci_lower": hr_info.get("ci_lower", 0.5),
        "ci_upper": hr_info.get("ci_upper", 2.0),
    }


def indirect_from_ipd(
    ipd_a: "pd.DataFrame",  # noqa: F821
    ipd_b_trial1: "pd.DataFrame",  # noqa: F821
    ipd_b_trial2: "pd.DataFrame",  # noqa: F821
    ipd_c: "pd.DataFrame",  # noqa: F821
    label_a: str = "A",
    label_b: str = "B",
    label_c: str = "C",
) -> Dict[str, Any]:
    """
    Perform indirect comparison starting directly from IPD DataFrames.
    Runs two log-rank tests then applies Bucher method.
    """
    from .logrank import compute_logrank

    result_ab = compute_logrank(ipd_a, ipd_b_trial1, label_a, label_b)
    result_bc = compute_logrank(ipd_b_trial2, ipd_c, label_b, label_c)

    hr_ab_info = extract_hr_from_logrank_result(result_ab)
    hr_bc_info = extract_hr_from_logrank_result(result_bc)

    indirect = bucher_indirect_comparison(
        hr_ab=hr_ab_info["hr"],
        ci_lower_ab=hr_ab_info["ci_lower"],
        ci_upper_ab=hr_ab_info["ci_upper"],
        hr_bc=hr_bc_info["hr"],
        ci_lower_bc=hr_bc_info["ci_lower"],
        ci_upper_bc=hr_bc_info["ci_upper"],
        label_a=label_a,
        label_b=label_b,
        label_c=label_c,
    )

    return {
        "logrank_ab": result_ab,
        "logrank_bc": result_bc,
        "indirect_ac": indirect,
    }
