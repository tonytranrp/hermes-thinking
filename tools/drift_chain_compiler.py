#!/usr/bin/env python3
"""
Drift-Aware Chain Compiler — automatically assembles optimal multi-agent chains
given a task profile and available models, respecting drift budgets.

Given:
  - Available models with known fingerprints (drift rates, blind spots, sensitivities)
  - Task profile (which semantic dimensions matter)
  - Drift budget (minimum acceptable fidelity)

Outputs:
  - Optimal chain ordering
  - Expected fidelity at each hop
  - Dimension coverage analysis
  - Recommendations for missing coverage

Usage:
  from drift_chain_compiler import DriftChainCompiler
  compiler = DriftChainCompiler()
  plan = compiler.compile(task_profile={"technicality": 5, "formality": 4},
                           models=["DeepSeek-V4-Pro", "Llama-Nemotron-8B"],
                           target_fidelity=0.7)
"""
import json, math
from pathlib import Path
from itertools import permutations

# Add tools to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from drift_budget import DriftBudget, EMPIRICAL_DRIFT_RATES
from perception_gap_adjuster import PerceptionGapAdjuster, DIMENSIONS

class DriftChainCompiler:
    """Compiles optimal multi-agent chains with drift awareness."""
    
    def __init__(self):
        self.adjuster = PerceptionGapAdjuster()
        self._load_fingerprints()
    
    def _load_fingerprints(self):
        """Load model fingerprint data."""
        fp_path = Path(__file__).parent.parent / "experiments" / "model_fingerprint_comparison.json"
        self.fingerprints = {}
        if fp_path.exists():
            with open(fp_path) as f:
                comp = json.load(f)
            for name, mdata in comp.get("models", {}).items():
                key = name.lower().replace(" ", "-")
                self.fingerprints[key] = mdata
    
    def _get_model_drift_rate(self, model):
        """Estimate per-hop drift rate for a model."""
        if model in self.fingerprints:
            fp = self.fingerprints[model]
            # Models with wider discriminative range have lower effective drift
            # (they perceive more precisely, so drift is more accurate)
            disc_range = fp.get("discriminative_range", 0.15)
            if isinstance(disc_range, (int, float)) and disc_range > 0:
                # Inverse relationship: more discriminative = less drift per hop
                return max(0.03, 0.15 / (1 + disc_range * 2))
        return EMPIRICAL_DRIFT_RATES["default_per_hop"]
    
    def _compute_pair_drift_rate(self, model_a, model_b):
        """Compute drift rate for a specific model pair."""
        rate_a = self._get_model_drift_rate(model_a)
        rate_b = self._get_model_drift_rate(model_b)
        # Average of both models' rates
        return (rate_a + rate_b) / 2.0
    
    def compile(self, task_profile=None, models=None, target_fidelity=0.7,
                chain_length=None, strategy="balanced"):
        """Compile an optimal chain plan.
        
        Args:
            task_profile: dict of dimension -> importance (1-5). If None,
                         treats all dimensions equally.
            models: list of available model names. If None, uses all known models.
            target_fidelity: minimum acceptable fidelity (0-1).
            chain_length: desired chain length. If None, uses max that stays
                         within budget.
            strategy: "faithful" (minimize drift), "creative" (maximize diversity),
                     "balanced" (optimize coverage within budget).
        
        Returns:
            dict with chain plan, fidelity projections, coverage analysis
        """
        if models is None:
            models = list(self.fingerprints.keys())
        
        if not models:
            return {"error": "No models available"}
        
        # Step 1: Compute per-pair drift rates
        pair_rates = {}
        for i in range(len(models)):
            for j in range(len(models)):
                if i != j:
                    pair_rates[(models[i], models[j])] = self._compute_pair_drift_rate(models[i], models[j])
        
        # Step 2: Find optimal chain ordering
        if chain_length is None:
            chain_length = min(len(models), 5)  # cap at 5
        
        best_chain = None
        best_score = -float('inf')
        
        # Try all permutations of models up to chain_length
        for perm in permutations(models, min(chain_length, len(models))):
            # Compute fidelity at each hop
            fidelity = 1.0
            for k in range(len(perm) - 1):
                pair = (perm[k], perm[k+1])
                rate = pair_rates.get(pair, 0.15)
                fidelity *= (1.0 - rate)
            
            # Score based on strategy
            if strategy == "faithful":
                # Maximize final fidelity
                score = fidelity
            elif strategy == "creative":
                # Maximize total drift while staying in budget
                score = (1.0 - fidelity) if fidelity >= target_fidelity else -1.0
            else:  # balanced
                # Optimize: high fidelity with good coverage
                coverage_result = self._compute_coverage(list(perm), task_profile)
                coverage = coverage_result.get("coverage_score", 0)
                score = fidelity * 0.6 + coverage * 0.4
            
            if score > best_score:
                best_score = score
                best_chain = list(perm)
        
        if best_chain is None:
            return {"error": "Could not find any valid chain"}
        
        # Step 3: Build detailed chain plan
        chain_plan = []
        current_fidelity = 1.0
        for k, model in enumerate(best_chain):
            if k == 0:
                chain_plan.append({
                    "step": k,
                    "model": model,
                    "fidelity": 1.0,
                    "drift_rate": 0.0,
                    "drift_tax": 0.0
                })
            else:
                pair = (best_chain[k-1], model)
                rate = pair_rates.get(pair, 0.15)
                current_fidelity *= (1.0 - rate)
                chain_plan.append({
                    "step": k,
                    "model": model,
                    "fidelity": round(current_fidelity, 4),
                    "drift_rate": round(rate, 4),
                    "drift_tax": round(rate, 4)
                })
        
        # Step 4: Coverage analysis
        coverage = self._compute_coverage(best_chain, task_profile)
        
        # Step 5: Recommendations
        recommendations = self._generate_recommendations(
            best_chain, coverage, task_profile, current_fidelity, target_fidelity)
        
        return {
            "chain": best_chain,
            "chain_plan": chain_plan,
            "final_fidelity": round(current_fidelity, 4),
            "target_fidelity": target_fidelity,
            "within_budget": current_fidelity >= target_fidelity,
            "strategy": strategy,
            "total_drift_tax": round(1.0 - current_fidelity, 4),
            "budget_remaining": round(current_fidelity - target_fidelity, 4),
            "coverage": coverage,
            "recommendations": recommendations,
            "pair_drift_rates": {f"{k[0]}→{k[1]}": round(v, 4) for k, v in pair_rates.items() if k[0] in best_chain and k[1] in best_chain}
        }
    
    def _compute_coverage(self, chain, task_profile=None):
        """Compute semantic dimension coverage for a chain of models."""
        if task_profile is None:
            task_profile = {d: 3 for d in DIMENSIONS}
        
        # Get complementarity analysis
        comp_result = self.adjuster.complementary_coverage(chain)
        
        coverage_by_dim = {}
        if "dimensions" in comp_result:
            for d in comp_result["dimensions"]:
                dim = d["dimension"]
                importance = task_profile.get(dim, 3) / 5.0
                best_sens = d.get("best_single_sensitivity", 3.0)
                coverage_by_dim[dim] = {
                    "sensitivity": best_sens,
                    "importance": importance,
                    "weighted_coverage": round(best_sens * importance, 3),
                    "is_blind_spot": d.get("is_shared_blind_spot", False)
                }
        
        # Overall coverage score
        if coverage_by_dim:
            total_weighted = sum(v["weighted_coverage"] for v in coverage_by_dim.values())
            max_possible = sum(5.0 * (task_profile.get(d, 3) / 5.0) for d in DIMENSIONS)
            coverage_score = total_weighted / max_possible if max_possible > 0 else 0
        else:
            coverage_score = 0
        
        return {
            "dimensions": coverage_by_dim,
            "coverage_score": round(coverage_score, 3),
            "blind_spots": [d for d, v in coverage_by_dim.items() if v.get("is_blind_spot", False)]
        }
    
    def _generate_recommendations(self, chain, coverage, task_profile, 
                                   final_fidelity, target_fidelity):
        """Generate actionable recommendations for improving the chain."""
        recs = []
        
        if final_fidelity < target_fidelity:
            recs.append(f"⚠️ Final fidelity ({final_fidelity:.2f}) below target ({target_fidelity:.2f}). "
                       f"Consider reducing chain length or using lower-drift models.")
        
        blind_spots = coverage.get("blind_spots", [])
        if blind_spots:
            important_blind = [d for d in blind_spots if task_profile and task_profile.get(d, 3) >= 4]
            if important_blind:
                recs.append(f"🔴 Critical blind spots on important dimensions: {important_blind}. "
                           f"No model in chain can detect drift here. Consider adding a model "
                           f"sensitive to these dimensions.")
            else:
                recs.append(f"🟡 Blind spots on low-importance dimensions: {blind_spots}. "
                           f"Drift on these dimensions is undetectable but not task-critical.")
        
        coverage_score = coverage.get("coverage_score", 0)
        if coverage_score < 0.5:
            recs.append(f"🟡 Low dimension coverage ({coverage_score:.2f}). "
                       f"Chain may miss drift on uncovered dimensions.")
        
        # Check if adding another model would help
        available = set(self.fingerprints.keys()) - set(chain)
        if available:
            for model in available:
                # Check if this model covers blind spots
                fp = self.fingerprints.get(model, {})
                sens = fp.get("sensitivity", {})
                covers_new_dims = [d for d in blind_spots if d in sens and sens[d] > 3.0]
                if covers_new_dims:
                    recs.append(f"💡 Adding {model} would cover blind spots: {covers_new_dims}")
        
        if not recs:
            recs.append("✅ Chain is well-optimized: within budget, good coverage, no critical blind spots.")
        
        return recs

