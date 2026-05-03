#!/usr/bin/env python3
"""
Semantic Fingerprint - creates unique perception profiles for each LLM.

A model's "semantic fingerprint" is its pattern of dimensional ratings across
a standardized set of probe texts. Two models with different fingerprints
perceive the same text differently, which is a source of drift in multi-agent
systems.

The fingerprint captures:
  1. Rating bias: systematic over/under-rating on specific dimensions
  2. Discriminability: how well the model distinguishes between text types
  3. Sensitivity: which dimensions change most across different texts
  4. Consistency: how stable ratings are across repeated trials

Usage:
  from semantic_fingerprint import SemanticFingerprinter
  fp = SemanticFingerprinter(api_key=...)
  fingerprint = fp.fingerprint_model("nvidia/Llama-3.1-Nemotron-Safety-Guard-8B-v3")
  print(fp.compare_fingerprints(fingerprint_a, fingerprint_b))
"""
import json, math, time, re, os
from pathlib import Path

# Standard probe texts for fingerprinting
PROBE_TEXTS = {
    "technical": "The quantum system exhibits superposition of states, where particles exist in multiple configurations simultaneously until measurement collapses the wavefunction",
    "casual": "hey so like I was thinking about that thing we talked about earlier and I'm not really sure what to make of it honestly",
    "formal": "The party of the first part shall henceforth be obligated to remit payment in full within thirty business days of receipt of the aforementioned invoice",
    "creative": "The moon hangs heavy in the velvet night, a silver coin tossed carelessly across the darkness, while below the sea sighs its ancient longing",
    "procedural": "First, initialize the counter variable to zero. Then iterate through each element in the array, incrementing the counter by one for each positive value found",
}

DIMENSIONS = [
    "concreteness", "technicality", "formality", "specificity", "agency",
    "temporality", "certainty", "complexity", "emotional", "scope"
]

DIM_DESC = {
    "concreteness": "1=abstract, 5=concrete",
    "technicality": "1=everyday, 5=technical",
    "formality": "1=casual, 5=formal",
    "specificity": "1=vague, 5=precise",
    "agency": "1=passive, 5=active",
    "temporality": "1=timeless, 5=time-bound",
    "certainty": "1=uncertain, 5=certain",
    "complexity": "1=simple, 5=complex",
    "emotional": "1=neutral, 5=emotional",
    "scope": "1=narrow, 5=broad"
}

def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)

def get_api_key():
    config_path = Path.home() / ".hermes" / "config.yaml"
    if config_path.exists():
        content = config_path.read_text()
        for line in content.split("\n"):
            if "api_key" in line and "vultr" not in line.lower():
                parts = line.split("api_key", 1)
                if len(parts) > 1:
                    rest = parts[1].strip().lstrip(":").strip().strip('"').strip("'")
                    if rest and len(rest) > 5:
                        return rest.split()[0].rstrip('"').rstrip("'")
    return os.environ.get("VULTR_API_KEY", "")

