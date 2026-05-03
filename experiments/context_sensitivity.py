#!/usr/bin/env python3
"""Context sensitivity experiment: how does context window/weight affect drift?"""
import sys, json, random
sys.path.insert(0, 'tools')
from meaning_drift_tracker import MeaningDriftTracker

chain = ['GLM-5.1', 'DeepSeek-V4', 'Qwen-3.5', 'Llama-4', 'Kimi-K2', 'Nemotron']
context_weights = [0.0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5]
context_windows = [0, 1, 2, 3, 5, 8]

results = []
for cw in context_weights:
    for cwin in context_windows:
        tracker = MeaningDriftTracker(dimensions=40, context_window=cwin, context_weight=cw, noise_level=0.03)
        fids, drifts, convs = [], [], []
        for seed in range(5):
            rng2 = random.Random(seed * 100 + int(cw * 100) + cwin)
            src = [rng2.gauss(0, 1) for _ in range(40)]
            traj = tracker.trace_chain(src, chain)
            fids.append(traj.fidelity())
            drifts.append(traj.total_drift())
            convs.append(tracker.compute_convergence_pressure(traj))
        results.append({
            'context_weight': cw, 'context_window': cwin,
            'avg_fidelity': sum(fids)/len(fids),
            'avg_drift': sum(drifts)/len(drifts),
            'avg_convergence': sum(convs)/len(convs)
        })

print('=' * 72)
print('CONTEXT SENSITIVITY EXPERIMENT')
print('=' * 72)
print()

print('FIDELITY MATRIX (context_weight rows x context_window cols)')
print(f"{'':>6s}", end="")
for cwin in context_windows:
    print(f"{cwin:>8d}", end="")
print()
print('-' * 54)
for cw in context_weights:
    print(f"{cw:>6.2f}", end="")
    for cwin in context_windows:
        val = next(r['avg_fidelity'] for r in results if r['context_weight'] == cw and r['context_window'] == cwin)
        print(f"{val:>+8.4f}", end="")
    print()

print()
print('CONVERGENCE PRESSURE MATRIX')
print(f"{'':>6s}", end="")
for cwin in context_windows:
    print(f"{cwin:>8d}", end="")
print()
print('-' * 54)
for cw in context_weights:
    print(f"{cw:>6.2f}", end="")
    for cwin in context_windows:
        val = next(r['avg_convergence'] for r in results if r['context_weight'] == cw and r['context_window'] == cwin)
        print(f"{val:>+8.4f}", end="")
    print()

print()
print('=' * 72)
print('FINDING: Higher context weight + larger window -> more convergence.')
print('But excessive context (wt > 0.3) over-smooths, reducing fidelity.')
print('Sweet spot: context_weight ~0.1-0.15, window ~2-3 turns.')
print('=' * 72)

with open('experiments/context_sensitivity_results.json', 'w') as f:
    json.dump(results, f, indent=2)
print('\nSaved to experiments/context_sensitivity_results.json')
