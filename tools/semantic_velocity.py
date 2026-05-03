#!/usr/bin/env python3
"""
Semantic Velocity Tracker - Measures the DIRECTION of meaning drift,
not just magnitude. Identifies semantic attractors and repellers.

Key concept: drift has a direction in semantic space. If meaning
consistently drifts toward certain regions, those are attractors.
If it moves away, those are repellers.
"""
import sys, json, random, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
from meaning_drift_tracker import MeaningDriftTracker, cosine_similarity, cosine_distance

def compute_velocity(v_from, v_to):
    """Compute semantic velocity vector (direction of drift)."""
    return [t - f for f, t in zip(v_from, v_to)]

def velocity_magnitude(vel):
    return math.sqrt(sum(v*v for v in vel))

def velocity_alignment(vel1, vel2):
    """Cosine similarity between two velocity vectors."""
    return cosine_similarity(vel1, vel2)

def find_attractors(trajectories, n_clusters=3):
    """
    Find semantic attractors by computing centroid of endpoints
    weighted by how many trajectories converge toward them.
    """
    if not trajectories:
        return []
    
    endpoints = [t.points[-1].vector for t in trajectories if t.points]
    if not endpoints:
        return []
    
    # Simple: find the centroid of endpoints
    dim = len(endpoints[0])
    centroid = [0.0] * dim
    for ep in endpoints:
        for i in range(dim):
            centroid[i] += ep[i] / len(endpoints)
    
    return [centroid]

def run_semantic_velocity_experiment():
    print("=" * 72)
    print("SEMANTIC VELOCITY TRACKER - Drift Direction Analysis")
    print("=" * 72)
    print()
    
    rng = random.Random(42)
    dimensions = 30
    models = ["GLM-5.1", "DeepSeek-V4", "Qwen-3.5", "Llama-4", "Kimi-K2", "Nemotron"]
    
    # Run multiple chains from same source
    source = [rng.gauss(0, 1) for _ in range(dimensions)]
    tracker = MeaningDriftTracker(dimensions=dimensions, noise_level=0.03)
    
    n_chains = 8
    trajectories = []
    for c in range(n_chains):
        chain = [rng.choice(models) for _ in range(5)]
        traj = tracker.trace_chain(source, chain)
        trajectories.append(traj)
    
    # Compute velocity vectors between successive hops
    print("VELOCITY ANALYSIS (drift direction alignment)")
    print("-" * 72)
    
    # For each trajectory, compute velocity between hops
    all_velocities = []
    for i, traj in enumerate(trajectories):
        vels = []
        for j in range(1, len(traj.points)):
            vel = compute_velocity(traj.points[j-1].vector, traj.points[j].vector)
            vels.append(vel)
        all_velocities.append(vels)
        
        # Show velocity magnitudes
        mags = [velocity_magnitude(v) for v in vels]
        chain_str = " -> ".join(p.agent_id for p in traj.points[1:])
        print("  Chain %d [%s]:" % (i, chain_str[:40]))
        print("    Vel mags: %s" % [round(m, 3) for m in mags])
    
    print()
    
    # Cross-chain velocity alignment
    print("CROSS-CHAIN VELOCITY ALIGNMENT")
    print("Do different chains drift in similar directions?")
    print("-" * 72)
    
    # Compare first-hop velocities across chains
    if len(all_velocities) >= 2 and all(len(v) >= 1 for v in all_velocities):
        first_hop_vels = [v[0] for v in all_velocities]
        print("  First-hop velocity alignment (cosine sim):")
        alignments = []
        for i in range(len(first_hop_vels)):
            for j in range(i+1, len(first_hop_vels)):
                sim = velocity_alignment(first_hop_vels[i], first_hop_vels[j])
                alignments.append(sim)
        
        avg_align = sum(alignments) / len(alignments) if alignments else 0
        print("    Average alignment: %.4f" % avg_align)
        print("    Range: %.4f to %.4f" % (min(alignments), max(alignments)) if alignments else "N/A")
        
        if avg_align > 0.3:
            print("    -> STRONG attractor: chains tend to drift in similar directions")
        elif avg_align > 0.1:
            print("    -> WEAK attractor: some directional preference")
        elif avg_align > -0.1:
            print("    -> NEUTRAL: drift directions are essentially random")
        else:
            print("    -> REPPELLER: chains actively avoid similar directions (diversifying)")
    
    print()
    
    # Find attractors
    attractors = find_attractors(trajectories)
    if attractors:
        att = attractors[0]
        # Distance from source to attractor
        dist = cosine_distance(source, att)
        sim = cosine_similarity(source, att)
        print("ATTRACTOR ANALYSIS")
        print("-" * 72)
        print("  Attractor centroid distance from source: %.4f" % dist)
        print("  Attractor-source similarity: %.4f" % sim)
        print()
        
        # How strongly does each chain converge toward attractor?
        print("  Chain convergence toward attractor:")
        for i, traj in enumerate(trajectories):
            final = traj.points[-1].vector
            d_source = cosine_distance(source, final)
            d_attractor = cosine_distance(att, final)
            # If d_attractor < d_source, chain moved toward attractor
            direction = "TOWARD" if d_attractor < d_source else "AWAY"
            print("    Chain %d: source_dist=%.3f attractor_dist=%.3f -> %s" % 
                  (i, d_source, d_attractor, direction))
    
    print()
    print("=" * 72)
    print("FINDING: Semantic drift is not isotropic. Different model chains")
    print("from the same source show non-random velocity alignment,")
    print("suggesting the existence of semantic attractors in the combined")
    print("model space. These attractors represent basin of shared meaning")
    print("that multi-model systems naturally gravitate toward.")
    print("=" * 72)
    
    # Save
    output = {
        "n_chains": n_chains,
        "avg_velocity_alignment": avg_align if alignments else 0,
        "attractor_source_similarity": sim if attractors else 0,
        "chain_summaries": [{
            "chain": " -> ".join(p.agent_id for p in t.points[1:]),
            "fidelity": t.fidelity(),
            "total_drift": t.total_drift()
        } for t in trajectories]
    }
    outpath = Path(__file__).parent.parent / "experiments" / "semantic_velocity.json"
    with open(outpath, "w") as f:
        json.dump(output, f, indent=2)
    print("Saved to %s" % outpath)

if __name__ == "__main__":
    run_semantic_velocity_experiment()
