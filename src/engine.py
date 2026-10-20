"""
Clean-Room Statistical Calculation Engine for Paired Samples t-Test (t-paired).

Implements the mathematical and behavioral specification defined in SPEC.md:
- Degrees of freedom: df = N - 1
- Noncentrality parameter: delta = sqrt(N) * dz (power uses |delta|)
- Critical t: central Student-t quantile at 1 - alpha (1-tailed) or 1 - alpha/2 (2-tailed)
- Noncentral t CDF: Lenth (1989) Algorithm AS 243 bidirectional Poisson-Beta series
- A-priori sample size solver: normal-approximation bracketing + Brent-Dekker root finding
  (rtol = 2^-53 = 1.1102230246251565e-16, max_iter = 300)
- Sample size rounding rule: ceil(floor(N_cont * 1e10 + 0.5) / 1e10)
"""

from __future__ import annotations

import math
from typing import Any, Callable, Dict, Optional


class ValidationError(ValueError):
    """Raised when an input parameter violates the admissible range in SPEC.md."""


# ============================================================================
# Special Functions & Statistical Distributions (IEEE-754 double precision)
# ============================================================================

def betainc_reg(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta function I_x(a, b) via Lentz's continued fraction."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    if x > (a + 1.0) / (a + b + 2.0):
        return 1.0 - betainc_reg(b, a, 1.0 - x)

    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    log_front = a * math.log(x) + b * math.log(1.0 - x) - lbeta
    if log_front < -740.0:
        return 0.0
    front = math.exp(log_front) / a

    tiny = 1e-300
    f = 1.0
    c = 1.0
    d = 0.0

    for m in range(0, 500):
        if m == 0:
            num = 1.0
        else:
            k = m // 2
            if m % 2 == 1:
                num = -((a + k) * (a + b + k) * x) / ((a + 2.0 * k) * (a + 2.0 * k + 1.0))
            else:
                num = (k * (b - k) * x) / ((a + 2.0 * k - 1.0) * (a + 2.0 * k))

        d = 1.0 + num * d
        if abs(d) < tiny:
            d = tiny
        d = 1.0 / d

        c = 1.0 + num / c
        if abs(c) < tiny:
            c = tiny

        cd = c * d
        f *= cd
        if m > 0 and abs(1.0 - cd) <= 1.1102230246251565e-16:
            break

    return min(1.0, max(0.0, front * (f - 1.0)))


def central_t_cdf(t_val: float, df: float) -> float:
    """Cumulative distribution function of the central Student-t distribution."""
    if df <= 0.0:
        raise ValidationError("TDist-Cdf: input parameter out of range")
    if t_val == 0.0:
        return 0.5
    if math.isinf(t_val):
        return 1.0 if t_val > 0 else 0.0
    x = df / (df + t_val * t_val)
    p = 0.5 * betainc_reg(0.5 * df, 0.5, x)
    return 1.0 - p if t_val >= 0.0 else p


def central_t_pdf(t_val: float, df: float) -> float:
    """Probability density function of the central Student-t distribution."""
    log_c = (
        math.lgamma(0.5 * (df + 1.0))
        - 0.5 * math.log(df * math.pi)
        - math.lgamma(0.5 * df)
    )
    log_k = -0.5 * (df + 1.0) * math.log(1.0 + (t_val * t_val) / df)
    return math.exp(log_c + log_k)


def norm_ppf(p: float) -> float:
    """Inverse standard normal CDF (Acklam rational approximation + Halley step)."""
    if p <= 0.0:
        return -math.inf
    if p >= 1.0:
        return math.inf
    if p == 0.5:
        return 0.0

    a = (
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    )
    b = (
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    )
    c = (
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    )
    d = (
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    )

    p_low = 0.02425
    p_high = 1.0 - p_low
    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        z = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
    elif p <= p_high:
        q = p - 0.5
        r = q * q
        z = (
            (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5])
            * q
            / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
        )
    else:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        z = -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )

    # One Newton-Raphson refinement step using math.erfc
    cdf_z = 0.5 * math.erfc(-z / math.sqrt(2.0))
    pdf_z = math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)
    if pdf_z > 0.0:
        z -= (cdf_z - p) / pdf_z
    return z


