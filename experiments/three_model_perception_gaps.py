#!/usr/bin/env python3
"""3-model perception gap analysis using the perception gap adjuster."""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
from perception_gap_adjuster import PerceptionGapAdjuster, cosine_similarity, DIMENSIONS

# Load the 3-model comparison data
with open(Path(__file__).parent / "model_fingerprint_comparison.json") as f:
    comp = json.load(f)

dims = comp['dimensions']
models = comp['models']
model_names = list(models.keys())

adj = PerceptionGapAdjuster()

print('PERCEPTION GAP ANALYSIS: 3-MODEL COMPARISON')
print('=' * 72)

results = {}

for i in range(len(model_names)):
    for j in range(i+1, len(model_names)):
        a, b = model_names[i], model_names[j]
        bias_a = models[a].get('bias', {})
        bias_b = models[b].get('bias', {})
        fp_a = models[a].get('fingerprint', [])
        fp_b = models[b].get('fingerprint', [])
        
        # Compute gap vector
        gap = {d: round(bias_b.get(d, 3.0) - bias_a.get(d, 3.0), 2) for d in dims}
        gap_magnitude = sum(v**2 for v in gap.values()) ** 0.5
        
        # Raw similarity of fingerprints
        raw_sim = cosine_similarity(fp_a, fp_b) if fp_a and fp_b else 1.0
        
        # Adjusted
        a_key = a.lower().replace(' ', '-')
        b_key = b.lower().replace(' ', '-')
        adjusted_result = adj.adjust_drift(fp_a, fp_b, a_key, b_key)
        adjusted_sim = 1.0 - adjusted_result["adjusted_drift"]
        inflation = raw_sim - adjusted_sim
        inflation_pct = adjusted_result["perception_inflation_pct"]
        
        pair_key = f"{a} vs {b}"
        results[pair_key] = {
            "gap_magnitude": round(gap_magnitude, 4),
            "gap_vector": gap,
            "raw_fingerprint_similarity": round(raw_sim, 4),
            "adjusted_similarity": round(adjusted_sim, 4),
            "perception_inflation": round(inflation, 4),
            "inflation_pct": inflation_pct,
            "biggest_gaps": dict(sorted(gap.items(), key=lambda x: -abs(x[1]))[:3])
        }
        
        print(f"\n{a} vs {b}:")
        print(f"  Gap magnitude: {gap_magnitude:.3f}")
        print(f"  Biggest gaps:")
        for d, g in sorted(gap.items(), key=lambda x: -abs(x[1]))[:3]:
            print(f"    {d}: {g:+.2f}")
        print(f"  Raw fingerprint similarity: {raw_sim:.4f}")
        print(f"  Adjusted similarity: {adjusted_sim:.4f}")
        if raw_sim > 0:
            print(f"  Perception inflation: {inflation:.4f} ({inflation_pct:.1f}%)")

# Overall analysis
print("\n" + "=" * 72)
print("OVERALL: HOW MUCH OF MEASURED DRIFT IS PERCEPTION BIAS?")
print("-" * 72)

avg_inflation = sum(r["inflation_pct"] for r in results.values()) / len(results) if results else 0
print(f"  Average perception inflation across model pairs: {avg_inflation:.1f}%")
print(f"  This means ~{avg_inflation:.0f}% of measured drift is actually model perception bias")

# Save
outpath = Path(__file__).parent / "three_model_perception_gaps.json"
with open(outpath, "w") as f:
    json.dump(results, f, indent=2)
print(f"\nSaved to {outpath}")
