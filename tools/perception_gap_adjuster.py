#!/usr/bin/env python3
"""
Perception Gap Adjuster — compensates for model-specific semantic biases.

When different LLMs rate the same text on semantic dimensions, they produce
different ratings (the "perception gap"). This tool measures that gap and
adjusts drift calculations to account for it.

Key insight: drift has two components:
  1. Genuine semantic transformation (conceptual drift)
  2. Perceptual differences between models (perception gap)

Without adjustment, the perception gap inflates measured drift. This tool
separates the two, producing a "perception-adjusted drift" score.

Usage:
  from perception_gap_adjuster import PerceptionGapAdjuster
  adjuster = PerceptionGapAdjuster()
  adjusted = adjuster.adjust_drift(ratings_a, ratings_b, model_a="llama", model_b="glm")
"""
import json, math, os
from pathlib import Path

# Default biases — overridden by loading experiments/fingerprint_comparison.json at runtime
_DEFAULT_BIASES = {
    ("llama-nemotron-8b", "glm-5.1-fp8"): {
        "concreteness": -1.4, "technicality": -0.2, "formality": -0.2,
        "specificity": -0.5, "agency": -0.5, "temporality": -1.2,
        "certainty": 0.8, "complexity": -0.5, "emotional": 0.0, "scope": -0.9
    }
}

def _load_empirical_biases():
    """Load perception gaps from fingerprint_comparison.json if available."""
    experiments_dir = Path(__file__).parent.parent / "experiments"
    
    # Try 3-model comparison first
    comp_path = experiments_dir / "model_fingerprint_comparison.json"
    if comp_path.exists():
        try:
            with open(comp_path) as f:
                comp = json.load(f)
            models = comp.get("models", {})
            biases = {}
            model_names = list(models.keys())
            for i in range(len(model_names)):
                for j in range(i + 1, len(model_names)):
                    name_a, name_b = model_names[i], model_names[j]
                    bias_a = models[name_a].get("bias", {})
                    bias_b = models[name_b].get("bias", {})
                    gap = {d: round(bias_b.get(d, 3.0) - bias_a.get(d, 3.0), 2) for d in DIMENSIONS}
                    biases[(name_a.lower().replace(" ", "-"), name_b.lower().replace(" ", "-"))] = gap
            if biases:
                return biases
        except Exception:
            pass
    
    # Fall back to pairwise comparison
    comp_path2 = experiments_dir / "fingerprint_comparison.json"
    if comp_path2.exists():
        try:
            with open(comp_path2) as f:
                comp = json.load(f)
            gaps = comp.get("perception_gaps", {})
            return {("llama-nemotron-8b", "glm-5.1-fp8"): {k: v for k, v in gaps.items()}}
        except Exception:
            pass
    
    return _DEFAULT_BIASES

DIMENSIONS = [
    "concreteness", "technicality", "formality", "specificity", "agency",
    "temporality", "certainty", "complexity", "emotional", "scope"
]

