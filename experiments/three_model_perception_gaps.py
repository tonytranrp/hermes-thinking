#!/usr/bin/env python3
"""3-model perception gap analysis using the perception gap adjuster.

This script computes perception gap statistics for DeepSeek-V4-Pro,
Llama-Nemotron-8B, and GLM-5.1-FP8 using adjust_drift() directly.

Key insight: we use bias-corrected cosine similarity (not raw fingerprint
cosine similarity) for the perception inflation formula. The raw fingerprint
cosine similarity has inverted metric semantics for this calculation.
"""
import json, sys, statistics
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
from perception_gap_adjuster import PerceptionGapAdjuster

DIMS = ["concreteness", "technicality", "formality", "specificity", "agency",
        "temporality", "certainty", "complexity", "emotional", "scope"]


def _load_fingerprint(model):
    """Load bias vector for a model from fingerprint JSON files.

    GLM fingerprints are stored as raw probe ratings lists, not bias vectors.
    DeepSeek and Llama store normalized bias dicts.
    """
    exp_dir = Path(__file__).parent
    if model == "deepseek":
        fp = json.load(open(exp_dir / "semantic_fingerprint_deepseek.json"))
        return [fp["bias"][d] for d in DIMS]
    elif model == "llama":
        fp = json.load(open(exp_dir / "semantic_fingerprint_llama.json"))
        return [fp["bias"][d] for d in DIMS]
    elif model == "glm":
        fp = json.load(open(exp_dir / "semantic_fingerprint_glm.json"))
        bias = {}
        for i, dim in enumerate(DIMS):
            vals = [fp["probe_ratings"][p][i] for p in
                    ["technical", "casual", "formal", "creative", "procedural"]]
            bias[dim] = statistics.mean(vals)
        return [bias[d] for d in DIMS]
    return None


def _compute_pair_analysis(a_key, b_key, fp_a, fp_b, adj):
    """Compute perception gap for a model pair using adjust_drift().

    Must use adjust_drift() which applies bias-corrected cosine similarity,
    NOT raw fingerprint cosine similarity (which produces inverted percentages).
    """
    result = adj.adjust_drift(fp_a, fp_b, a_key, b_key)

    gap_magnitude = sum(v**2 for v in result["details"]["gap_vector"].values()) ** 0.5

    return {
        "raw_drift": result["raw_drift"],
        "adjusted_drift": result["adjusted_drift"],
        "perception_inflation": result["perception_inflation"],
        "inflation_pct": result["perception_inflation_pct"],
        "gap_magnitude": round(gap_magnitude, 4),
        "gap_vector": {k: round(v, 2) for k, v in result["details"]["gap_vector"].items()},
        "raw_similarity": round(1.0 - result["raw_drift"], 4),
        "adjusted_similarity": round(1.0 - result["adjusted_drift"], 4),
        "biggest_gaps": dict(sorted(
            result["details"]["gap_vector"].items(), key=lambda x: -abs(x[1])
        )[:3])
    }


def run_perception_analysis():
    """Run 3-model perception gap analysis."""
    adj = PerceptionGapAdjuster()

    fp_ds = _load_fingerprint("deepseek")
    fp_ll = _load_fingerprint("llama")
    fp_glm = _load_fingerprint("glm")

    pairs = [
        (("Llama-Nemotron-8B", fp_ll, "llama-nemotron-8b"),
         ("DeepSeek-V4-Pro", fp_ds, "deepseek-v4-pro")),
        (("DeepSeek-V4-Pro", fp_ds, "deepseek-v4-pro"),
         ("GLM-5.1-FP8", fp_glm, "glm-5.1-fp8")),
        (("Llama-Nemotron-8B", fp_ll, "llama-nemotron-8b"),
         ("GLM-5.1-FP8", fp_glm, "glm-5.1-fp8")),
    ]

    results = {}

    for (name_a, fp_a, key_a), (name_b, fp_b, key_b) in pairs:
        pair_name = f"{name_a} vs {name_b}"
        results[pair_name] = _compute_pair_analysis(key_a, key_b, fp_a, fp_b, adj)

        print(f"\n{pair_name}:")
        print(f"  Raw drift:         {results[pair_name]['raw_drift']:.4f}")
        print(f"  Adjusted drift:    {results[pair_name]['adjusted_drift']:.4f}")
        print(f"  Perception inflation: {results[pair_name]['perception_inflation']:.4f} "
              f"({results[pair_name]['inflation_pct']:.1f}%)")
        print(f"  Gap magnitude:     {results[pair_name]['gap_magnitude']:.3f}")
        print(f"  Biggest gaps:      {results[pair_name]['biggest_gaps']}")

    # Overall analysis
    avg_inflation = sum(r["inflation_pct"] for r in results.values()) / len(results)
    avg_raw_drift = sum(r["raw_drift"] for r in results.values()) / len(results)
    avg_adjusted_drift = sum(r["adjusted_drift"] for r in results.values()) / len(results)

    print("\n" + "=" * 72)
    print("OVERALL: HOW MUCH OF MEASURED DRIFT IS PERCEPTION BIAS?")
    print("-" * 72)
    print(f"  Average raw drift:            {avg_raw_drift:.4f}")
    print(f"  Average adjusted drift:        {avg_adjusted_drift:.4f}")
    print(f"  Average perception inflation:  {avg_inflation:.1f}%")
    print(f"  ~{avg_inflation:.0f}% of measured drift is perception bias")
    print(f"  ~{100 - avg_inflation:.0f}% is genuine semantic divergence")

    return results


if __name__ == "__main__":
    results = run_perception_analysis()
    outpath = Path(__file__).parent / "three_model_perception_gaps.json"
    with open(outpath, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to {outpath}")