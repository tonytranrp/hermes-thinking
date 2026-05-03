#!/usr/bin/env python3
"""
Drift-Aware Router - Selects optimal model sequences based on drift targets.
"""
import sys, json, random, itertools
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
from meaning_drift_tracker import MeaningDriftTracker

MODELS = ["GLM-5.1", "DeepSeek-V4", "Qwen-3.5", "Llama-4", "Kimi-K2", "Nemotron"]

def evaluate_routing(chain, sources, dimensions=40):
    tracker = MeaningDriftTracker(dimensions=dimensions, context_window=3, context_weight=0.15, noise_level=0.03)
    fids, drifts, convs = [], [], []
    for src in sources:
        traj = tracker.trace_chain(src, chain)
        fids.append(traj.fidelity())
        drifts.append(traj.total_drift())
        convs.append(tracker.compute_convergence_pressure(traj))
    return {"chain": chain, "avg_fidelity": sum(fids)/len(fids), "avg_drift": sum(drifts)/len(drifts), "avg_convergence": sum(convs)/len(convs)}

def search_optimal_routing(target="balanced", chain_length=3, n_candidates=50, n_sources=8):
    rng = random.Random(42)
    sources = [[rng.gauss(0, 1) for _ in range(40)] for _ in range(n_sources)]
    candidates = [[rng.choice(MODELS) for _ in range(chain_length)] for _ in range(n_candidates)]
    if chain_length <= 3:
        for perm in itertools.permutations(MODELS, chain_length):
            candidates.append(list(perm))
    results = [evaluate_routing(c, sources) for c in candidates]
    if target == "faithful":
        results.sort(key=lambda r: r["avg_fidelity"], reverse=True)
        metric = "fidelity"
    elif target == "creative":
        results.sort(key=lambda r: r["avg_drift"], reverse=True)
        metric = "drift"
    else:
        results.sort(key=lambda r: r["avg_fidelity"] * r["avg_drift"], reverse=True)
        metric = "fidelity*drift"
    return {"target": target, "metric": metric, "n_evaluated": len(results),
            "top_5": [{"chain": " -> ".join(r["chain"]), "fidelity": round(r["avg_fidelity"], 4), "drift": round(r["avg_drift"], 4), "convergence": round(r["avg_convergence"], 4)} for r in results[:5]],
            "worst_3": [{"chain": " -> ".join(r["chain"]), "fidelity": round(r["avg_fidelity"], 4), "drift": round(r["avg_drift"], 4)} for r in results[-3:]]}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=["faithful", "creative", "balanced"], default="balanced")
    parser.add_argument("--chain-length", type=int, default=3)
    parser.add_argument("--candidates", type=int, default=60)
    args = parser.parse_args()
    print("=" * 72)
    print("DRIFT-AWARE ROUTER - Target: %s" % args.target.upper())
    print("=" * 72)
    result = search_optimal_routing(args.target, args.chain_length, args.candidates)
    print("Evaluated: %d sequences | Optimizing: %s" % (result["n_evaluated"], result["metric"]))
    print("TOP 5 ROUTINGS:")
    print("  %-35s %10s %8s %8s" % ("Chain", "Fidelity", "Drift", "Conv.P"))
    print("  " + "-" * 63)
    for r in result["top_5"]:
        print("  %-35s %+10.4f %8.4f %+8.4f" % (r["chain"], r["fidelity"], r["drift"], r["convergence"]))
    print("WORST 3:")
    for r in result["worst_3"]:
        print("  %-35s %+10.4f %8.4f" % (r["chain"], r["fidelity"], r["drift"]))
    best = result["top_5"][0]
    print("=" * 72)
    print("RECOMMENDATION: %s (fid %+.4f, drift %.4f)" % (best["chain"], best["fidelity"], best["drift"]))
    print("=" * 72)
    outpath = Path(__file__).parent.parent / "experiments" / ("routing_%s.json" % args.target)
    with open(outpath, "w") as f:
        json.dump(result, f, indent=2)
    print("Saved to %s" % outpath)
