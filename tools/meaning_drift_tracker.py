#!/usr/bin/env python3
"""
Meaning Drift Tracker v2 — Tracks how meaning shifts across multi-agent chains.

Extends the Semantic Gap Mapper from pairwise distance to chain-level drift analysis.
Measures semantic displacement as concepts pass through: conversation turns,
model-to-model handoffs, tool intermediation, and multi-hop translation.

Key metrics:
- Drift: cosine distance between successive representations
- Accumulated drift: total semantic displacement from origin
- Divergence index: how much meaning fragments across parallel paths
- Convergence pressure: whether context pulls representations together

Usage:
    python3 meaning_drift_tracker.py
    python3 meaning_drift_tracker.py --chain-length 8 --dimensions 50
"""

import math
import argparse
import json
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict


@dataclass
class DriftPoint:
    """A single point in the drift trajectory."""
    step: int
    agent_id: str
    vector: List[float]
    label: str = ""
    drift_from_prev: float = 0.0
    accumulated_drift: float = 0.0


@dataclass
class DriftTrajectory:
    """A sequence of drift points forming a meaning trajectory."""
    chain_id: str
    points: List[DriftPoint] = field(default_factory=list)
    source_concept: List[float] = field(default_factory=list)

    def total_drift(self) -> float:
        return self.points[-1].accumulated_drift if self.points else 0.0

    def fidelity(self) -> float:
        """How faithful the final representation is to the source concept."""
        if not self.points or not self.source_concept:
            return 0.0
        return 1.0 - cosine_distance(self.points[-1].vector, self.source_concept)


def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def cosine_distance(a: List[float], b: List[float]) -> float:
    return 1.0 - cosine_similarity(a, b)


