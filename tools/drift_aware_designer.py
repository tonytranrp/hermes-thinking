#!/usr/bin/env python3
"""
Drift-Aware Conversation Designer — recommends optimal conversation structures
based on model semantic fingerprints.

Given the perception profiles of the models in a multi-agent system, this tool:
1. Identifies shared blind spots (drift on these dims is invisible to all models)
2. Recommends model ordering based on desired drift outcome
3. Estimates per-dimension drift exposure
4. Suggests which dimensions to monitor based on model sensitivity

Usage:
  from drift_aware_designer import DriftAwareDesigner
  designer = DriftAwareDesigner(fingerprint_a, fingerprint_b)
  plan = designer.design_for_creativity()
  plan = designer.design_for_fidelity()
"""
import json, math
from pathlib import Path

DIMS = ["concreteness", "technicality", "formality", "specificity", "agency",
        "temporality", "certainty", "complexity", "emotional", "scope"]

def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)

class DriftAwareDesigner:
    """Designs conversation structures based on model semantic fingerprints."""
    
    def __init__(self, fingerprint_a, fingerprint_b=None):
        """
        Args:
            fingerprint_a: dict with 'bias', 'discriminability', etc.
            fingerprint_b: optional second model fingerprint
        """
        self.fp_a = fingerprint_a
        self.fp_b = fingerprint_b
    
    def analyze_perception_landscape(self):
        """Analyze the combined perception landscape of the models."""
        result = {
            "model_a": self.fp_a.get("model", "unknown"),
            "shared_blind_spots": [],
            "unique_blind_spots_a": [],
            "perception_gaps": {},
            "complementary_dims": [],
            "conflicting_dims": []
        }
        
        # Blind spots: dims where discriminability < 0.3
        blind_a = {d for d in DIMS if self.fp_a.get("discriminability", {}).get(d, 1.0) < 0.3}
        result["unique_blind_spots_a"] = list(blind_a)
        
        if self.fp_b:
            result["model_b"] = self.fp_b.get("model", "unknown")
            blind_b = {d for d in DIMS if self.fp_b.get("discriminability", {}).get(d, 1.0) < 0.3}
            result["unique_blind_spots_b"] = list(blind_b)
            result["shared_blind_spots"] = list(blind_a & blind_b)
            
            # Perception gaps
            for d in DIMS:
                gap = abs(self.fp_b.get("bias", {}).get(d, 3.0) - self.fp_a.get("bias", {}).get(d, 3.0))
                result["perception_gaps"][d] = round(gap, 2)
            
            # Complementary: one model's blind spot is the other's strength
            for d in DIMS:
                disc_a = self.fp_a.get("discriminability", {}).get(d, 1.0)
                disc_b = self.fp_b.get("discriminability", {}).get(d, 1.0)
                if (disc_a < 0.3 and disc_b > 0.5) or (disc_b < 0.3 and disc_a > 0.5):
                    result["complementary_dims"].append(d)
            
            # Conflicting: both sensitive but with different biases
            for d in DIMS:
                disc_a = self.fp_a.get("discriminability", {}).get(d, 1.0)
                disc_b = self.fp_b.get("discriminability", {}).get(d, 1.0)
                gap = result["perception_gaps"].get(d, 0)
                if disc_a > 0.5 and disc_b > 0.5 and gap > 0.7:
                    result["conflicting_dims"].append(d)
        
        return result
    
    def design_for_creativity(self):
        """Design a conversation structure that maximizes creative drift.
        
        Creative drift = drift that generates novel meaning while remaining coherent.
        Strategy: route through models with conflicting perceptions on key dimensions.
        """
        landscape = self.analyze_perception_landscape()
        
        plan = {
            "goal": "maximize_creative_drift",
            "routing_recommendation": [],
            "monitor_dimensions": [],
            "ignore_dimensions": [],
            "risk_dimensions": [],
            "explanation": []
        }
        
        if self.fp_b:
            # For creativity: route through the model with HIGHER bias on
            # conflicting dimensions first (it will push meaning in a direction),
            # then through the other (it will push back differently).
            # This creates oscillation = creative tension.
            
            for d in landscape["conflicting_dims"]:
                bias_a = self.fp_a.get("bias", {}).get(d, 3.0)
                bias_b = self.fp_b.get("bias", {}).get(d, 3.0)
                if bias_a > bias_b:
                    plan["routing_recommendation"].append({
                        "dimension": d,
                        "first": self.fp_a.get("model", "A"),
                        "then": self.fp_b.get("model", "B"),
                        "reason": "%s rates %s higher (%.1f vs %.1f) — starts the push" % (
                            self.fp_a.get("model", "A"), d, bias_a, bias_b)
                    })
                else:
                    plan["routing_recommendation"].append({
                        "dimension": d,
                        "first": self.fp_b.get("model", "B"),
                        "then": self.fp_a.get("model", "A"),
                        "reason": "%s rates %s higher (%.1f vs %.1f) — starts the push" % (
                            self.fp_b.get("model", "B"), d, bias_b, bias_a)
                    })
            
            # Monitor: conflicting dimensions (where drift generates novelty)
            plan["monitor_dimensions"] = landscape["conflicting_dims"]
            
            # Ignore: shared blind spots (can't detect drift here anyway)
            plan["ignore_dimensions"] = landscape["shared_blind_spots"]
            
            # Risk: dimensions where both models have high bias but low discriminability
            # (they'll both push in the same wrong direction)
            for d in DIMS:
                disc_a = self.fp_a.get("discriminability", {}).get(d, 1.0)
                disc_b = self.fp_b.get("discriminability", {}).get(d, 1.0)
                bias_a = self.fp_a.get("bias", {}).get(d, 3.0)
                bias_b = self.fp_b.get("bias", {}).get(d, 3.0)
                if disc_a < 0.5 and disc_b < 0.5 and abs(bias_a - 3.0) > 0.5 and abs(bias_b - 3.0) > 0.5:
                    plan["risk_dimensions"].append(d)
            
            plan["explanation"] = [
                "Creative drift is maximized when models have conflicting perceptions on key dimensions.",
                "Route through the higher-bias model first to establish a strong direction,",
                "then through the lower-bias model to create tension and generate novelty.",
                "Monitor conflicting dimensions for productive drift.",
                "Ignore shared blind spots — drift there is undetectable.",
                "Watch risk dimensions where both models share a bias."
            ]
        else:
            plan["explanation"] = ["Need at least 2 model fingerprints for creative design."]
        
        return plan
    
    def design_for_fidelity(self):
        """Design a conversation structure that minimizes drift.
        
        Fidelity = meaning preservation across the chain.
        Strategy: route through models with aligned perceptions, avoid conflicting dims.
        """
        landscape = self.analyze_perception_landscape()
        
        plan = {
            "goal": "maximize_fidelity",
            "routing_recommendation": [],
            "avoid_dimensions": [],
            "safe_dimensions": [],
            "compensate_dimensions": [],
            "explanation": []
        }
        
        if self.fp_b:
            # For fidelity: avoid routing through models that disagree on the
            # dimensions most important to the content.
            
            # Safe: dimensions where both models agree (low gap, high discriminability)
            for d in DIMS:
                gap = landscape["perception_gaps"].get(d, 0)
                disc_a = self.fp_a.get("discriminability", {}).get(d, 1.0)
                disc_b = self.fp_b.get("discriminability", {}).get(d, 1.0)
                if gap < 0.5 and disc_a > 0.3 and disc_b > 0.3:
                    plan["safe_dimensions"].append(d)
            
            # Avoid: dimensions with high perception gap
            for d in DIMS:
                if landscape["perception_gaps"].get(d, 0) > 1.0:
                    plan["avoid_dimensions"].append(d)
            
            # Compensate: shared blind spots (need external verification)
            plan["compensate_dimensions"] = landscape["shared_blind_spots"]
            
            # Routing: alternate models on their complementary dimensions
            for d in landscape["complementary_dims"]:
                disc_a = self.fp_a.get("discriminability", {}).get(d, 1.0)
                disc_b = self.fp_b.get("discriminability", {}).get(d, 1.0)
                if disc_a > disc_b:
                    plan["routing_recommendation"].append({
                        "dimension": d,
                        "use_model": self.fp_a.get("model", "A"),
                        "reason": "%s is sensitive to %s (%.2f > %.2f) — use for verification" % (
                            self.fp_a.get("model", "A"), d, disc_a, disc_b)
                    })
                else:
                    plan["routing_recommendation"].append({
                        "dimension": d,
                        "use_model": self.fp_b.get("model", "B"),
                        "reason": "%s is sensitive to %s (%.2f > %.2f) — use for verification" % (
                            self.fp_b.get("model", "B"), d, disc_b, disc_a)
                    })
            
            plan["explanation"] = [
                "Fidelity is maximized by routing through models that agree on key dimensions.",
                "Use models with complementary blind spots for mutual verification.",
                "Avoid dimensions with high perception gaps — meaning will distort.",
                "Safe dimensions have low gaps and high discriminability in both models.",
                "Compensate for shared blind spots with external verification."
            ]
        else:
            plan["explanation"] = ["Need at least 2 model fingerprints for fidelity design."]
        
        return plan