class SemanticFingerprinter:
    """Creates unique perception profiles for LLMs."""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or get_api_key()
    
    def rate_text(self, text, model, n_trials=1):
        """Rate a single text on semantic dimensions."""
        import urllib.request
        
        dim_lines = ["  %d. %s (%s)" % (i+1, d, DIM_DESC[d]) for i, d in enumerate(DIMENSIONS)]
        prompt = "Rate this text on 10 dimensions (1-5 each).\n\nText: %s\n\nDimensions:\n%s\n\nOutput ONLY 10 comma-separated integers." % (text[:800], "\n".join(dim_lines))
        
        all_ratings = []
        for trial in range(n_trials):
            payload = json.dumps({
                "model": model,
                "messages": [
                    {"role": "system", "content": "Output ONLY 10 comma-separated integers (1-5). No explanation."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 100
            }).encode()
            
            req = urllib.request.Request(
                "https://api.vultrinference.com/v1/chat/completions",
                data=payload,
                headers={"Content-Type": "application/json", "Authorization": "Bearer %s" % self.api_key}
            )
            
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = json.loads(resp.read())
                    raw = data["choices"][0]["message"].get("content", "") or ""
                    numbers = re.findall(r"\b(\d+)\b", raw)
                    if len(numbers) >= 8:
                        parsed = [max(1, min(5, int(n))) for n in numbers]
                        while len(parsed) < 10:
                            parsed.append(sorted(parsed)[len(parsed)//2])
                        all_ratings.append(parsed[:10])
            except Exception as e:
                pass
            
            if trial < n_trials - 1:
                time.sleep(0.5)
        
        return all_ratings
    
    def fingerprint_model(self, model, n_trials=2):
        """Create a semantic fingerprint for a model.
        
        Returns a dict with the model's perception profile.
        """
        print("FINGERPRINTING: %s" % model)
        print("-" * 50)
        
        probe_ratings = {}
        all_flat = []
        
        for name, text in PROBE_TEXTS.items():
            ratings = self.rate_text(text, model, n_trials=n_trials)
            if ratings:
                # Average across trials
                avg = [sum(r[i] for r in ratings) / len(ratings) for i in range(10)]
                probe_ratings[name] = {
                    "ratings": ratings,
                    "average": [round(x, 2) for x in avg],
                    "consistency": self._consistency(ratings)
                }
                all_flat.extend(ratings)
                print("  %s: %s (consistency: %.3f)" % (name, [round(x,1) for x in avg], probe_ratings[name]["consistency"]))
            else:
                print("  %s: FAILED" % name)
            time.sleep(0.3)
        
        if not probe_ratings:
            return {"error": "No successful ratings"}
        
        # Compute fingerprint metrics
        # 1. Bias: mean rating per dimension across all probes
        bias = []
        for i in range(10):
            dim_vals = [r["average"][i] for r in probe_ratings.values() if "average" in r]
            bias.append(round(sum(dim_vals) / len(dim_vals), 2) if dim_vals else 3.0)
        
        # 2. Discriminability: std dev per dimension across probes
        discriminability = []
        for i in range(10):
            dim_vals = [r["average"][i] for r in probe_ratings.values() if "average" in r]
            if len(dim_vals) > 1:
                mean = sum(dim_vals) / len(dim_vals)
                std = math.sqrt(sum((v - mean)**2 for v in dim_vals) / len(dim_vals))
                discriminability.append(round(std, 2))
            else:
                discriminability.append(0.0)
        
        # 3. Sensitivity: which dimensions vary most (ranked)
        sensitivity_ranking = sorted(range(10), key=lambda i: -discriminability[i])
        
        # 4. Overall consistency
        consistencies = [r["consistency"] for r in probe_ratings.values() if "consistency" in r]
        overall_consistency = round(sum(consistencies) / len(consistencies), 3) if consistencies else 0.0
        
        # 5. Discriminative power (how well this model separates text types)
        # Cosine similarity between most different probe pairs
        probe_names = list(probe_ratings.keys())
        min_sim = 1.0
        max_sim = 0.0
        for i in range(len(probe_names)):
            for j in range(i+1, len(probe_names)):
                if "average" in probe_ratings[probe_names[i]] and "average" in probe_ratings[probe_names[j]]:
                    sim = cosine_similarity(
                        [(v-1)/4 for v in probe_ratings[probe_names[i]]["average"]],
                        [(v-1)/4 for v in probe_ratings[probe_names[j]]["average"]]
                    )
                    min_sim = min(min_sim, sim)
                    max_sim = max(max_sim, sim)
        
        fingerprint = {
            "model": model,
            "n_trials": n_trials,
            "probe_ratings": probe_ratings,
            "bias": {DIMENSIONS[i]: bias[i] for i in range(10)},
            "discriminability": {DIMENSIONS[i]: discriminability[i] for i in range(10)},
            "sensitivity_ranking": [DIMENSIONS[i] for i in sensitivity_ranking],
            "overall_consistency": overall_consistency,
            "discriminative_range": round(max_sim - min_sim, 3),
            "min_inter_text_similarity": round(min_sim, 3),
            "max_inter_text_similarity": round(max_sim, 3),
        }
        
        print("\n  Bias: %s" % fingerprint["bias"])
        print("  Most sensitive dims: %s" % fingerprint["sensitivity_ranking"][:3])
        print("  Consistency: %.3f" % overall_consistency)
        print("  Discriminative range: %.3f" % fingerprint["discriminative_range"])
        
        return fingerprint
    
    def _consistency(self, ratings_list):
        """Compute consistency (1 = perfect, 0 = random)."""
        if len(ratings_list) < 2:
            return 1.0
        # Average std dev per dimension, normalized
        total_std = 0
        for i in range(10):
            vals = [r[i] for r in ratings_list]
            mean = sum(vals) / len(vals)
            std = math.sqrt(sum((v - mean)**2 for v in vals) / len(vals))
            total_std += std
        avg_std = total_std / 10
        return round(max(0, 1.0 - avg_std / 2.0), 3)
    
    def compare_fingerprints(self, fp_a, fp_b):
        """Compare two model fingerprints.
        
        Returns similarity, bias differences, and overlap metrics.
        """
        # Compare bias vectors
        bias_a = [fp_a["bias"].get(d, 3.0) for d in DIMENSIONS]
        bias_b = [fp_b["bias"].get(d, 3.0) for d in DIMENSIONS]
        bias_sim = cosine_similarity([(v-1)/4 for v in bias_a], [(v-1)/4 for v in bias_b])
        
        # Compare discriminability patterns
        disc_a = [fp_a["discriminability"].get(d, 0.0) for d in DIMENSIONS]
        disc_b = [fp_b["discriminability"].get(d, 0.0) for d in DIMENSIONS]
        disc_sim = cosine_similarity(disc_a, disc_b)
        
        # Dimension-by-dimension bias gap
        bias_gaps = {d: round(fp_b["bias"].get(d, 3.0) - fp_a["bias"].get(d, 3.0), 2) for d in DIMENSIONS}
        
        # Sensitivity overlap (do they agree on which dims are most important?)
        top3_a = set(fp_a["sensitivity_ranking"][:3])
        top3_b = set(fp_b["sensitivity_ranking"][:3])
        sensitivity_overlap = len(top3_a & top3_b) / 3.0
        
        return {
            "model_a": fp_a["model"],
            "model_b": fp_b["model"],
            "bias_similarity": round(bias_sim, 4),
            "discriminability_similarity": round(disc_sim, 4),
            "bias_gaps": bias_gaps,
            "sensitivity_overlap": round(sensitivity_overlap, 3),
            "consistency_diff": round(abs(fp_a["overall_consistency"] - fp_b["overall_consistency"]), 3),
            "discriminative_range_diff": round(abs(fp_a["discriminative_range"] - fp_b["discriminative_range"]), 3),
            "perception_distance": round(1.0 - bias_sim, 4)
        }

def demo():
    """Demo: fingerprint Llama Nemotron model."""
    fp = SemanticFingerprinter()
    
    if not fp.api_key:
        print("ERROR: No API key found")
        return
    
    # Fingerprint one model
    fingerprint = fp.fingerprint_model("nvidia/Llama-3.1-Nemotron-Safety-Guard-8B-v3", n_trials=2)
    
    # Save
    outpath = Path(__file__).parent.parent / "experiments" / "semantic_fingerprint_llama.json"
    with open(outpath, "w") as f:
        json.dump(fingerprint, f, indent=2)
    print("\nSaved to %s" % outpath)

if __name__ == "__main__":
    demo()