def central_t_ppf(p: float, df: float) -> float:
    """Inverse CDF (quantile) of the central Student-t distribution."""
    if not (0.0 < p < 1.0) or df <= 0.0:
        raise ValidationError("TDist-Quantile: input parameter out of range")
    if p == 0.5:
        return 0.0
    if p < 0.5:
        return -central_t_ppf(1.0 - p, df)

    # Hill (1970) Cornish-Fisher asymptotic expansion starting guess (as in 0x4514f0)
    z = norm_ppf(p)
    z2 = z * z
    g1 = (z2 + 1.0) / 4.0
    g2 = ((5.0 * z2 + 16.0) * z2 + 3.0) / 96.0
    g3 = (((3.0 * z2 + 19.0) * z2 + 17.0) * z2 - 15.0) / 384.0
    g4 = ((((79.0 * z2 + 776.0) * z2 + 1482.0) * z2 - 1920.0) * z2 - 945.0) / 92160.0
    x = z * (1.0 + (g1 + (g2 + (g3 + g4 / df) / df) / df) / df)
    if df <= 2.5:
        # Exact closed forms for df=1 (Cauchy) and df=2 as safe anchors
        if abs(df - 1.0) < 1e-12:
            return math.tan(math.pi * (p - 0.5))
        if abs(df - 2.0) < 1e-12:
            return (2.0 * p - 1.0) / math.sqrt(2.0 * p * (1.0 - p))
        x = max(z, (1.0 - p) ** (-1.0 / df))

    # Bracket and refine via safeguarded Newton-Raphson
    lo = 0.0
    hi = max(x * 2.0, 10.0)
    while central_t_cdf(hi, df) < p:
        lo = hi
        hi *= 2.0

    cur = min(max(x, lo), hi)
    for _ in range(80):
        err = central_t_cdf(cur, df) - p
        if abs(err) <= 1e-15:
            break
        if err < 0.0:
            lo = cur
        else:
            hi = cur
        slope = central_t_pdf(cur, df)
        if slope > 1e-30:
            nxt = cur - err / slope
            if lo < nxt < hi:
                cur = nxt
            else:
                cur = 0.5 * (lo + hi)
        else:
            cur = 0.5 * (lo + hi)
        if abs(hi - lo) <= 1e-15 * max(1.0, abs(cur)):
            break

    return cur


def noncentral_t_cdf(t_val: float, df: float, delta: float) -> float:
    """
    Cumulative distribution function of the noncentral Student-t distribution.

    Implements Lenth (1989) Algorithm AS 243 with forward and backward summation
    from the Poisson mode k0 = floor(delta^2 / 2), matching G*Power's TDistribution::cdf.
    """
    if df <= 0.0:
        raise ValidationError("TDist-Cdf: input parameter out of range")
    if abs(delta) < 1e-100:
        return central_t_cdf(t_val, df)
    if df > 1e7:
        # Normal approximation for huge df
        return 0.5 * math.erfc(-(t_val - delta) / math.sqrt(2.0))

    negate = False
    if t_val < 0.0:
        t_val = -t_val
        delta = -delta
        negate = True

    x = (t_val * t_val) / (t_val * t_val + df)
    d2 = delta * delta
    half_d2 = 0.5 * d2
    norm_neg = 0.5 * math.erfc(delta / math.sqrt(2.0))

    if x == 0.0:
        res = norm_neg
        return 1.0 - res if negate else res

    k0 = int(math.floor(half_d2))
    half_df = 0.5 * df
    sign_delta = 1.0 if delta > 0.0 else -1.0
    log_half_d2 = math.log(half_d2) if half_d2 > 0.0 else -1e300

    def term_at(k: int) -> float:
        log_p = -half_d2 + k * log_half_d2 - math.lgamma(k + 1.0)
        log_q = -half_d2 + (k + 0.5) * log_half_d2 - math.lgamma(k + 1.5)
        p_even = math.exp(log_p) if log_p > -745.0 else 0.0
        q_odd = sign_delta * (math.exp(log_q) if log_q > -745.0 else 0.0)
        if p_even == 0.0 and q_odd == 0.0:
            return 0.0
        ix_even = betainc_reg(k + 0.5, half_df, x)
        ix_odd = betainc_reg(k + 1.0, half_df, x)
        return p_even * ix_even + q_odd * ix_odd

    total = term_at(k0)
    eps = 5.551115123125783e-17  # 2^-54 stopping criterion

    # Forward series: k = k0 + 1, k0 + 2, ...
    for step in range(1, 50000):
        k = k0 + step
        val = term_at(k)
        total += val
        if total != 0.0 and abs(val) / abs(total) <= eps:
            break

    # Backward series: k = k0 - 1, k0 - 2, ..., 0
    for k in range(k0 - 1, -1, -1):
        val = term_at(k)
        total += val
        if total != 0.0 and abs(val) / abs(total) <= eps:
            break

    prob = min(1.0, max(0.0, norm_neg + 0.5 * total))
    return 1.0 - prob if negate else prob


