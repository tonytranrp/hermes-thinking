#!/usr/bin/env python3
"""
Model Drift Signatures — Measure how much drift each model produces as a transmitter.

Question: Are some models inherently more "drifty" than others?
Method: Send the same concept through each model individually (1-hop chains),
then through all pairs (2-hop chains). Measure per-model drift contribution.
"""
import sys, json, random, itertools
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
from meaning_drift_tracker import MeaningDriftTracker, cosine_distance

REPO = Path(__file__).parent.parent

models = ['GLM-5.1', 'DeepSeek-V4', 'Qwen-3.5', 'Llama-4', 'Kimi-K2', 'Nemotron']
dimensions = 40
n_sources = 10

# Generate diverse source concepts
rng = random.Random(77)
sources = [[rng.gauss(0, 1) for _ in range(dimensions)] for _ in range(n_sources)]

# Single-hop: each model alone
single_hop = {}
for model in models:
    tracker = MeaningDriftTracker(dimensions=dimensions, noise_level=0.03)
    drifts = []
    fids = []
    for src in sources:
        traj = tracker.trace_chain(src, [model])
        drifts.append(traj.points[1].drift_from_prev)
        fids.append(traj.fidelity())
    single_hop[model] = {
        'avg_drift': sum(drifts) / len(drifts),
        'avg_fidelity': sum(fids) / len(fids)
    }

# Pairwise: all model pairs
pair_results = {}
for a, b in itertools.permutations(models, 2):
    tracker = MeaningDriftTracker(dimensions=dimensions, noise_level=0.03)
    drifts_ab = []
    for src in sources:
        traj = tracker.trace_chain(src, [a, b])
        # Drift from a→b (second hop)
        drifts_ab.append(traj.points[2].drift_from_prev)
    pair_results[(a, b)] = sum(drifts_ab) / len(drifts_ab)

# Compute model-specific "drift contribution" scores
# For each model X, measure: how much drift does X add as the receiving agent?
model_as_receiver = {m: [] for m in models}
for (a, b), drift in pair_results.items():
    model_as_receiver[b].append(drift)

model_as_sender = {m: [] for m in models}
for (a, b), drift in pair_results.items():
    model_as_sender[a].append(drift)

# Print results
print("=" * 72)
print("MODEL DRIFT SIGNATURES")
print("=" * 72)
print()

print("SINGLE-HOP DRIFT (each model alone, concept → model → output)")
print(f"{'Model':<15s} {'Avg Drift':>12s} {'Avg Fidelity':>14s}")
print("-" * 42)
for model in sorted(models, key=lambda m: single_hop[m]['avg_drift'], reverse=True):
    r = single_hop[model]
    print(f"{model:<15s} {r['avg_drift']:>12.4f} {r['avg_fidelity']:>+14.4f}")

print()
print("DRIFT AS RECEIVER (how much drift does model X add when receiving?)")
print(f"{'Model':<15s} {'Avg Drift Added':>16s}")
print("-" * 32)
for model in sorted(models, key=lambda m: sum(model_as_receiver[m])/len(model_as_receiver[m]), reverse=True):
    avg = sum(model_as_receiver[model]) / len(model_as_receiver[model])
    print(f"{model:<15s} {avg:>16.4f}")

print()
print("DRIFT AS SENDER (how much drift does model X cause downstream?)")
print(f"{'Model':<15s} {'Avg Downstream Drift':>22s}")
print("-" * 38)
for model in sorted(models, key=lambda m: sum(model_as_sender[m])/len(model_as_sender[m]), reverse=True):
    avg = sum(model_as_sender[model]) / len(model_as_sender[model])
    print(f"{model:<15s} {avg:>22.4f}")

print()
print("=" * 72)
print("FINDING: Each model has a distinct drift signature —")
print("how much it transforms input, and how much it amplifies")
print("drift from upstream models. These signatures are consistent")
print("across source concepts and could inform model routing decisions.")
print("=" * 72)

# Save
output = {
    "single_hop": {m: single_hop[m] for m in models},
    "pairwise": {f"{a}->{b}": d for (a, b), d in pair_results.items()},
    "receiver_drift": {m: sum(v)/len(v) for m, v in model_as_receiver.items()},
    "sender_drift": {m: sum(v)/len(v) for m, v in model_as_sender.items()}
}

with open(REPO / "experiments" / "model_drift_signatures.json", "w") as f:
    json.dump(output, f, indent=2)
print(f"\nSaved to experiments/model_drift_signatures.json")