def demo():
    """Demo: design conversations for Llama Nemotron + GLM-5.1."""
    print("DRIFT-AWARE CONVERSATION DESIGNER")
    print("=" * 72)
    
    # Load fingerprints
    llama_path = Path(__file__).parent.parent / "experiments" / "semantic_fingerprint_llama.json"
    glm_path = Path(__file__).parent.parent / "experiments" / "semantic_fingerprint_glm.json"
    
    if not llama_path.exists() or not glm_path.exists():
        print("ERROR: Fingerprint files not found. Run semantic_fingerprinter first.")
        return
    
    with open(llama_path) as f:
        llama_fp = json.load(f)
    with open(glm_path) as f:
        glm_fp = json.load(f)
    
    designer = DriftAwareDesigner(llama_fp, glm_fp)
    
    # Analyze landscape
    print("\n1. PERCEPTION LANDSCAPE:")
    landscape = designer.analyze_perception_landscape()
    print("   Shared blind spots: %s" % landscape["shared_blind_spots"])
    print("   Complementary dims: %s" % landscape["complementary_dims"])
    print("   Conflicting dims: %s" % landscape["conflicting_dims"])
    print("   Perception gaps: %s" % landscape["perception_gaps"])
    
    # Creative design
    print("\n2. CREATIVE DRIFT DESIGN:")
    creative = designer.design_for_creativity()
    print("   Monitor: %s" % creative["monitor_dimensions"])
    print("   Ignore: %s" % creative["ignore_dimensions"])
    print("   Risk: %s" % creative["risk_dimensions"])
    for rec in creative["routing_recommendation"]:
        print("   Route: %s -> %s for %s" % (rec["first"][:15], rec["then"][:15], rec["dimension"]))
    
    # Fidelity design
    print("\n3. FIDELITY DESIGN:")
    fidelity = designer.design_for_fidelity()
    print("   Safe dims: %s" % fidelity["safe_dimensions"])
    print("   Avoid dims: %s" % fidelity["avoid_dimensions"])
    print("   Compensate: %s" % fidelity["compensate_dimensions"])
    for rec in fidelity["routing_recommendation"]:
        print("   Use %s for %s" % (rec["use_model"][:15], rec["dimension"]))
    
    print("\n" + "=" * 72)

if __name__ == "__main__":
    demo()