# ============================================================================
# Root-Finding & Sample Size Rounding (SPEC.md Section 2.4)
# ============================================================================

def brent_dekker_solve(
    func: Callable[[float], float],
    x_low: float,
    x_high: float,
    max_iter: int = 300,
) -> float:
    """
    Brent-Dekker root-finding algorithm matching SPEC.md Section 2.4.3:
    Stops when |0.5 * (c - b)| <= 1.1102230246251565e-16 * |b| or f(b) == 0.0.
    """
    a = x_low
    b = x_high
    c = x_high
    fa = func(a)
    fb = func(b)
    fc = fb
    d = b - a
    e = d

    if fa * fb > 0.0:
        return 0.0

    eps = 1.1102230246251565e-16  # 2^-53

    for _ in range(max_iter):
        if (fb > 0.0 and fc > 0.0) or (fb < 0.0 and fc < 0.0):
            c = a
            fc = fa
            d = b - a
            e = d

        if abs(fc) < abs(fb):
            a = b
            b = c
            c = a
            fa = fb
            fb = fc
            fc = fa

        tol1 = abs(b) * eps
        xm = 0.5 * (c - b)
        if fb == 0.0 or abs(xm) <= tol1:
            return b

        if abs(e) >= tol1 and abs(fa) > abs(fb):
            s = fb / fa
            if a == c:
                p = 2.0 * xm * s
                q = 1.0 - s
            else:
                q = fa / fc
                r = fb / fc
                p = s * (2.0 * xm * q * (q - r) - (b - a) * (r - 1.0))
                q = (q - 1.0) * (r - 1.0) * (s - 1.0)
            if p > 0.0:
                q = -q
            p = abs(p)
            min1 = 3.0 * xm * q - abs(tol1 * q)
            min2 = abs(e * q)
            if 2.0 * p < (min1 if min1 < min2 else min2):
                e = d
                d = p / q
            else:
                d = xm
                e = d
        else:
            d = xm
            e = d

        a = b
        fa = fb
        if abs(d) > tol1:
            b += d
        else:
            b += tol1 if xm > 0.0 else -tol1
        fb = func(b)

    return b


def round_up_sample_size(n_cont: float) -> int:
    """
    10-decimal-place pre-rounded ceiling rule (SPEC.md Section 2.4.4):
      N_rounded = floor(N_cont * 1e10 + 0.5) / 1e10
      N = ceil(N_rounded)
    """
    scaled = math.floor(n_cont * 10000000000.0 + 0.5)
    _, ip = math.modf(scaled)
    n_rounded = ip / 10000000000.0
    return int(math.ceil(n_rounded))


# ============================================================================
# Effect Size (dz) Calculator (SPEC.md Section 2.1)
# ============================================================================

def compute_effect_size_dz(
    *,
    mean_dz: Optional[float] = None,
    sd_dz: Optional[float] = None,
    mean1: Optional[float] = None,
    mean2: Optional[float] = None,
    sd1: Optional[float] = None,
    sd2: Optional[float] = None,
    corr: Optional[float] = None,
) -> float:
    """
    Computes Cohen's dz for paired samples either from difference parameters
    (mean_dz, sd_dz) or from group parameters (mean1, mean2, sd1, sd2, corr).
    """
    if mean_dz is not None or sd_dz is not None:
        if mean_dz is None or sd_dz is None:
            raise ValidationError("Both mean_dz and sd_dz must be provided to compute dz from differences.")
        if sd_dz <= 1e-12:
            raise ValidationError("The standard deviation must be greater than 1e-12")
        return float(mean_dz) / float(sd_dz)

    if any(v is not None for v in (mean1, mean2, sd1, sd2, corr)):
        if any(v is None for v in (mean1, mean2, sd1, sd2, corr)):
            raise ValidationError("mean1, mean2, sd1, sd2, and corr are all required to compute dz from group parameters.")
        assert mean1 is not None and mean2 is not None and sd1 is not None and sd2 is not None and corr is not None
        if sd1 <= 1e-12 or sd2 <= 1e-12:
            raise ValidationError("The standard deviation must be greater than 1e-12")
        if corr <= -0.99999999 or corr > 0.99999999:
            raise ValidationError("Correlation lies outside of admissible range (-1+1e-8,1-1e-8)")
        var_diff = (sd1 * sd1) + (sd2 * sd2) - (2.0 * corr * sd1 * sd2)
        sd_diff = math.sqrt(max(0.0, var_diff))
        return abs(mean1 - mean2) / sd_diff

    raise ValidationError("Effect size dz (or group/difference parameters) must be provided.")