def cosine_similarity(a, b):
    """Cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)

def normalize_ratings(ratings):
    """Normalize 1-5 ratings to 0-1."""
    return [(r - 1) / 4.0 for r in ratings]

class PerceptionGapAdjuster:
    """Adjusts drift measurements for model-specific perception biases."""
    
    def __init__(self, bias_data=None):
        """
        Args:
            bias_data: dict of (model_a, model_b) -> {dim: bias} mappings.
                       If None, uses built-in biases from our experiments.
        """
        self.biases = bias_data or _load_empirical_biases()
    
    def measure_perception_gap(self, ratings_by_model):
        """Measure the perception gap between models using paired ratings.
        
        Args:
            ratings_by_model: dict of model_name -> list of ratings on same text
                              e.g. {"llama": [3,5,5,5,3,5,5,5,1,3], "glm": [1,5,5,5,4,3,5,5,1,3]}
        
        Returns:
            dict with raw_gap, gap_vector, and adjusted_ratings
        """
        models = list(ratings_by_model.keys())
        if len(models) < 2:
            return {"error": "Need at least 2 models"}
        
        model_a, model_b = models[0], models[1]
        ratings_a = ratings_by_model[model_a]
        ratings_b = ratings_by_model[model_b]
        
        # Raw gap vector
        gap_vector = [ratings_b[i] - ratings_a[i] for i in range(len(ratings_a))]
        
        # Raw similarity (unadjusted)
        norm_a = normalize_ratings(ratings_a)
        norm_b = normalize_ratings(ratings_b)
        raw_sim = cosine_similarity(norm_a, norm_b)
        
        # Adjusted ratings: subtract the expected bias from model_b's ratings
        bias_key = (model_a, model_b)
        if bias_key in self.biases:
            bias = self.biases[bias_key]
            adjusted_b = []
            for i, dim in enumerate(DIMENSIONS[:len(ratings_b)]):
                if dim in bias:
                    adjusted_b.append(ratings_b[i] - bias[dim])
                else:
                    adjusted_b.append(ratings_b[i])
        else:
            # No known bias — use the empirical gap as bias estimate
            adjusted_b = ratings_b[:]
        
        # Adjusted similarity
        norm_adj_b = normalize_ratings(adjusted_b)
        adjusted_sim = cosine_similarity(norm_a, norm_adj_b)
        
        # Perception gap = how much of the raw dissimilarity is due to perception
        perception_component = max(0, adjusted_sim - raw_sim)
        
        return {
            "model_a": model_a,
            "model_b": model_b,
            "raw_similarity": round(raw_sim, 4),
            "adjusted_similarity": round(adjusted_sim, 4),
            "perception_component": round(perception_component, 4),
            "gap_vector": {DIMENSIONS[i]: gap_vector[i] for i in range(len(gap_vector))},
            "ratings_a": ratings_a,
            "ratings_b": ratings_b,
            "adjusted_b": [round(x, 2) for x in adjusted_b]
        }
    
    def adjust_drift(self, ratings_a, ratings_b, model_a="unknown", model_b="unknown"):
        """Adjust drift between two rating vectors for perception bias.
        
        Returns the perception-adjusted drift (1 - adjusted_similarity).
        """
        result = self.measure_perception_gap({
            model_a: ratings_a,
            model_b: ratings_b
        })
        
        raw_drift = 1.0 - result["raw_similarity"]
        adjusted_drift = 1.0 - result["adjusted_similarity"]
        
        return {
            "raw_drift": round(raw_drift, 4),
            "adjusted_drift": round(adjusted_drift, 4),
            "perception_inflation": round(raw_drift - adjusted_drift, 4),
            "perception_inflation_pct": round((raw_drift - adjusted_drift) / max(raw_drift, 0.001) * 100, 1),
            "details": result
        }
    
    def adjust_drift_dimensionwise(self, ratings_a, ratings_b, model_a="unknown", model_b="unknown"):
        """Dimension-wise drift correction — identifies which dimensions have
        genuine drift vs. perception bias.
        
        Key insight: the aggregate correction can over-correct when models
        have similar average profiles but different sensitivities per dimension.
        This method corrects each dimension independently and classifies it as:
          - "genuine": real semantic change (gap exceeds known perception bias)
          - "perception": explainable by model bias alone
          - "ambiguous": gap roughly equals known perception bias
          - "blind_spot": both models rate near-identically (can't distinguish)
        
        Returns:
            dict with per-dimension analysis and composite scores
        """
        # Get the known bias for this pair
        bias_key = (model_a, model_b)
        known_bias = self.biases.get(bias_key, {})
        # Also check reversed pair
        if not known_bias:
            bias_key_rev = (model_b, model_a)
            known_bias_rev = self.biases.get(bias_key_rev, {})
            # Reverse the sign
            known_bias = {k: -v for k, v in known_bias_rev.items()}
        
        n_dims = min(len(ratings_a), len(ratings_b), len(DIMENSIONS))
        
        dimension_analysis = []
        for i in range(n_dims):
            dim = DIMENSIONS[i]
            raw_gap = ratings_b[i] - ratings_a[i]
            expected_bias = known_bias.get(dim, 0.0)
            residual = raw_gap - expected_bias
            
            # Classify this dimension
            if abs(ratings_a[i] - ratings_b[i]) < 0.3:
                classification = "blind_spot"
            elif abs(residual) < 0.3 and abs(expected_bias) > 0.3:
                classification = "perception"
            elif abs(residual) > abs(expected_bias):
                classification = "genuine"
            else:
                classification = "ambiguous"
            
            dimension_analysis.append({
                "dimension": dim,
                "rating_a": ratings_a[i],
                "rating_b": ratings_b[i],
                "raw_gap": round(raw_gap, 2),
                "expected_bias": round(expected_bias, 2),
                "residual": round(residual, 2),
                "classification": classification
            })
        
        # Compute dimension-wise fidelity
        genuine_drift_dims = [d for d in dimension_analysis if d["classification"] == "genuine"]
        perception_drift_dims = [d for d in dimension_analysis if d["classification"] == "perception"]
        blind_dims = [d for d in dimension_analysis if d["classification"] == "blind_spot"]
        
        # Genuine drift magnitude (RMS of residuals on genuine dimensions)
        if genuine_drift_dims:
            genuine_rms = math.sqrt(sum(d["residual"]**2 for d in genuine_drift_dims) / len(genuine_drift_dims))
        else:
            genuine_rms = 0.0
        
        # Perception drift magnitude
        if perception_drift_dims:
            perception_rms = math.sqrt(sum(d["raw_gap"]**2 for d in perception_drift_dims) / len(perception_drift_dims))
        else:
            perception_rms = 0.0
        
        # Composite scores
        total_dims = max(1, len(dimension_analysis))
        genuine_fraction = len(genuine_drift_dims) / total_dims
        perception_fraction = len(perception_drift_dims) / total_dims
        blind_fraction = len(blind_dims) / total_dims
        
        # Dimension-adjusted fidelity: 1 - (genuine_rms / scale)
        # Scale: max possible drift per dimension is ~4 (5-1 on 1-5 scale)
        dim_adjusted_fidelity = max(0.0, 1.0 - genuine_rms / 4.0)
        
        return {
            "dimensions": dimension_analysis,
            "summary": {
                "total_dimensions": total_dims,
                "genuine_drift_count": len(genuine_drift_dims),
                "perception_drift_count": len(perception_drift_dims),
                "blind_spot_count": len(blind_dims),
                "ambiguous_count": total_dims - len(genuine_drift_dims) - len(perception_drift_dims) - len(blind_dims),
                "genuine_fraction": round(genuine_fraction, 3),
                "perception_fraction": round(perception_fraction, 3),
                "blind_fraction": round(blind_fraction, 3),
                "genuine_drift_rms": round(genuine_rms, 4),
                "perception_drift_rms": round(perception_rms, 4),
                "dim_adjusted_fidelity": round(dim_adjusted_fidelity, 4)
            },
            "model_a": model_a,
            "model_b": model_b
        }
    
    def complementary_coverage(self, models_list=None):
        """Analyze which models have complementary blind spots.
        
        Two models have complementary coverage when one's blind spot
        is the other's hypersensitivity. A chain with complementary models
        can detect drift on more dimensions than either model alone.
        
        Args:
            models_list: list of model names to analyze. If None, uses all
                         models in the loaded bias data.
        
        Returns:
            dict with coverage analysis per dimension and overall complementarity score
        """
        if models_list is None:
            # Extract all unique model names from bias keys
            models_list = sorted(set(m for pair in self.biases.keys() for m in pair))
        
        if len(models_list) < 2:
            return {"error": "Need at least 2 models for complementarity analysis"}
        
        # Load fingerprint data for sensitivity analysis
        fp_path = Path(__file__).parent.parent / "experiments" / "model_fingerprint_comparison.json"
        sensitivities = {}
        if fp_path.exists():
            try:
                with open(fp_path) as f:
                    comp = json.load(f)
                for name, mdata in comp.get("models", {}).items():
                    key = name.lower().replace(" ", "-")
                    sens = mdata.get("sensitivity", {})
                    if sens:
                        sensitivities[key] = sens
            except Exception:
                pass
        
        # If no fingerprint data, infer from biases
        if not sensitivities:
            for model in models_list:
                sensitivities[model] = {}
                for dim in DIMENSIONS:
                    # Models with larger biases on a dimension are more sensitive to it
                    max_bias = 0
                    for key, bias in self.biases.items():
                        if model in key:
                            max_bias = max(max_bias, abs(bias.get(dim, 0)))
                    sensitivities[model][dim] = min(5.0, max_bias + 1.0) if max_bias > 0 else 2.0  # rough estimate; no bias data = low sensitivity
        
        # Compute per-dimension coverage
        dim_coverage = []
        for dim in DIMENSIONS:
            model_sensitivities = {}
            for model in models_list:
                if model in sensitivities and dim in sensitivities[model]:
                    model_sensitivities[model] = sensitivities[model][dim]
                else:
                    model_sensitivities[model] = 3.0  # default
            
            # Best single model sensitivity
            best_single = max(model_sensitivities.values())
            # Ensemble sensitivity: max of any model (best sensor wins)
            ensemble_sensitivity = best_single
            # Complementarity: how much does adding other models improve coverage?
            # Measure as: (ensemble - average_single) / average_single
            avg_single = sum(model_sensitivities.values()) / len(model_sensitivities)
            complementarity = (ensemble_sensitivity - avg_single) / max(avg_single, 0.01)
            
            # Identify blind spots (all models rate < 2)
            is_blind_spot = all(s < 2.0 for s in model_sensitivities.values())
            
            dim_coverage.append({
                "dimension": dim,
                "model_sensitivities": {k: round(v, 2) for k, v in model_sensitivities.items()},
                "best_single_sensitivity": round(best_single, 2),
                "ensemble_sensitivity": round(ensemble_sensitivity, 2),
                "complementarity": round(complementarity, 3),
                "is_shared_blind_spot": is_blind_spot
            })
        
        # Overall complementarity score
        avg_complementarity = sum(d["complementarity"] for d in dim_coverage) / len(dim_coverage)
        shared_blind_spots = [d["dimension"] for d in dim_coverage if d["is_shared_blind_spot"]]
        covered_dims = [d["dimension"] for d in dim_coverage if not d["is_shared_blind_spot"]]
        
        return {
            "dimensions": dim_coverage,
            "overall": {
                "complementarity_score": round(avg_complementarity, 3),
                "shared_blind_spots": shared_blind_spots,
                "covered_dimensions": covered_dims,
                "coverage_fraction": round(len(covered_dims) / len(DIMENSIONS), 3),
                "models_analyzed": models_list
            }
        }
    
    def calibrate(self, paired_ratings):
        """Calibrate perception biases from paired ratings of same texts.
        
        Args:
            paired_ratings: list of {model_a: ratings, model_b: ratings} dicts
                            where both models rated the same text
        
        Returns:
            Calibrated bias dict to use in __init__
        """
        if not paired_ratings:
            return {}
        
        models = set()
        for pair in paired_ratings:
            models.update(pair.keys())
        models = sorted(models)
        
        biases = {}
        for i, model_a in enumerate(models):
            for model_b in models[i+1:]:
                gaps = {dim: [] for dim in DIMENSIONS}
                for pair in paired_ratings:
                    if model_a in pair and model_b in pair:
                        for j, dim in enumerate(DIMENSIONS):
                            if j < len(pair[model_a]) and j < len(pair[model_b]):
                                gaps[dim].append(pair[model_b][j] - pair[model_a][j])
                
                bias = {}
                for dim in DIMENSIONS:
                    if gaps[dim]:
                        bias[dim] = round(sum(gaps[dim]) / len(gaps[dim]), 2)
                biases[(model_a, model_b)] = bias
        
        return biases

def demo():
    """Demonstrate perception gap adjustment."""
    print("PERCEPTION GAP ADJUSTER — DEMO")
    print("=" * 72)
    
    # Example: same quantum physics text rated by two different models
    llama_ratings = [3, 5, 5, 5, 3, 5, 5, 5, 1, 3]
    glm_ratings = [1, 5, 5, 5, 4, 3, 5, 5, 1, 3]
    
    adjuster = PerceptionGapAdjuster()
    
    print("\n1. Raw ratings comparison:")
    print("   Llama: %s" % llama_ratings)
    print("   GLM:   %s" % glm_ratings)
    
    # Measure gap
    gap_result = adjuster.measure_perception_gap({
        "llama-nemotron-8b": llama_ratings,
        "glm-5.1-fp8": glm_ratings
    })
    
    print("\n2. Perception gap analysis:")
    print("   Raw similarity: %.4f" % gap_result["raw_similarity"])
    print("   Gap vector: %s" % gap_result["gap_vector"])
    
    # Adjust drift
    drift_result = adjuster.adjust_drift(llama_ratings, glm_ratings, 
                                          "llama-nemotron-8b", "glm-5.1-fp8")
    
    print("\n3. Drift adjustment:")
    print("   Raw drift: %.4f" % drift_result["raw_drift"])
    print("   Adjusted drift: %.4f" % drift_result["adjusted_drift"])
    print("   Perception inflation: %.4f (%.1f%%)" % (
        drift_result["perception_inflation"],
        drift_result["perception_inflation_pct"]
    ))
    
    # Calibrate from paired data
    print("\n4. Calibration from paired ratings:")
    paired_data = [
        {"llama": [3, 5, 5, 5, 3, 5, 5, 5, 1, 3], "glm": [1, 5, 5, 5, 4, 3, 5, 5, 1, 3]},
        {"llama": [3, 2, 2, 2, 2, 5, 2, 2, 1, 2], "glm": [1, 1, 1, 1, 2, 4, 1, 1, 2, 2]},
        {"llama": [4, 5, 5, 5, 5, 5, 5, 3, 1, 5], "glm": [2, 5, 5, 5, 4, 4, 5, 3, 1, 5]},
    ]
    calibrated = adjuster.calibrate(paired_data)
    for key, bias in calibrated.items():
        print("   %s → %s:" % key)
        for dim, val in bias.items():
            if val != 0:
                print("     %s: %+.2f" % (dim, val))
    
    print("\n" + "=" * 72)

if __name__ == "__main__":
    demo()
