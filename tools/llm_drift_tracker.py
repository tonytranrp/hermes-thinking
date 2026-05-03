#!/usr/bin/env python3
"""
LLM-Based Semantic Drift Tracker - v2: Semantic Dimension Rating

Instead of asking an LLM for a direct similarity score (which reasoning models
handle poorly), we rate both texts on 10 semantic dimensions, then compute
cosine similarity between the dimension vectors. This is more robust and
produces richer data for drift analysis.

Dimensions:
  1. Concreteness    (1=abstract, 5=concrete)
  2. Technicality    (1=everyday, 5=highly technical)
  3. Formality       (1=casual, 5=formal)
  4. Specificity     (1=vague, 5=precise)
  5. Agency          (1=passive/object, 5=active/subject)
  6. Temporality     (1=timeless, 5=time-bound)
  7. Certainty       (1=uncertain, 5=certain)
  8. Complexity      (1=simple, 5=complex)
  9. Emotional       (1=neutral, 5=emotionally charged)
 10. Scope           (1=narrow/focused, 5=broad/systemic)

Uses Vultr Inference API.
"""
import sys, json, re, os, time, math
from pathlib import Path

DIMENSIONS = [
    "concreteness", "technicality", "formality", "specificity", "agency",
    "temporality", "certainty", "complexity", "emotional", "scope"
]

DIM_DESCRIPTIONS = {
    "concreteness": "1=abstract/conceptual, 5=concrete/tangible",
    "technicality": "1=everyday language, 5=highly technical jargon",
    "formality": "1=casual/colloquial, 5=formal/academic",
    "specificity": "1=vague/general, 5=precise/specific",
    "agency": "1=passive/objects, 5=active/subjects with agency",
    "temporality": "1=timeless/eternal, 5=time-bound/situational",
    "certainty": "1=uncertain/hedged, 5=certain/assertive",
    "complexity": "1=simple/single-factor, 5=complex/multi-factor",
    "emotional": "1=neutral/detached, 5=emotionally charged",
    "scope": "1=narrow/focused, 5=broad/systemic"
}

def get_api_key():
    """Extract API key from hermes config."""
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

def cosine_similarity(a, b):
    """Cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)

# Default model for dimension rating: Llama Nemotron is a non-reasoning model
# that produces clean, parseable output. Reasoning models (GLM-5.1, Qwen3.5,
# Nemotron-3-Nano) consume all tokens on chain-of-thought and return null content.
DEFAULT_RATING_MODEL = "nvidia/Llama-3.1-Nemotron-Safety-Guard-8B-v3"

def rate_text_dimensions(text: str, api_key: str, model: str = None) -> list:
    """Rate a text on all 10 semantic dimensions via LLM.
    
    Returns a list of 10 floats (1-5 scale) or None on failure.
    """
    import urllib.request
    
    if model is None:
        model = DEFAULT_RATING_MODEL
    
    dim_lines = []
    for i, dim in enumerate(DIMENSIONS, 1):
        dim_lines.append("  %d. %s (%s)" % (i, dim, DIM_DESCRIPTIONS[dim]))
    
    prompt = """Rate the following text on each of 10 semantic dimensions.
Each dimension is a scale from 1 to 5.

Text: %s

Dimensions:
%s