# ============================================================================
# Core Power & Sample Size Engine for t-paired (SPEC.md Sections 2.2 - 2.4)
# ============================================================================

def _compute_power_for_n(dz: float, alpha: float, n_val: float, tails: int) -> Dict[str, float]:
    """Internal core calculation of df, critical_t, ncp, and power for continuous or integer N."""
    df = n_val - 1.0
    p_crit = 1.0 - (alpha if tails == 1 else 0.5 * alpha)
    t_crit_abs = central_t_ppf(p_crit, df)
    t_crit = -t_crit_abs if dz < 0.0 else t_crit_abs
    abs_ncp = math.sqrt(n_val) * abs(dz)
    signed_ncp = math.sqrt(n_val) * dz

    upper_tail = 1.0 - noncentral_t_cdf(t_crit_abs, df, abs_ncp)
    if tails == 1:
        power = upper_tail
    else:
        lower_tail = noncentral_t_cdf(-t_crit_abs, df, abs_ncp)
        power = upper_tail + lower_tail

    return {
        "df": df,
        "critical": t_crit,
        "ncp": signed_ncp,
        "abs_ncp": abs_ncp,
        "power": power,
    }


def _initial_sample_size_guess(dz: float, alpha: float, target_power: float, tails: int) -> float:
    """Normal-approximation initial sample size guess (SPEC.md Section 2.4.2)."""
    min_n = 2.0
    z_alpha = norm_ppf(1.0 - (alpha if tails == 1 else 0.5 * alpha))
    z_power = norm_ppf(target_power)
    denom = dz * dz
    if denom <= 0.0:
        return min_n
    guess = ((z_alpha + z_power) ** 2) / denom
    return max(min_n, guess)


def _bracket_sample_size(dz: float, alpha: float, target_power: float, tails: int) -> tuple[float, float]:
    """Brackets the sample size root [n_low, n_high] starting from normal approximation."""
    min_bound = 2.0
    guess = max(min_bound, _initial_sample_size_guess(dz, alpha, target_power, tails))
    f_guess = _compute_power_for_n(dz, alpha, guess, tails)["power"] - target_power

    if f_guess <= 0.0:
        n_low = guess
        n_high = max(min_bound, 2.0 * guess)
        for _ in range(100):
            if _compute_power_for_n(dz, alpha, n_high, tails)["power"] >= target_power:
                break
            n_low = n_high
            n_high = n_high + n_high
    else:
        n_high = guess
        n_low = max(min_bound, 0.5 * (guess + min_bound))
        while _compute_power_for_n(dz, alpha, n_low, tails)["power"] > target_power and n_low > min_bound:
            n_high = n_low
            nxt = 0.5 * (n_low + min_bound)
            if abs(nxt - min_bound) <= 1e-12:
                n_low = min_bound
                break
            n_low = nxt

    return n_low, n_high