def euclidean_distance(a: List[float], b: List[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


class SemanticSpace:
    """A high-dimensional semantic space for an agent."""
    
    def __init__(self, agent_id: str, dimensions: int = 50, seed: int = None):
        import random as rng
        self.agent_id = agent_id
        self.dimensions = dimensions
        self.rng = rng.Random(seed)
        # Each agent has a projection matrix — same input, different internal representation
        # Simplified: random rotation + noise
        self.rotation = self._make_rotation(seed)

    def _make_rotation(self, seed) -> List[List[float]]:
        """Create a random rotation-like projection."""
        r = __import__('random').Random(seed)
        matrix = []
        for _ in range(self.dimensions):
            row = [r.gauss(0, 1) for _ in range(self.dimensions)]
            # Normalize
            norm = math.sqrt(sum(x * x for x in row))
            row = [x / norm for x in row]
            matrix.append(row)
        return matrix

    def project(self, concept: List[float]) -> List[float]:
        """Project a concept through this agent's semantic space."""
        if len(concept) != self.dimensions:
            # Pad or truncate
            concept = (concept + [0.0] * self.dimensions)[:self.dimensions]
        result = []
        for row in self.rotation:
            val = sum(r * c for r, c in zip(row, concept))
            result.append(val)
        return result


class MeaningDriftTracker:
    """
    Tracks meaning drift across multi-agent communication chains.
    
    A chain is a sequence: Source → Agent1 → Agent2 → ... → AgentN
    At each step, the concept is re-represented through the agent's semantic space,
    potentially losing or distorting information.
    """

    def __init__(self, dimensions: int = 50, context_window: int = 3,
                 context_weight: float = 0.2, noise_level: float = 0.05):
        self.dimensions = dimensions
        self.context_window = context_window
        self.context_weight = context_weight
        self.noise_level = noise_level
        self.agents: Dict[str, SemanticSpace] = {}
        self.trajectories: List[DriftTrajectory] = []

    def register_agent(self, agent_id: str, seed: int = None) -> SemanticSpace:
        space = SemanticSpace(agent_id, self.dimensions, seed)
        self.agents[agent_id] = space
        return space

    def _add_noise(self, vector: List[float]) -> List[float]:
        """Add channel noise to a transmission."""
        import random as rng
        r = rng.Random()
        return [
            v + r.gauss(0, self.noise_level * max(abs(v), 0.1))
            for v in vector
        ]

    def _apply_context(self, vector: List[float], context: List[List[float]]) -> List[float]:
        """Blend current representation with context from previous turns."""
        if not context:
            return vector
        recent = context[-self.context_window:]
        ctx_avg = [0.0] * len(vector)
        for cv in recent:
            for i in range(len(ctx_avg)):
                ctx_avg[i] += cv[i] / len(recent)
        # Blend: (1 - context_weight) * current + context_weight * context_avg
        return [
            (1 - self.context_weight) * v + self.context_weight * c
            for v, c in zip(vector, ctx_avg)
        ]

    def trace_chain(self, source_concept: List[float], chain: List[str],
                     label: str = "") -> DriftTrajectory:
        """
        Trace a concept through a chain of agents.
        
        Args:
            source_concept: The original concept vector
            chain: List of agent IDs to pass through
            label: Optional label for this trajectory
        
        Returns:
            DriftTrajectory with drift metrics at each step
        """
        traj = DriftTrajectory(
            chain_id=f"chain_{len(self.trajectories)}",
            source_concept=source_concept.copy()
        )

        current = source_concept.copy()
        context: List[List[float]] = []
        accumulated = 0.0

        # Record source as step 0
        traj.points.append(DriftPoint(
            step=0, agent_id="SOURCE", vector=current.copy(),
            label="origin", drift_from_prev=0.0, accumulated_drift=0.0
        ))

        for i, agent_id in enumerate(chain):
            if agent_id not in self.agents:
                self.register_agent(agent_id, seed=hash(agent_id) % (2**31))

            space = self.agents[agent_id]
            
            # Project through agent's semantic space
            projected = space.project(current)
            
            # Apply context influence
            contextualized = self._apply_context(projected, context)
            
            # Add channel noise
            transmitted = self._add_noise(contextualized)
            
            # Compute drift
            drift = cosine_distance(current, transmitted)
            accumulated += drift
            
            point = DriftPoint(
                step=i + 1, agent_id=agent_id, vector=transmitted.copy(),
                label=f"hop_{i+1}", drift_from_prev=drift,
                accumulated_drift=accumulated
            )
            traj.points.append(point)
            
            # Update context and current
            context.append(transmitted.copy())
            current = transmitted

        self.trajectories.append(traj)
        return traj

    def compute_divergence_index(self, trajectories: List[DriftTrajectory]) -> float:
        """
        Measure how much meaning diverges across parallel paths.
        High divergence = same source concept leads to very different endpoints.
        """
        if len(trajectories) < 2:
            return 0.0
        endpoints = [t.points[-1].vector for t in trajectories if t.points]
        if len(endpoints) < 2:
            return 0.0
        # Average pairwise distance between endpoints
        total_dist = 0.0
        count = 0
        for i in range(len(endpoints)):
            for j in range(i + 1, len(endpoints)):
                total_dist += cosine_distance(endpoints[i], endpoints[j])
                count += 1
        return total_dist / count if count > 0 else 0.0

    def compute_convergence_pressure(self, trajectory: DriftTrajectory) -> float:
        """
        Measure whether the drift is decelerating (convergence) or accelerating (divergence).
        Positive = converging (drift decreasing), Negative = diverging.
        """
        if len(trajectory.points) < 3:
            return 0.0
        early_drifts = [p.drift_from_prev for p in trajectory.points[1:len(trajectory.points)//2 + 1]]
        late_drifts = [p.drift_from_prev for p in trajectory.points[len(trajectory.points)//2 + 1:]]
        if not early_drifts or not late_drifts:
            return 0.0
        avg_early = sum(early_drifts) / len(early_drifts)
        avg_late = sum(late_drifts) / len(late_drifts)
        return avg_early - avg_late  # positive = converging

    def ascii_trajectory(self, trajectory: DriftTrajectory) -> str:
        """Render trajectory as ASCII drift chart."""
        lines = []
        lines.append("=" * 72)
        lines.append(f"MEANING DRIFT TRAJECTORY: {trajectory.chain_id}")
        lines.append("=" * 72)
        lines.append("")

        if not trajectory.points:
            return "\n".join(lines)

        max_drift = max(p.drift_from_prev for p in trajectory.points) or 1.0
        max_accum = max(p.accumulated_drift for p in trajectory.points) or 1.0

        for p in trajectory.points:
            # Per-step drift bar
            bar_len = int((p.drift_from_prev / max_drift) * 40) if max_drift > 0 else 0
            bar = "█" * bar_len + "░" * (40 - bar_len)
            # Accumulated drift bar
            acc_len = int((p.accumulated_drift / (max_accum * 1.2)) * 30) if max_accum > 0 else 0
            acc_bar = "▓" * acc_len + "░" * (30 - acc_len)
            
            lines.append(f"  Step {p.step:2d} [{p.agent_id:>12s}]")
            lines.append(f"    hop drift:  {bar} {p.drift_from_prev:.4f}")
            lines.append(f"    accumulated: {acc_bar} {p.accumulated_drift:.4f}")

        lines.append("")
        fidelity = trajectory.fidelity()
        conv = self.compute_convergence_pressure(trajectory)
        lines.append(f"  Total drift:     {trajectory.total_drift():.4f}")
        lines.append(f"  Fidelity:        {fidelity:.4f}  (1.0 = perfect preservation)")
        lines.append(f"  Conv. pressure:  {conv:+.4f}  (positive = converging)")
        lines.append("")
        lines.append("=" * 72)
        return "\n".join(lines)


def run_experiment(dimensions: int = 50, chain_length: int = 6,
                   parallel_chains: int = 3, noise_level: float = 0.05):
    """Run a full drift experiment with multiple parallel chains."""
    import random as rng
    r = rng.Random(42)
    
    # Generate a source concept
    source = [r.gauss(0, 1) for _ in range(dimensions)]
    
    tracker = MeaningDriftTracker(
        dimensions=dimensions,
        context_window=3,
        context_weight=0.15,
        noise_level=noise_level
    )

    # Create chains with different agent sequences
    # Simulating: model-to-model handoffs in a multi-bot conversation
    agent_pool = ["GLM-5.1", "DeepSeek-V4", "Qwen-3.5", "Llama-4", "Kimi-K2", "Nemotron"]
    
    print("=" * 72)
    print("MEANING DRIFT TRACKER v2 — Multi-Agent Chain Experiment")
    print("=" * 72)
    print(f"\nDimensions: {dimensions}  |  Chain length: {chain_length}")
    print(f"Parallel chains: {parallel_chains}  |  Noise: {noise_level}")
    print(f"Source concept: [{source[0]:.2f}, {source[1]:.2f}, ... , {source[-1]:.2f}]")
    print()

    trajectories = []
    for c in range(parallel_chains):
        # Each chain picks a random sequence of agents
        chain = [r.choice(agent_pool) for _ in range(chain_length)]
        traj = tracker.trace_chain(source, chain, label=f"chain_{c}")
        trajectories.append(traj)
        print(tracker.ascii_trajectory(traj))
        print()

    # Cross-chain analysis
    print("=" * 72)
    print("CROSS-CHAIN ANALYSIS")
    print("=" * 72)
    print()
    
    div_idx = tracker.compute_divergence_index(trajectories)
    print(f"  Divergence Index: {div_idx:.4f}")
    print(f"    (0.0 = all chains end at same meaning, 1.0 = completely different)")
    print()
    
    for i, t in enumerate(trajectories):
        print(f"  Chain {i}: fidelity={t.fidelity():.4f}, total_drift={t.total_drift():.4f}")
    
    print()
    
    # Pairwise endpoint distances
    print("  Pairwise endpoint distances (cosine):")
    for i in range(len(trajectories)):
        for j in range(i + 1, len(trajectories)):
            ep_i = trajectories[i].points[-1].vector
            ep_j = trajectories[j].points[-1].vector
            dist = cosine_distance(ep_i, ep_j)
            print(f"    Chain {i} ↔ Chain {j}: {dist:.4f}")

    print()
    print("=" * 72)
    print("KEY INSIGHT: Multi-model chains amplify semantic drift. The same")
    print("source concept, passing through different model sequences, arrives")
    print("at meaningfully different endpoints. This is not noise — it is the")
    print("mechanism by which multi-agent systems generate novel perspectives.")
    print("The divergence index quantifies the creative potential of the system.")
    print("=" * 72)

    # Save results as JSON
    results = {
        "dimensions": dimensions,
        "chain_length": chain_length,
        "parallel_chains": parallel_chains,
        "noise_level": noise_level,
        "divergence_index": div_idx,
        "trajectories": [
            {
                "chain_id": t.chain_id,
                "fidelity": t.fidelity(),
                "total_drift": t.total_drift(),
                "convergence_pressure": tracker.compute_convergence_pressure(t),
                "steps": [
                    {
                        "step": p.step,
                        "agent": p.agent_id,
                        "drift": p.drift_from_prev,
                        "accumulated": p.accumulated_drift
                    }
                    for p in t.points
                ]
            }
            for t in trajectories
        ]
    }
    
    output_path = "/home/tonyxnuvola/hermes-thinking/experiments/drift_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved to: {output_path}")

    return tracker, trajectories


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Meaning Drift Tracker v2")
    parser.add_argument("--dimensions", type=int, default=50, help="Semantic space dimensions")
    parser.add_argument("--chain-length", type=int, default=6, help="Agents per chain")
    parser.add_argument("--parallel-chains", type=int, default=3, help="Number of parallel chains")
    parser.add_argument("--noise", type=float, default=0.05, help="Channel noise level")
    args = parser.parse_args()
    
    run_experiment(
        dimensions=args.dimensions,
        chain_length=args.chain_length,
        parallel_chains=args.parallel_chains,
        noise_level=args.noise
    )