def demo():
    """Demo: compile chains for different task profiles."""
    print("DRIFT-AWARE CHAIN COMPILER")
    print("=" * 72)
    
    compiler = DriftChainCompiler()
    
    # Scenario 1: Technical task
    print("\n1. TECHNICAL TASK (high technicality, formality)")
    result = compiler.compile(
        task_profile={"technicality": 5, "formality": 5, "specificity": 4, "complexity": 4},
        models=["deepseek-v4-pro", "llama-nemotron-8b", "glm-5.1-fp8"],
        target_fidelity=0.7,
        strategy="faithful"
    )
    print_chain(result)
    
    # Scenario 2: Creative task
    print("\n2. CREATIVE TASK (high emotional, low formality)")
    result = compiler.compile(
        task_profile={"emotional": 5, "formality": 1, "concreteness": 3, "agency": 4},
        models=["deepseek-v4-pro", "llama-nemotron-8b", "glm-5.1-fp8"],
        target_fidelity=0.7,
        strategy="creative"
    )
    print_chain(result)
    
    # Scenario 3: Balanced
    print("\n3. BALANCED ANALYSIS")
    result = compiler.compile(
        models=["deepseek-v4-pro", "llama-nemotron-8b", "glm-5.1-fp8"],
        target_fidelity=0.7,
        strategy="balanced"
    )
    print_chain(result)
    
    # Save results
    outpath = Path(__file__).parent.parent / "experiments" / "chain_compiler_results.json"
    with open(outpath, "w") as f:
        # Re-run to get fresh results for saving
        results = {
            "faithful": compiler.compile(
                task_profile={"technicality": 5, "formality": 5},
                strategy="faithful"),
            "creative": compiler.compile(
                task_profile={"emotional": 5, "formality": 1},
                strategy="creative"),
            "balanced": compiler.compile(strategy="balanced")
        }
        json.dump(results, f, indent=2, default=str)
    print(f"\nSaved to {outpath}")

def print_chain(result):
    """Print a chain compilation result."""
    if "error" in result:
        print(f"   ERROR: {result['error']}")
        return
    
    print(f"   Chain: {' → '.join(result['chain'])}")
    print(f"   Final fidelity: {result['final_fidelity']:.4f} (target: {result['target_fidelity']})")
    print(f"   Within budget: {'✓' if result['within_budget'] else '✗'}")
    print(f"   Total drift tax: {result['total_drift_tax']:.2%}")
    print(f"   Coverage score: {result['coverage']['coverage_score']:.3f}")
    for rec in result['recommendations']:
        print(f"   {rec}")

if __name__ == "__main__":
    demo()
