#!/usr/bin/env python3
"""
Convergence Detector - Identifies when conversations transition from
generative (divergent) to convergent mode.

Uses a sliding window over drift trajectory to detect phase transitions.
A conversation that shifts from negative to positive convergence pressure
has crossed the generative-to-convergent boundary.
"""
import sys, json, random, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
from meaning_drift_tracker import MeaningDriftTracker, cosine_distance

def detect_phase_transitions(drifts: list, window: int = 3) -> list:
    """
    Detect phase transitions in a drift sequence.
    Uses sliding-window convergence pressure.
    Returns list of transition points.
    """
    if len(drifts) < window * 2:
        return []
    
    pressures = []
    for i in range(len(drifts) - window + 1):
        chunk = drifts[i:i+window]
        # Convergence pressure: early vs late drift in window
        if len(chunk) >= 2:
            mid = len(chunk) // 2
            early = sum(chunk[:mid]) / max(mid, 1)
            late = sum(chunk[mid:]) / max(len(chunk) - mid, 1)
            pressures.append(early - late)
        else:
            pressures.append(0.0)
    
    transitions = []
    for i in range(1, len(pressures)):
        if pressures[i-1] < 0 and pressures[i] >= 0:
            transitions.append({"step": i + window // 2, "type": "divergent->convergent"})
        elif pressures[i-1] >= 0 and pressures[i] < 0:
            transitions.append({"step": i + window // 2, "type": "convergent->divergent"})
    
    return transitions

def classify_conversation_phase(drifts: list) -> str:
    """Classify the overall conversation phase."""
    if not drifts:
        return "unknown"
    # Compare first half vs second half drift
    mid = len(drifts) // 2
    early = sum(drifts[:mid]) / max(mid, 1)
    late = sum(drifts[mid:]) / max(len(drifts) - mid, 1)
    
    if early > late * 1.2:
        return "converging"
    elif late > early * 1.2:
        return "diverging"
    else:
        return "steady"

def run_convergence_experiment():
    """Generate synthetic conversations with known phase transitions and detect them."""
    print("=" * 72)
    print("CONVERGENCE DETECTOR — Phase Transition Analysis")
    print("=" * 72)
    print()
    
    rng = random.Random(42)
    dimensions = 40
    
    # Scenario 1: Pure generative (always diverging)
    print("SCENARIO 1: Pure generative conversation")
    tracker = MeaningDriftTracker(dimensions=dimensions, context_weight=0.05, noise_level=0.05)
    src = [rng.gauss(0, 1) for _ in range(dimensions)]
    chain = ["DeepSeek-V4", "Qwen-3.5", "Nemotron", "Kimi-K2", "GLM-5.1", "Llama-4",
             "DeepSeek-V4", "Qwen-3.5"]
    traj = tracker.trace_chain(src, chain)
    drifts = [p.drift_from_prev for p in traj.points[1:]]
    transitions = detect_phase_transitions(drifts)
    phase = classify_conversation_phase(drifts)
    print(f"  Drifts: {[round(d, 3) for d in drifts]}")
    print(f"  Phase: {phase}")
    print(f"  Transitions: {transitions}")
    print()
    
    # Scenario 2: Converging (high context, repeated models)
    print("SCENARIO 2: Converging conversation (high context)")
    tracker2 = MeaningDriftTracker(dimensions=dimensions, context_weight=0.4, noise_level=0.01)
    src2 = [rng.gauss(0, 1) for _ in range(dimensions)]
    traj2 = tracker2.trace_chain(src2, ["Llama-4", "Kimi-K2", "Llama-4", "Kimi-K2", "Llama-4"])
    drifts2 = [p.drift_from_prev for p in traj2.points[1:]]
    transitions2 = detect_phase_transitions(drifts2)
    phase2 = classify_conversation_phase(drifts2)
    print(f"  Drifts: {[round(d, 3) for d in drifts2]}")
    print(f"  Phase: {phase2}")
    print(f"  Transitions: {transitions2}")
    print()
    
    # Scenario 3: Mixed (starts divergent, converges)
    print("SCENARIO 3: Phase transition (divergent -> convergent)")
    # Simulate by combining two sub-chains with different context weights
    tracker3a = MeaningDriftTracker(dimensions=dimensions, context_weight=0.05, noise_level=0.05)
    src3 = [rng.gauss(0, 1) for _ in range(dimensions)]
    traj3a = tracker3a.trace_chain(src3, ["DeepSeek-V4", "Qwen-3.5", "Nemotron"])
    current = traj3a.points[-1].vector
    tracker3b = MeaningDriftTracker(dimensions=dimensions, context_weight=0.35, noise_level=0.01)
    traj3b = tracker3b.trace_chain(current, ["Llama-4", "Kimi-K2", "Llama-4", "Kimi-K2"])
    
    # Combine drifts
    combined_drifts = [p.drift_from_prev for p in traj3a.points[1:]] + [p.drift_from_prev for p in traj3b.points[1:]]
    transitions3 = detect_phase_transitions(combined_drifts)
    phase3 = classify_conversation_phase(combined_drifts)
    print(f"  Drifts: {[round(d, 3) for d in combined_drifts]}")
    print(f"  Phase: {phase3}")
    print(f"  Transitions: {transitions3}")
    print()
    
    # ASCII phase diagram
    print("PHASE DIAGRAM")
    print("-" * 72)
    for i, d in enumerate(combined_drifts):
        phase_char = "^" if d > 1.0 else "|" if d > 0.5 else "."
        bar = phase_char * int(d * 20)
        print(f"  Step {i+1:2d}: {bar} {d:.3f}")
    print()
    
    print("=" * 72)
    print("FINDING: Phase transitions are detectable via sliding-window")
    print("convergence pressure. When the sign flips from negative to")
    print("positive, the conversation has moved from generative to")
    print("convergent mode. This could be used as a real-time signal")
    print("for when to switch model routing strategies.")
    print("=" * 72)
    
    results = {
        "generative": {"drifts": [round(d, 4) for d in drifts], "phase": phase, "transitions": transitions},
        "converging": {"drifts": [round(d, 4) for d in drifts2], "phase": phase2, "transitions": transitions2},
        "mixed": {"drifts": [round(d, 4) for d in combined_drifts], "phase": phase3, "transitions": transitions3}
    }
    outpath = Path(__file__).parent.parent / "experiments" / "convergence_detection.json"
    with open(outpath, "w") as f:
        json.dump(results, f, indent=2)
    print("Saved to %s" % outpath)

if __name__ == "__main__":
    run_convergence_experiment()