def calculate_t_paired(
    *,
    mode: str,
    tails: int = 2,
    dz: Optional[float] = None,
    alpha: float = 0.05,
    power: Optional[float] = None,
    n_total: Optional[int] = None,
    mean_dz: Optional[float] = None,
    sd_dz: Optional[float] = None,
    mean1: Optional[float] = None,
    mean2: Optional[float] = None,
    sd1: Optional[float] = None,
    sd2: Optional[float] = None,
    corr: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Executes 'a-priori' or 'post-hoc' power analysis for the Paired Samples t-Test ('t-paired').

    Returns a dictionary matching the CONTRACT.md & SPEC.md schema.
    Raises ValidationError on invalid inputs.
    """
    mode_norm = mode.strip().lower().replace("_", "-")
    if mode_norm in ("apriori", "a-priori"):
        mode_norm = "a-priori"
    elif mode_norm in ("posthoc", "post-hoc"):
        mode_norm = "post-hoc"
    else:
        raise ValidationError(f"Unsupported analysis mode '{mode}'. Use 'a-priori' or 'post-hoc'.")

    if tails not in (1, 2):
        raise ValidationError("Tails must be 1 or 2.")

    # Resolve dz if not directly supplied
    if dz is None:
        dz = compute_effect_size_dz(
            mean_dz=mean_dz,
            sd_dz=sd_dz,
            mean1=mean1,
            mean2=mean2,
            sd1=sd1,
            sd2=sd2,
            corr=corr,
        )
    else:
        dz = float(dz)

    alpha = float(alpha)

    if mode_norm == "a-priori":
        if power is None:
            raise ValidationError("Target power (--power) is required for a-priori analysis.")
        power = float(power)

        # Validation order matching SPEC.md:
        if abs(dz) < 1e-5:
            raise ValidationError(
                "In an a priori analysis, the absolute value of the effect size be greater than 0.00001."
            )
        if dz < -20.0 or dz > 20.0:
            raise ValidationError("Effect size dz is outside the admissible range (-20, 20)")
        if alpha < 1e-7 or alpha > 0.9999999:
            raise ValidationError("Alpha is outside the admissible range (1e-07, 0.9999999)")
        if power < 1e-7 or power > 0.9999999:
            raise ValidationError("Power is outside the admissible range (1e-07, 0.9999999)")
        if power < alpha:
            raise ValidationError("Power must be greater than or equal to alpha.")

        n_low, n_high = _bracket_sample_size(dz, alpha, power, tails)
        f_low = _compute_power_for_n(dz, alpha, n_low, tails)["power"] - power
        if f_low >= 0.0:
            n_cont = n_low
        else:
            n_cont = brent_dekker_solve(
                lambda x: _compute_power_for_n(dz, alpha, x, tails)["power"] - power,
                n_low,
                n_high,
                max_iter=300,
            )

        n_int = round_up_sample_size(n_cont)
        if n_int < round_up_sample_size(n_low):
            n_int = round_up_sample_size(n_low)
        n_int = max(2, n_int)

        core = _compute_power_for_n(dz, alpha, float(n_int), tails)
        return {
            "test": "t-paired",
            "mode": "a-priori",
            "tails": tails,
            "dz": round(dz, 7),
            "alpha": round(alpha, 7),
            "target_power": round(power, 7),
            "n_total": int(n_int),
            "total_sample_size": int(n_int),
            "actual_power": round(core["power"], 7),
            "power": round(core["power"], 7),
            "critical": round(core["critical"], 7),
            "critical_t": round(core["critical"], 7),
            "df": int(round(core["df"])),
            "ncp": round(core["ncp"], 7),
            "noncentrality_parameter": round(core["ncp"], 7),
        }

    # mode_norm == "post-hoc"
    if n_total is None:
        raise ValidationError("Total sample size (--n) is required for post-hoc analysis.")
    try:
        n_int = int(n_total)
        if float(n_total) != float(n_int):
            raise ValidationError("Total sample size must be an integer.")
    except (TypeError, ValueError) as exc:
        raise ValidationError("Total sample size must be an integer.") from exc

    if dz < -20.0 or dz > 20.0:
        raise ValidationError("Effect size dz is outside the admissible range (-20, 20)")
    if alpha < 1e-7 or alpha > 0.9999999:
        raise ValidationError("Alpha is outside the admissible range (1e-07, 0.9999999)")
    if n_int < 3 or n_int > 2147483646:
        raise ValidationError("Total sample size is outside the admissible range (3, 2147483646)")

    core = _compute_power_for_n(dz, alpha, float(n_int), tails)
    return {
        "test": "t-paired",
        "mode": "post-hoc",
        "tails": tails,
        "dz": round(dz, 7),
        "alpha": round(alpha, 7),
        "n_total": int(n_int),
        "total_sample_size": int(n_int),
        "power": round(core["power"], 7),
        "actual_power": round(core["power"], 7),
        "critical": round(core["critical"], 7),
        "critical_t": round(core["critical"], 7),
        "df": int(round(core["df"])),
        "ncp": round(core["ncp"], 7),
        "noncentrality_parameter": round(core["ncp"], 7),
    }
