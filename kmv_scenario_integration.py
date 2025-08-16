import numpy as np
import pandas as pd
from math import sqrt
from scipy.stats import norm
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Dict, List

# ---------- KMV / Merton core ----------
def solve_assets(E, E_vol, D, r, T, tol=1e-7, max_iter=200):
    V = E + D
    sV = max(E_vol * 0.8, 1e-6)
    for _ in range(max_iter):
        d1 = (np.log(max(V, 1e-12)/D) + (r + 0.5 * sV**2) * T) / (sV * sqrt(T))
        d2 = d1 - sV * sqrt(T)
        N1 = norm.cdf(d1); N2 = norm.cdf(d2)
        Eq = V * N1 - D * np.exp(-r * T) * N2
        dE_dV = max(N1, 1e-6)
        Eq_vol_imp = (N1 * V / max(Eq, 1e-8)) * sV
        f1 = Eq - E
        f2 = Eq_vol_imp - E_vol
        J11 = dE_dV
        J22 = max(N1 * V / max(Eq, 1e-8), 1e-6)
        V_new  = V  - f1 / J11
        sV_new = sV - f2 / J22
        if abs(V_new - V) < tol and abs(sV_new - sV) < tol:
            V, sV = V_new, sV_new
            break
        V, sV = V_new, sV_new
    return max(V, 1e-6), max(sV, 1e-6)

def merton_dd_pd(E, E_vol, D, r, T):
    V, sV = solve_assets(E, E_vol, D, r, T)
    d1 = (np.log(V / D) + (r + 0.5 * sV**2) * T) / (sV * sqrt(T))
    d2 = d1 - sV * sqrt(T)
    DD = d2
    PD = norm.cdf(-DD)
    return V, sV, DD, PD

# ---------- Activist scenario mapping ----------
@dataclass
class Impact:
    profit_pct: float
    mcap_pct: float

BASE_MAP   = {10: Impact(20, 15), 20: Impact(40, 30), 30: Impact(60, 45)}
LIGHT_MAP  = {10: Impact(15, 12), 20: Impact(30, 24), 30: Impact(45, 36)}
SEVERE_MAP = {10: Impact(25, 18), 20: Impact(50, 35), 30: Impact(75, 55)}
SCENARIOS = {"Base": BASE_MAP, "Light": LIGHT_MAP, "Severe": SEVERE_MAP}

def _interp(x0, x1, y0, y1, x):
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)

def get_impact(rev_drop, mp):
    keys = sorted(mp.keys())
    if rev_drop in mp:
        return mp[rev_drop]
    if rev_drop < keys[0]:
        k0, k1 = keys[0], keys[1]
    elif rev_drop > keys[-1]:
        k0, k1 = keys[-2], keys[-1]
    else:
        for i in range(len(keys) - 1):
            if keys[i] <= rev_drop <= keys[i + 1]:
                k0, k1 = keys[i], keys[i + 1]; break
    p = _interp(k0, k1, mp[k0].profit_pct, mp[k1].profit_pct, rev_drop)
    m = _interp(k0, k1, mp[k0].mcap_pct,   mp[k1].mcap_pct,   rev_drop)
    return Impact(round(p, 2), round(m, 2))

class VolShockRule:
    def __init__(self, mode="linear", gamma=0.5):
        assert mode in ("none", "linear")
        self.mode = mode
        self.gamma = gamma
    def apply(self, equity_vol, sales_decline_pct):
        if self.mode == "none":
            return equity_vol
        frac = max(sales_decline_pct, 0.0) / 100.0
        return max(equity_vol * (1.0 + self.gamma * frac), 1e-6)

# ---------- サンプルデータ ----------
sample_data = [
    {'firm': 'FirmA', 'equity_value': 100, 'equity_vol': 0.3, 'debt_face': 80, 'risk_free': 0.01, 'horizon_years': 1},
    {'firm': 'FirmB', 'equity_value': 200, 'equity_vol': 0.25, 'debt_face': 150, 'risk_free': 0.015, 'horizon_years': 1},
    {'firm': 'FirmC', 'equity_value': 150, 'equity_vol': 0.28, 'debt_face': 120, 'risk_free': 0.012, 'horizon_years': 1},
]

def run_pipeline_sample(
    base_data,
    sales_range=None,
    scenarios=None,
    vol_rule=None
):
    if sales_range is None:
        sales_range = list(range(0, 31, 10))  # 0,10,20,30%
    if scenarios is None:
        scenarios = SCENARIOS
    if vol_rule is None:
        vol_rule = VolShockRule(mode="linear", gamma=0.5)

    rows = []
    for r in base_data:
        firm = r["firm"]
        E0, sE0, D, rf, T = float(r["equity_value"]), float(r["equity_vol"]), float(r["debt_face"]), float(r["risk_free"]), float(r["horizon_years"])

        # Baseline PD (no sales decline)
        V0, sV0, DD0, PD0 = merton_dd_pd(E0, sE0, D, rf, T)
        rows.append({
            "firm": firm, "scenario": "Baseline", "sales_decline_pct": 0,
            "equity_value": E0, "equity_vol": sE0,
            "asset_value": V0, "asset_vol": sV0, "DD": DD0, "PD": PD0
        })

        for scen_name, mp in scenarios.items():
            for s in sales_range:
                if s == 0: continue
                impact = get_impact(s, mp)
                E_adj = max(E0 * (1.0 - impact.mcap_pct / 100.0), 1e-6)
                sE_adj = vol_rule.apply(sE0, s)
                V, sV, DD, PD = merton_dd_pd(E_adj, sE_adj, D, rf, T)
                rows.append({
                    "firm": firm, "scenario": scen_name, "sales_decline_pct": s,
                    "equity_value": E_adj, "equity_vol": sE_adj,
                    "asset_value": V, "asset_vol": sV, "DD": DD, "PD": PD,
                    "assumed_mcap_decline_pct": impact.mcap_pct,
                    "assumed_profit_decline_pct": impact.profit_pct
                })

    df = pd.DataFrame(rows)
    print(df)
    # グラフ例: FirmAのPD推移
    for firm in df["firm"].unique():
        sub = df[(df["firm"] == firm) & (df["scenario"] != "Baseline")]
        if sub.empty:
            continue
        plt.figure()
        for scen_name in scenarios.keys():
            y = sub[sub["scenario"] == scen_name].sort_values("sales_decline_pct")["PD"].values
            x = sorted(sub["sales_decline_pct"].unique())
            if len(y) == len(x):
                plt.plot(x, y, label=scen_name)
        plt.title(f"PD vs Sales Decline — {firm}")
        plt.xlabel("Sales Decline (%)"); plt.ylabel("Probability of Default (PD)")
        plt.grid(True); plt.legend(); plt.tight_layout()
        plt.show()

# 実行
run_pipeline_sample(sample_data)