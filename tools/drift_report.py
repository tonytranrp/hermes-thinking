#!/usr/bin/env python3
"""
Unified Drift Report — runs the full drift analysis suite.

Produces a comprehensive report combining:
  - Meaning drift tracker (fidelity, convergence, divergence index)
  - Drift atlas (corpus-wide patterns)
  - Semantic velocity (direction and speed)
  - Semantic fingerprint (model perception profiles)
  - Perception gap adjuster (bias-corrected drift)
  - Drift predictor (forecast with model selection)
  - Drift budget (how many hops can you afford?)
  - Attractor landscape (semantic basins)
  - Cross-session drift (longitudinal co-evolution)

Usage:
  python3 tools/drift_report.py
  python3 tools/drift_report.py --quick   # skip expensive API calls
"""
import json, sys, os
from pathlib import Path
from datetime import datetime

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent))

def run_tracker():
    """Run meaning drift tracker."""
    from meaning_drift_tracker import MeaningDriftTracker, cosine_similarity
    tracker = MeaningDriftTracker(dimensions=10)
    
    # Register agents
    tracker.register_agent("source", seed=42)
    for i in range(5):
        tracker.register_agent(f"hop_{i+1}", seed=100+i)
    
    # Trace a chain
    source = [3.0, 4.0, 5.0, 2.0, 4.0, 3.0, 5.0, 2.0, 4.0, 3.0]
    trajectory = tracker.trace_chain(source, ["source", "hop_1", "hop_2", "hop_3", "hop_4", "hop_5"])
    
    # Compute fidelity (cosine similarity of last point to source)
    last_vec = trajectory.points[-1].vector
    fidelity = cosine_similarity(source, last_vec)
    
    return {
        "fidelity": round(fidelity, 4),
        "total_drift": round(trajectory.points[-1].accumulated_drift, 4),
        "hops": 5
    }

def run_text_mode():
    """Run text-mode drift analysis."""
    from drift_text_mode import TextEmbedder, cosine_similarity
    
    texts = [
        "Quantum entanglement is a physical phenomenon where particles become interconnected.",
        "When tiny particles link up, they share properties across any distance.",
        "Small bits of matter connect in ways that defy normal space limitations.",
        "Little things join together and feel each other no matter how far apart."
    ]
    
    embedder = TextEmbedder()
    embedder.fit(texts)
    
    # Track drift through the chain
    embeddings = [embedder.embed(t) for t in texts]
    fidelities = []
    for i in range(1, len(embeddings)):
        sim = cosine_similarity(embeddings[0], embeddings[i])
        fidelities.append(round(sim, 4))
    
    return {
        "fidelity": fidelities[-1] if fidelities else 1.0,
        "per_step_drift": round(1.0 - sum(fidelities) / len(fidelities), 4) if fidelities else 0.0
    }

def run_predictor():
    """Run drift predictor."""
    from drift_predictor import DriftPredictor
    predictor = DriftPredictor()
    
    telephone = [1.0, 0.948, 0.945, 1.000, 0.863, 0.832]
    result = predictor.predict(telephone, total_steps=8)
    return {
        "predicted_fidelity": result["predicted_fidelity"],
        "trajectory": result["trajectory"],
        "best_model": result.get("best_model", "unknown"),
        "model_comparison": result.get("model_comparison", {})
    }

def run_budget():
    """Run drift budget analysis."""
    from drift_budget import DriftBudget
    
    budgets = {}
    for name, rate in [("llm_dimension", 0.068), ("default", 0.15), ("text_tfidf", 0.781)]:
        b = DriftBudget(target_fidelity=0.7, drift_rate=rate)
        budgets[name] = {
            "max_hops": b.max_hops(),
            "drift_rate": rate,
            "drift_tax_pct": round(rate * 100, 1)
        }
    return budgets

def run_velocity():
    """Run semantic velocity analysis."""
    from semantic_velocity import compute_velocity, velocity_magnitude, velocity_alignment
    
    # Create a simple trajectory
    trajectory = [(0.1 * i, 0.05 * i) for i in range(10)]
    
    # Compute velocities
    velocities = [compute_velocity(trajectory[i], trajectory[i+1]) for i in range(len(trajectory)-1)]
    mags = [velocity_magnitude(v) for v in velocities]
    alignments = [velocity_alignment(velocities[i], velocities[i+1]) for i in range(len(velocities)-1)]
    
    return {
        "avg_velocity": round(sum(mags) / len(mags), 4) if mags else 0,
        "avg_alignment": round(sum(alignments) / len(alignments), 4) if alignments else 0,
        "attractor_direction": "converging" if sum(alignments) / len(alignments) > 0.5 else "diverging" if alignments else "unknown"
    }

