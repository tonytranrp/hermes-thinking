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

# Known perception biases (from our experiments)
# These are average rating differences between models on the same text.
# Positive = second model rates higher than first.
PERCEPTION_BIASES = {
    ("llama-nemotron-8b", "glm-5.1-fp8"): {
        "concreteness": -1.5,  # GLM rates lower on concreteness
        "technicality": -0.5,
        "formality": -0.5,
        "specificity": -0.5,
        "agency": 0.5,
        "temporality": -1.0,
        "certainty": -0.5,
        "complexity": 0.0,
        "emotional": 0.5,
        "scope": 0.0
    }
}

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
        self.biases = bias_data or PERCEPTION_BIASES
    
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
