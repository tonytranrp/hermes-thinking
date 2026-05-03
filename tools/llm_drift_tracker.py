#!/usr/bin/env python3
"""
LLM-Based Semantic Drift Tracker - Uses actual LLM judgments for drift.

Instead of synthetic embeddings, asks an LLM to rate semantic similarity
between consecutive utterances. This captures human-like meaning perception.

Uses Vultr Inference API (GLM-5.1-FP8) for judgments.
"""
import sys, json, re, os, time
from pathlib import Path

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

def llm_similarity(text_a: str, text_b: str, api_key: str) -> float:
    """Ask the LLM to rate semantic similarity between two texts (0-1)."""
    import urllib.request
    
    prompt = """Rate the semantic similarity between these two texts on a scale of 0.0 to 1.0.
0.0 = completely unrelated meanings
0.5 = partially overlapping meanings  
1.0 = essentially the same meaning expressed differently

Text A: %s

Text B: %s

Respond with ONLY a number between 0.0 and 1.0, nothing else.""" % (text_a[:500], text_b[:500])
    
    payload = json.dumps({
        "model": "zai-org/GLM-5.1-FP8",
        "messages": [
            {"role": "system", "content": "You are a semantic similarity rater. Respond with ONLY a single float between 0.0 and 1.0. No explanation. No reasoning. Just the number."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0,
        "max_tokens": 10
    }).encode()
    
    req = urllib.request.Request(
        "https://api.vultrinference.com/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": "Bearer %s" % api_key}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            content = data["choices"][0]["message"].get("content", "") or ""
            reasoning = data["choices"][0]["message"].get("reasoning", "") or ""
            # Try content first, then reasoning
            text_to_parse = content if content else reasoning
            match = re.search(r"(\d+\.?\d*)", text_to_parse)
            if match:
                val = float(match.group(1))
                return max(0.0, min(1.0, val))
    except Exception as e:
        print("  API error: %s" % str(e)[:100])
    return 0.5  # fallback

def llm_drift_chain(texts: list, labels: list = None) -> dict:
    """Track drift through a text chain using LLM similarity judgments."""
    api_key = get_api_key()
    if not api_key:
        print("ERROR: No API key found")
        return {}
    
    if labels is None:
        labels = ["step_%d" % i for i in range(len(texts))]
    
    similarities = [1.0]  # first text = reference, similarity 1.0
    drifts = [0.0]
    accumulated = 0.0
    
    print("LLM-BASED SEMANTIC DRIFT TRACKING")
    print("=" * 72)
    print()
    
    for i in range(1, len(texts)):
        sim = llm_similarity(texts[i-1], texts[i], api_key)
        drift = 1.0 - sim
        accumulated += drift
        similarities.append(sim)
        drifts.append(drift)
        
        print("  Step %d [%s] -> [%s]:" % (i, labels[i-1][:15], labels[i][:15]))
        print("    Similarity: %.3f | Drift: %.3f | Accumulated: %.3f" % (sim, drift, accumulated))
        
        time.sleep(0.5)  # rate limiting
    
    fidelity = similarities[-1]
    print()
    print("  Total drift: %.3f" % accumulated)
    print("  Fidelity (sim to source): %.3f" % fidelity)
    print("=" * 72)
    
    return {
        "similarities": similarities,
        "drifts": drifts,
        "accumulated_drift": accumulated,
        "fidelity": fidelity,
        "steps": [{"step": i, "label": labels[i], "sim": similarities[i], "drift": drifts[i]} for i in range(len(texts))]
    }

if __name__ == "__main__":
    # Demo: telephone game with LLM judgments
    texts = [
        "The quantum system exhibits superposition of states",
        "The quantum system shows overlapping conditions",
        "The system displays multiple simultaneous states",
        "The framework presents several concurrent positions",
        "The structure reveals parallel viewpoints",
        "The group shows varying opinions on the matter"
    ]
    labels = ["Physicist", "Translator", "Interpreter", "Analyst", "Manager", "Audience"]
    
    result = llm_drift_chain(texts, labels)
    if result:
        outpath = Path(__file__).parent.parent / "experiments" / "llm_drift_results.json"
        with open(outpath, "w") as f:
            json.dump(result, f, indent=2)
        print("Saved to %s" % outpath)
