#!/usr/bin/env python3
"""
Drift Budget — how many agent hops can you afford before meaning degrades?

Given empirical drift rates per model pair, computes the maximum chain length
that maintains fidelity above a target threshold. Also computes the "drift tax"
— how much fidelity each hop costs on average.

Key concepts:
  - Drift per hop: average (1 - similarity) between consecutive agents
  - Fidelity decay: cumulative fidelity loss across N hops
  - Drift budget: max hops before fidelity drops below threshold
  - Drift tax: fidelity cost per hop (like a transaction fee)

Usage:
  from drift_budget import DriftBudget
  budget = DriftBudget(target_fidelity=0.7)
  plan = budget.plan_chain(models=["DeepSeek-V4-Pro", "Llama-Nemotron-8B", "GLM-5.1-FP8"])
  print(budget.report())
"""
import json, math
from pathlib import Path

# Empirical drift rates from our experiments
# These are per-hop drifts (1 - cosine_similarity) for different model pairings
EMPIRICAL_DRIFT_RATES = {
    # From routing order experiment
    "default_per_hop": 0.15,  # average drift per hop across all our experiments
    # From LLM dimension rating telephone game
    "llm_dimension_per_hop": 0.068,  # average per-step drift
    # From text-mode telephone game  
    "text_mode_per_hop": 0.781,  # much higher (TF-IDF is coarse)
    # From cross-speaker analysis
    "cross_speaker_per_hop": 0.25,  # typical inter-model drift
}

class DriftBudget:
    """Computes drift budgets for multi-agent chains."""
    
    def __init__(self, target_fidelity=0.7, drift_rate=None):
        """
        Args:
            target_fidelity: minimum acceptable fidelity (0-1)
            drift_rate: per-hop drift rate. If None, uses empirical default.
        """
        self.target_fidelity = target_fidelity
        self.drift_rate = drift_rate or EMPIRICAL_DRIFT_RATES["default_per_hop"]
    
    def fidelity_after_n_hops(self, n):
        """Estimate fidelity after N hops using exponential decay.
        
        fidelity(n) = exp(-lambda * n) where lambda = -ln(1 - drift_rate)
        This models drift as a memoryless process (each hop independent).
        """
        if self.drift_rate >= 1.0:
            return 0.0
        # Exponential decay: fidelity = (1 - drift_rate)^n
        return (1.0 - self.drift_rate) ** n
    
    def max_hops(self):
        """Maximum hops before fidelity drops below target."""
        if self.drift_rate >= 1.0:
            return 0
        if self.drift_rate <= 0:
            return float('inf')
        # Solve: (1 - r)^n = target
        # n = ln(target) / ln(1 - r)
        n = math.log(self.target_fidelity) / math.log(1.0 - self.drift_rate)
        return max(0, int(n))
    
    def drift_tax(self):
        """Fidelity cost per hop (drift tax)."""
        return self.drift_rate
    
    def fidelity_at_each_hop(self, max_n=None):
        """Compute fidelity at each hop up to max_n."""
        if max_n is None:
            max_n = self.max_hops() + 5
        return [round(self.fidelity_after_n_hops(n), 4) for n in range(max_n + 1)]
    
    def plan_chain(self, models, drift_rates=None):
        """Plan a chain of models with per-pair drift rates.
        
        Args:
            models: list of model names in chain order
            drift_rates: dict of (model_a, model_b) -> drift_rate.
                        If None, uses default per-hop rate.
        
        Returns:
            dict with planned fidelity at each step and chain assessment
        """
        if drift_rates is None:
            drift_rates = {}
        
        chain = [{"step": 0, "model": models[0] if models else "start", "fidelity": 1.0}]
        current_fidelity = 1.0
        
        for i in range(1, len(models)):
            # Get drift rate for this pair
            pair_key = (models[i-1], models[i])
            rate = drift_rates.get(pair_key, self.drift_rate)
            
            # Apply drift
            current_fidelity *= (1.0 - rate)
            chain.append({
                "step": i,
                "model": models[i],
                "fidelity": round(current_fidelity, 4),
                "drift_rate": rate,
                "drift_tax": round(rate, 4)
            })
        
        final_fidelity = current_fidelity
        within_budget = final_fidelity >= self.target_fidelity
        
        return {
            "models": models,
            "chain": chain,
            "final_fidelity": round(final_fidelity, 4),
            "target_fidelity": self.target_fidelity,
            "within_budget": within_budget,
            "total_drift_tax": round(1.0 - final_fidelity, 4),
            "budget_remaining": round(final_fidelity - self.target_fidelity, 4) if within_budget else 0.0,
            "assessment": "PASS" if within_budget else "FAIL — fidelity below target"
        }
    
    def optimize_chain(self, models, n_positions=None):
        """Find the optimal ordering of models to maximize fidelity.
        
        Brute-force: try all permutations of models and pick the one
        with highest final fidelity.
        """
        from itertools import permutations
        
        best = None
        best_fidelity = 0
        
        for perm in permutations(models):
            result = self.plan_chain(list(perm))
            if result["final_fidelity"] > best_fidelity:
                best_fidelity = result["final_fidelity"]
                best = result
        
        return best
    
    def report(self):
        """Generate a drift budget report."""
        lines = []
        lines.append("DRIFT BUDGET REPORT")
        lines.append("=" * 60)
        lines.append("Target fidelity: %.2f" % self.target_fidelity)
        lines.append("Per-hop drift rate: %.4f" % self.drift_rate)
        lines.append("Drift tax per hop: %.2f%%" % (self.drift_rate * 100))
        lines.append("Max hops before budget exceeded: %d" % self.max_hops())
        lines.append("")
        lines.append("FIDELITY DECAY TABLE:")
        lines.append("-" * 40)
        fidelities = self.fidelity_at_each_hop(max_n=min(20, self.max_hops() + 10))
        for n, f in enumerate(fidelities):
            marker = " <-- BUDGET LINE" if abs(f - self.target_fidelity) < 0.02 else ""
            bar = "█" * int(f * 30)
            lines.append("  Hop %2d: %.4f %s%s" % (n, f, bar, marker))
        lines.append("=" * 60)
        return "\n".join(lines)