Respond with ONLY 10 numbers separated by commas, like: 3,4,2,5,1,4,3,2,1,4
No explanation. No extra text.""" % (text[:800], "\n".join(dim_lines))
    
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": "You rate texts on semantic dimensions. Output ONLY comma-separated integers. Example: 3,4,2,5,1,4,3,2,1,4"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 100
    }).encode()
    
    req = urllib.request.Request(
        "https://api.vultrinference.com/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": "Bearer %s" % api_key}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            content = data["choices"][0]["message"].get("content", "") or ""
            reasoning = data["choices"][0]["message"].get("reasoning", "") or ""
            
            # Try content first, then fall back to reasoning
            text_to_parse = content if content.strip() else reasoning
            
            # Extract all numbers from the response
            numbers = re.findall(r"\b(\d+)\b", text_to_parse)
            if len(numbers) >= 10:
                ratings = [max(1, min(5, int(n))) for n in numbers[:10]]
                return ratings
            elif len(numbers) >= 8:
                # Close enough — pad missing dimensions with median
                parsed = [max(1, min(5, int(n))) for n in numbers]
                while len(parsed) < 10:
                    parsed.append(sorted(parsed)[len(parsed)//2])  # median
                return parsed[:10]
            
            # Try comma-separated
            if "," in text_to_parse:
                parts = text_to_parse.split(",")
                ratings = []
                for p in parts[:10]:
                    n = re.search(r"(\d+)", p.strip())
                    if n:
                        ratings.append(max(1, min(5, int(n.group(1)))))
                if len(ratings) == 10:
                    return ratings
                    
    except Exception as e:
        print("  API error: %s" % str(e)[:100])
    return None

def llm_similarity_dimensional(text_a: str, text_b: str, api_key: str) -> dict:
    """Compute semantic similarity between two texts via dimension rating.
    
    Returns dict with ratings for both texts, cosine similarity, and per-dimension diffs.
    """
    ratings_a = rate_text_dimensions(text_a, api_key)
    if not ratings_a:
        return {"similarity": 0.5, "error": "Failed to rate text A"}
    
    time.sleep(0.5)  # rate limiting
    
    ratings_b = rate_text_dimensions(text_b, api_key)
    if not ratings_b:
        return {"similarity": 0.5, "error": "Failed to rate text B"}
    
    # Normalize to 0-1 range (from 1-5)
    norm_a = [(r - 1) / 4.0 for r in ratings_a]
    norm_b = [(r - 1) / 4.0 for r in ratings_b]
    
    sim = cosine_similarity(norm_a, norm_b)
    
    # Per-dimension drift
    dim_drifts = {}
    for i, dim in enumerate(DIMENSIONS):
        dim_drifts[dim] = {
            "a": ratings_a[i],
            "b": ratings_b[i],
            "diff": ratings_b[i] - ratings_a[i]
        }
    
    return {
        "similarity": round(sim, 4),
        "ratings_a": ratings_a,
        "ratings_b": ratings_b,
        "dimension_drifts": dim_drifts
    }

def llm_drift_chain(texts: list, labels: list = None) -> dict:
    """Track drift through a text chain using LLM dimension ratings."""
    api_key = get_api_key()
    if not api_key:
        print("ERROR: No API key found")
        return {}
    
    if labels is None:
        labels = ["step_%d" % i for i in range(len(texts))]
    
    print("LLM SEMANTIC DIMENSION DRIFT TRACKING")
    print("=" * 72)
    print("Method: Rate each text on 10 semantic dimensions, compute cosine similarity")
    print("Dimensions: %s" % ", ".join(DIMENSIONS))
    print()
    
    # Rate all texts first
    all_ratings = []
    for i, text in enumerate(texts):
        print("  Rating [%s]..." % labels[i], end=" ", flush=True)
        ratings = rate_text_dimensions(text, api_key)
        if ratings:
            all_ratings.append(ratings)
            print("OK: %s" % ratings)
        else:
            print("FAILED — using fallback [3,3,3,3,3,3,3,3,3,3]")
            all_ratings.append([3] * 10)  # neutral fallback
        if i < len(texts) - 1:
            time.sleep(0.5)
    
    print()
    
    # Compute pairwise similarities
    similarities = [1.0]
    drifts = [0.0]
    accumulated = 0.0
    dimension_trajectories = {dim: [all_ratings[0][i]] for i, dim in enumerate(DIMENSIONS)}
    
    for i in range(1, len(texts)):
        norm_a = [(r - 1) / 4.0 for r in all_ratings[i-1]]
        norm_b = [(r - 1) / 4.0 for r in all_ratings[i]]
        sim = cosine_similarity(norm_a, norm_b)
        drift = 1.0 - sim
        accumulated += drift
        similarities.append(round(sim, 4))
        drifts.append(round(drift, 4))
        
        # Track dimension trajectories
        for j, dim in enumerate(DIMENSIONS):
            dimension_trajectories[dim].append(all_ratings[i][j])
        
        # Find biggest dimension shift
        max_dim = max(DIMENSIONS, key=lambda d: abs(all_ratings[i][DIMENSIONS.index(d)] - all_ratings[i-1][DIMENSIONS.index(d)]))
        max_shift = abs(all_ratings[i][DIMENSIONS.index(max_dim)] - all_ratings[i-1][DIMENSIONS.index(max_dim)])
        
        print("  Step %d [%s] -> [%s]:" % (i, labels[i-1][:15], labels[i][:15]))
        print("    Similarity: %.3f | Drift: %.3f | Accumulated: %.3f" % (sim, drift, accumulated))
        print("    Biggest shift: %s (%+d)" % (max_dim, all_ratings[i][DIMENSIONS.index(max_dim)] - all_ratings[i-1][DIMENSIONS.index(max_dim)]))
    
    # Fidelity = similarity of last to first
    norm_first = [(r - 1) / 4.0 for r in all_ratings[0]]
    norm_last = [(r - 1) / 4.0 for r in all_ratings[-1]]
    fidelity = cosine_similarity(norm_first, norm_last)
    
    # Overall dimension shifts (first to last)
    total_shifts = {}
    for j, dim in enumerate(DIMENSIONS):
        total_shifts[dim] = all_ratings[-1][j] - all_ratings[0][j]
    
    print()
    print("  Total drift: %.3f" % accumulated)
    print("  Fidelity (sim to source): %.3f" % fidelity)
    print()
    print("  Dimension shifts (source -> final):")
    for dim in DIMENSIONS:
        shift = total_shifts[dim]
        arrow = "↑" if shift > 0 else "↓" if shift < 0 else "→"
        print("    %s: %d -> %d (%s%d)" % (dim, all_ratings[0][DIMENSIONS.index(dim)], all_ratings[-1][DIMENSIONS.index(dim)], arrow, shift))
    
    print("=" * 72)
    
    return {
        "method": "semantic_dimension_rating",
        "dimensions": DIMENSIONS,
        "similarities": similarities,
        "drifts": drifts,
        "accumulated_drift": round(accumulated, 4),
        "fidelity": round(fidelity, 4),
        "all_ratings": all_ratings,
        "dimension_trajectories": dimension_trajectories,
        "total_dimension_shifts": total_shifts,
        "steps": [
            {
                "step": i,
                "label": labels[i],
                "ratings": all_ratings[i],
                "sim_to_prev": similarities[i],
                "drift_from_prev": drifts[i]
            }
            for i in range(len(texts))
        ]
    }

if __name__ == "__main__":
    # Demo: telephone game with LLM dimension ratings
    texts = [
        "The quantum system exhibits superposition of states, where particles exist in multiple configurations simultaneously until measurement collapses the wavefunction",
        "The quantum system shows overlapping conditions where things can be in multiple states at the same time",
        "The system displays multiple simultaneous states that coexist before being observed",
        "The framework presents several concurrent positions that exist together until someone looks at them",
        "The structure reveals parallel viewpoints that are held simultaneously",
        "The group shows varying opinions on the matter that they hold at the same time"
    ]
    labels = ["Physicist", "Translator", "Interpreter", "Analyst", "Manager", "Audience"]
    
    result = llm_drift_chain(texts, labels)
    if result:
        outpath = Path(__file__).parent.parent / "experiments" / "llm_drift_results.json"
        with open(outpath, "w") as f:
            json.dump(result, f, indent=2)
        print("\nSaved to %s" % outpath)