def run_fingerprint():
    """Check if fingerprint data exists."""
    comp_path = Path(__file__).parent.parent / "experiments" / "model_fingerprint_comparison.json"
    if comp_path.exists():
        with open(comp_path) as f:
            data = json.load(f)
        summary = {}
        for name, mdata in data.get("models", {}).items():
            summary[name] = {
                "consistency": mdata.get("consistency", "N/A"),
                "discriminative_range": mdata.get("discriminative_range", "N/A"),
                "blind_spot": mdata.get("blind_spots", ["N/A"])[0] if mdata.get("blind_spots") else "N/A"
            }
        return summary
    return {"status": "no fingerprint data found"}

def generate_report(quick=False):
    """Generate the full drift report."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "mode": "quick" if quick else "full",
        "results": {}
    }
    
    print("=" * 72)
    print("UNIFIED DRIFT REPORT")
    print("Generated:", report["timestamp"])
    print("=" * 72)
    
    # Run each analysis
    analyses = [
        ("Meaning Drift Tracker", run_tracker, not quick),
        ("Text-Mode Drift", run_text_mode, not quick),
        ("Drift Predictor", run_predictor, True),
        ("Drift Budget", run_budget, True),
        ("Semantic Velocity", run_velocity, not quick),
        ("Semantic Fingerprint", run_fingerprint, True),
    ]
    
    for name, fn, should_run in analyses:
        if not should_run:
            report["results"][name] = {"status": "skipped (quick mode)"}
            continue
        try:
            print(f"\n  Running {name}...")
            result = fn()
            report["results"][name] = result
            print(f"  ✓ {name} complete")
        except Exception as e:
            report["results"][name] = {"status": f"error: {str(e)}"}
            print(f"  ✗ {name} failed: {e}")
    
    # Summary
    print("\n" + "=" * 72)
    print("SUMMARY")
    print("-" * 72)
    
    for name, result in report["results"].items():
        if isinstance(result, dict) and "status" in result and "error" in str(result.get("status", "")):
            print(f"  {name}: FAILED")
        elif isinstance(result, dict) and result.get("status") == "skipped (quick mode)":
            print(f"  {name}: SKIPPED")
        else:
            print(f"  {name}: OK")
    
    # Key metrics
    print("\nKEY METRICS:")
    if "Meaning Drift Tracker" in report["results"] and isinstance(report["results"]["Meaning Drift Tracker"], dict):
        mdt = report["results"]["Meaning Drift Tracker"]
        if "fidelity" in mdt:
            print(f"  Chain fidelity: {mdt['fidelity']:.4f}")
    
    if "Drift Budget" in report["results"] and isinstance(report["results"]["Drift Budget"], dict):
        for regime, info in report["results"]["Drift Budget"].items():
            print(f"  Budget ({regime}): {info['max_hops']} hops max (tax: {info['drift_tax_pct']}%/hop)")
    
    if "Drift Predictor" in report["results"] and isinstance(report["results"]["Drift Predictor"], dict):
        dp = report["results"]["Drift Predictor"]
        print(f"  Predicted trajectory: {dp.get('trajectory', 'N/A')} (best model: {dp.get('best_model', 'N/A')})")
    
    if "Semantic Fingerprint" in report["results"] and isinstance(report["results"]["Semantic Fingerprint"], dict):
        sf = report["results"]["Semantic Fingerprint"]
        for model, info in sf.items():
            if isinstance(info, dict) and "discriminative_range" in info:
                print(f"  {model}: discriminative_range={info['discriminative_range']}, blind_spot={info.get('blind_spot', 'N/A')}")
    
    print("=" * 72)
    
    # Save
    outpath = Path(__file__).parent.parent / "experiments" / "unified_drift_report.json"
    with open(outpath, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nSaved to {outpath}")
    
    return report

if __name__ == "__main__":
    quick = "--quick" in sys.argv
    generate_report(quick=quick)