def demo():
    """Demo: drift budgets for different scenarios."""
    print("=" * 72)
    print("DRIFT BUDGET ANALYSIS")
    print("=" * 72)
    
    # Scenario 1: Default drift rate
    print("\n1. DEFAULT SCENARIO (drift rate = 0.15/hop)")
    budget1 = DriftBudget(target_fidelity=0.7)
    print(budget1.report())
    
    # Scenario 2: LLM dimension rating (low drift)
    print("\n2. LLM DIMENSION RATING (drift rate = 0.068/hop)")
    budget2 = DriftBudget(target_fidelity=0.7, drift_rate=0.068)
    print("   Max hops: %d" % budget2.max_hops())
    print("   Fidelity at 10 hops: %.4f" % budget2.fidelity_after_n_hops(10))
    
    # Scenario 3: Text-mode (high drift)
    print("\n3. TEXT-MODE TF-IDF (drift rate = 0.781/hop)")
    budget3 = DriftBudget(target_fidelity=0.7, drift_rate=0.781)
    print("   Max hops: %d" % budget3.max_hops())
    
    # Scenario 4: Chain planning with 3 models
    print("\n4. 3-MODEL CHAIN PLANNING")
    models = ["DeepSeek-V4-Pro", "Llama-Nemotron-8B", "GLM-5.1-FP8"]
    budget4 = DriftBudget(target_fidelity=0.7, drift_rate=0.15)
    
    # Default order
    result = budget4.plan_chain(models)
    print("   Order: %s" % " → ".join(models))
    print("   Final fidelity: %.4f (%s)" % (result["final_fidelity"], result["assessment"]))
    
    # Find optimal order
    print("\n5. OPTIMAL CHAIN ORDER (brute-force)")
    optimal = budget4.optimize_chain(models)
    print("   Best: %s" % " → ".join(optimal["models"]))
    print("   Final fidelity: %.4f" % optimal["final_fidelity"])
    
    # Save results
    results = {
        "default_budget": {"max_hops": budget1.max_hops(), "drift_rate": budget1.drift_rate},
        "llm_budget": {"max_hops": budget2.max_hops(), "drift_rate": budget2.drift_rate},
        "chain_plan": result,
        "optimal_chain": optimal
    }
    outpath = Path(__file__).parent.parent / "experiments" / "drift_budget_results.json"
    with open(outpath, "w") as f:
        json.dump(results, f, indent=2)
    print("\nSaved to", outpath)

if __name__ == "__main__":
    demo()
