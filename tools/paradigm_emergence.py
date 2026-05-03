#!/usr/bin/env python3
"""
Paradigm Emergence Simulator — Models how knowledge paradigms form, consolidate,
and collapse through Hebbian learning, preferential attachment, and pruning.

Based on "The Topology of Ideas" dialogue:
- Concepts are nodes in a weighted graph
- Hebbian reinforcement: co-activated concepts strengthen their connection
- Preferential attachment: well-connected concepts attract more connections
- Pruning: weak connections below threshold die
- Paradigm shift: when pruning disconnects the graph, a new paradigm forms

Usage:
    python3 paradigm_emergence.py
    python3 paradigm_emergence.py --concepts 60 --steps 200 --prune-threshold 0.08
"""

import random
import math
import argparse
from collections import defaultdict


class ConceptNetwork:
    """A network of concepts with weighted edges and dynamics."""
    
    def __init__(self, n_concepts=40, seed=None):
        self.rng = random.Random(seed)
        self.n = n_concepts
        self.nodes = list(range(n_concepts))
        # Edge weights: {(i,j): float} where i < j
        self.edges = {}
        # Edge age: {(i,j): int} — how many steps since edge was created/last reinforced
        self.edge_age = {}
        # Activation levels: {node: float}
        self.activation = {i: 0.0 for i in self.nodes}
        # Track paradigm membership: {node: paradigm_id}
        self.paradigm = {i: 0 for i in self.nodes}
        # History tracking
        self.n_paradigms_history = []
        self.n_edges_history = []
        self.avg_weight_history = []
        self.density_history = []
        self.shift_events = []
        self.step = 0
        
        # Initialize with sparse random connections — some above prune threshold
        for i in range(n_concepts):
            for j in range(i + 1, n_concepts):
                if self.rng.random() < 0.12:  # 12% initial density
                    self.edges[(i, j)] = self.rng.uniform(0.03, 0.12)
                    self.edge_age[(i, j)] = 0
    
    def _edge_key(self, i, j):
        return (min(i, j), max(i, j))
    
    def get_weight(self, i, j):
        key = self._edge_key(i, j)
        return self.edges.get(key, 0.0)
    
    def set_weight(self, i, j, w):
        key = self._edge_key(i, j)
        if w > 0.001:
            self.edges[key] = w
            if key not in self.edge_age:
                self.edge_age[key] = 0  # new edge
        elif key in self.edges:
            del self.edges[key]
            self.edge_age.pop(key, None)
    
    def get_neighbors(self, node):
        """Get all neighbors of a node with their edge weights."""
        neighbors = []
        for other in self.nodes:
            if other == node:
                continue
            key = self._edge_key(node, other)
            if key in self.edges:
                neighbors.append((other, self.edges[key]))
        return neighbors
    
    def activate_cluster(self, center, radius=2):
        """Activate a cluster of concepts around a center node.
        Simulates a researcher thinking about related ideas."""
        self.activation[center] = 1.0
        visited = {center}
        frontier = [center]
        
        for hop in range(radius):
            new_frontier = []
            decay = 0.5 ** (hop + 1)  # activation decays with distance
            for node in frontier:
                for neighbor, weight in self.get_neighbors(node):
                    if neighbor not in visited:
                        # Stronger connections propagate activation better
                        if self.rng.random() < min(weight * 8 * decay, 0.9):
                            self.activation[neighbor] = decay
                            visited.add(neighbor)
                            new_frontier.append(neighbor)
            frontier = new_frontier
        
        # Also randomly activate a few concepts (cross-paradigm stimulation)
        # This models reading broadly / encountering unexpected connections
        for _ in range(2):
            node = self.rng.choice(self.nodes)
            if node not in visited:
                self.activation[node] = 0.3
                visited.add(node)
    
    def hebbian_reinforce(self, lr=0.04):
        """Strengthen connections between co-activated concepts (Hebbian learning)."""
        active = [n for n in self.nodes if self.activation[n] > 0.1]
        for i in active:
            for j in active:
                if i >= j:
                    continue
                # Strengthen proportional to co-activation
                boost = lr * self.activation[i] * self.activation[j]
                current = self.get_weight(i, j)
                new_w = current + boost
                self.set_weight(i, j, new_w)
                key = self._edge_key(i, j)
                if key in self.edge_age:
                    self.edge_age[key] = 0  # reset age on reinforcement
    
    def preferential_attach(self, p_new=0.04):
        """Add new connections. Mix of preferential (rich-get-richer) and random (curiosity).
        Curiosity: random connections model encountering unexpected ideas.
        Preferential: hubs attract more connections (Matthew effect)."""
        degrees = defaultdict(int)
        for (i, j) in self.edges:
            degrees[i] += 1
            degrees[j] += 1
        
        for i in self.nodes:
            if self.rng.random() < p_new:
                # 60% preferential, 40% random curiosity
                if self.rng.random() < 0.6:
                    # Preferential attachment
                    total_degree = sum(max(degrees[n], 1) for n in self.nodes if n != i)
                    r = self.rng.uniform(0, total_degree)
                    cumulative = 0
                    target = None
                    for n in self.nodes:
                        if n == i:
                            continue
                        cumulative += max(degrees[n], 1)
                        if cumulative >= r:
                            target = n
                            break
                else:
                    # Random curiosity — uniform random target
                    candidates = [n for n in self.nodes if n != i]
                    target = self.rng.choice(candidates) if candidates else None
                
                if target is not None:
                    current = self.get_weight(i, target)
                    if current < 0.001:
                        self.set_weight(i, target, self.rng.uniform(0.01, 0.03))
    
    def prune(self, threshold=0.05, grace_period=3):
        """Remove weak connections. New edges get a grace period before pruning.
        This models the fact that new ideas need time to prove themselves."""
        to_remove = []
        for key, w in self.edges.items():
            age = self.edge_age.get(key, 0)
            # Only prune if edge is old enough AND below threshold
            if w < threshold and age >= grace_period:
                to_remove.append(key)
        for key in to_remove:
            del self.edges[key]
            self.edge_age.pop(key, None)
        return len(to_remove)
    
    def find_paradigms(self):
        """Find connected components — each is a paradigm."""
        visited = set()
        paradigms = []
        
        for start in self.nodes:
            if start in visited:
                continue
            # BFS
            component = []
            queue = [start]
            while queue:
                node = queue.pop(0)
                if node in visited:
                    continue
                visited.add(node)
                component.append(node)
                for neighbor, _ in self.get_neighbors(node):
                    if neighbor not in visited:
                        queue.append(neighbor)
            paradigms.append(component)
        
        # Update paradigm membership
        for pid, members in enumerate(paradigms):
            for node in members:
                self.paradigm[node] = pid
        
        return paradigms
    
    def decay_activations(self, rate=0.7):
        """Decay all activations toward zero."""
        for n in self.nodes:
            self.activation[n] *= rate
    
    def compute_metrics(self):
        """Compute network metrics."""
        n_edges = len(self.edges)
        max_edges = self.n * (self.n - 1) / 2
        density = n_edges / max_edges if max_edges > 0 else 0
        avg_weight = (sum(self.edges.values()) / n_edges) if n_edges > 0 else 0
        paradigms = self.find_paradigms()
        n_paradigms = len(paradigms)
        
        # Modularity: fraction of edges within paradigms vs between
        within = 0
        between = 0
        for (i, j) in self.edges:
            if self.paradigm[i] == self.paradigm[j]:
                within += 1
            else:
                between += 1
        modularity = within / (within + between) if (within + between) > 0 else 0
        
        return {
            "n_paradigms": n_paradigms,
            "n_edges": n_edges,
            "density": density,
            "avg_weight": avg_weight,
            "modularity": modularity,
            "paradigms": paradigms,
        }
    
    def decay_weights(self, rate=0.008):
        """Passive weight decay — unused connections slowly weaken. Age all edges."""
        to_remove = []
        for key in self.edges:
            self.edges[key] -= rate
            self.edge_age[key] = self.edge_age.get(key, 0) + 1
            if self.edges[key] < 0.001:
                to_remove.append(key)
        for key in to_remove:
            del self.edges[key]
            self.edge_age.pop(key, None)
    
    def step_simulate(self, prune_threshold=0.05, prune_interval=5):
        """One step of the simulation."""
        self.step += 1
        
        # Pick a random concept to activate
        center = self.rng.choice(self.nodes)
        self.decay_activations()
        self.activate_cluster(center)
        
        # Hebbian reinforcement
        self.hebbian_reinforce()
        
        # Preferential attachment (stochastic)
        self.preferential_attach()
        
        # Passive weight decay
        self.decay_weights()
        
        # Record pre-prune paradigm state
        old_paradigms = self.find_paradigms()
        old_n = len(old_paradigms)
        
        # Periodic pruning (not every step — gives Hebbian time to build)
        pruned = 0
        if self.step % prune_interval == 0:
            pruned = self.prune(threshold=prune_threshold)
        
        # Record post-prune state
        metrics = self.compute_metrics()
        new_n = metrics["n_paradigms"]
        
        # Detect paradigm shift: number of paradigms changed
        if new_n != old_n:
            # Determine shift type
            largest = max(len(p) for p in metrics["paradigms"])
            self.shift_events.append({
                "step": self.step,
                "type": "fragmentation" if new_n > old_n else "consolidation",
                "old_paradigms": old_n,
                "new_paradigms": new_n,
                "largest_paradigm_size": largest,
                "edges_pruned": pruned,
            })
        
        # Record history
        self.n_paradigms_history.append(metrics["n_paradigms"])
        self.n_edges_history.append(metrics["n_edges"])
        self.avg_weight_history.append(metrics["avg_weight"])
        self.density_history.append(metrics["density"])
        
        return metrics
    
    def simulate(self, steps=100, prune_threshold=0.05, prune_interval=5):
        """Run the full simulation."""
        print("=" * 70)
        print("PARADIGM EMERGENCE SIMULATOR")
        print("=" * 70)
        print(f"\nConcepts: {self.n} | Steps: {steps} | Prune threshold: {prune_threshold} | Prune interval: {prune_interval}")
        print()
        
        # Initial state
        initial = self.compute_metrics()
        print(f"Initial state: {initial['n_edges']} edges, density={initial['density']:.3f}, "
              f"{initial['n_paradigms']} paradigm(s)")
        print()
        
        for s in range(steps):
            metrics = self.step_simulate(prune_threshold=prune_threshold, prune_interval=prune_interval)
        
        # Final state
        final = self.compute_metrics()
        
        # Results
        print("FINAL STATE")
        print("=" * 70)
        print(f"  Edges:       {initial['n_edges']} → {final['n_edges']}")
        print(f"  Density:     {initial['density']:.3f} → {final['density']:.3f}")
        print(f"  Avg weight:  {initial['avg_weight']:.4f} → {final['avg_weight']:.4f}")
        print(f"  Paradigms:   {initial['n_paradigms']} → {final['n_paradigms']}")
        print(f"  Modularity:  {initial['modularity']:.3f} → {final['modularity']:.3f}")
        print()
        
        # Paradigm details
        print("PARADIGM STRUCTURE")
        print("-" * 70)
        for pid, members in enumerate(final["paradigms"]):
            size = len(members)
            # Compute internal density
            internal = 0
            for i in members:
                for j in members:
                    if i < j and self._edge_key(i, j) in self.edges:
                        internal += 1
            max_internal = size * (size - 1) / 2
            internal_density = internal / max_internal if max_internal > 0 else 0
            bar = "█" * int(internal_density * 30) + "░" * (30 - int(internal_density * 30))
            print(f"  Paradigm {pid}: {size:>3} concepts, density=|{bar}| {internal_density:.3f}")
        print()
        
        # Shift timeline
        if self.shift_events:
            print("PARADIGM SHIFTS")
            print("-" * 70)
            for event in self.shift_events[:20]:
                direction = "⬆" if event["type"] == "fragmentation" else "⬇"
                print(f"  Step {event['step']:>3} {direction} {event['type']}: "
                      f"{event['old_paradigms']}→{event['new_paradigms']} paradigms "
                      f"(pruned {event['edges_pruned']} edges, "
                      f"largest={event['largest_paradigm_size']})")
            if len(self.shift_events) > 20:
                print(f"  ... and {len(self.shift_events) - 20} more shifts")
        else:
            print("  No paradigm shifts detected — network remained connected.")
        print()
        
        # Trajectory summary
        print("TRAJECTORY")
        print("-" * 70)
        step = max(1, steps // 20)
        for i in range(0, steps, step):
            paradigms = self.n_paradigms_history[i]
            edges = self.n_edges_history[i]
            density = self.density_history[i]
            bar_p = "█" * paradigms + "░" * (10 - min(paradigms, 10))
            print(f"  Step {i:>3}: paradigms={paradigms} |{bar_p}| "
                  f"edges={edges:>4} density={density:.3f}")
        # Final
        paradigms = self.n_paradigms_history[-1]
        edges = self.n_edges_history[-1]
        density = self.density_history[-1]
        bar_p = "█" * paradigms + "░" * (10 - min(paradigms, 10))
        print(f"  Step {steps:>3}: paradigms={paradigms} |{bar_p}| "
              f"edges={edges:>4} density={density:.3f}")
        print()
        
        # Fragmentation vs consolidation counts
        frag_count = sum(1 for e in self.shift_events if e["type"] == "fragmentation")
        cons_count = sum(1 for e in self.shift_events if e["type"] == "consolidation")
        
        # Key insights
        print("=" * 70)
        print("KEY INSIGHTS")
        print("=" * 70)
        
        if final["n_paradigms"] > 1:
            sizes = [len(p) for p in final["paradigms"]]
            largest = max(sizes)
            total = sum(sizes)
            dominance = largest / total
            print(f"\n✦ PARADIGM DOMINANCE — The largest paradigm contains {dominance:.0%} of concepts.")
            print(f"  This is typical of 'normal science': one dominant paradigm with")
            print(f"  isolated pockets of alternative thinking.")
        
        if frag_count > cons_count:
            print(f"\n✦ FRAGMENTATION BIAS — {frag_count} fragmentations vs {cons_count} consolidations.")
            print("  Pruning creates boundaries faster than Hebbian learning can bridge them.")
            print("  This models the tendency of fields to specialize into subdisciplines.")
        elif cons_count > frag_count:
            print(f"\n✦ CONSOLIDATION BIAS — {cons_count} consolidations vs {frag_count} fragmentations.")
            print("  Hebbian reinforcement bridges gaps faster than pruning creates them.")
            print("  This models the tendency of ideas to merge into unified theories.")
        else:
            print(f"\n✦ BALANCED DYNAMICS — {frag_count} fragmentations, {cons_count} consolidations.")
            print("  Pruning and reinforcement are in approximate equilibrium.")
        
        if final["modularity"] > 0.7:
            print(f"\n✦ HIGH MODULARITY ({final['modularity']:.2f}) — The network is deeply fractured.")
            print("  Concepts within paradigms are densely connected, but paradigms are")
            print("  nearly isolated. Communication between paradigms requires bridging nodes.")
        elif final["modularity"] > 0.4:
            print(f"\n✦ MODERATE MODULARITY ({final['modularity']:.2f}) — Partial paradigm structure.")
            print("  Some concepts bridge paradigm boundaries. These are the 'interdisciplinary'")
            print("  concepts that enable communication across fields.")
        else:
            print(f"\n✦ LOW MODULARITY ({final['modularity']:.2f}) — Network is largely unified.")
            print("  Despite pruning, Hebbian reinforcement maintains a connected core.")
            print("  This is a 'pre-paradigm' state where no clear boundaries have formed.")
        
        print()
        print("KEY INSIGHT: Paradigms emerge from the TENSION between Hebbian reinforcement")
        print("(which unifies) and pruning (which divides). Neither force alone creates")
        print("paradigm structure — it is the dynamic equilibrium that produces the")
        print("clustered, modular structure of knowledge. A paradigm shift occurs when")
        print("pruning severs a critical bridge, fragmenting the dominant paradigm.")
        print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Paradigm Emergence Simulator")
    parser.add_argument("--concepts", type=int, default=40, help="Number of concept nodes")
    parser.add_argument("--steps", type=int, default=100, help="Simulation steps")
    parser.add_argument("--prune-threshold", type=float, default=0.05, 
                        help="Edge weight below which connections are pruned")
    parser.add_argument("--prune-interval", type=int, default=5,
                        help="Prune every N steps (gives Hebbian time to build)")
    parser.add_argument("--regime", choices=["pre-paradigm", "normal-science", "revolution", "fragmented"],
                        default=None,
                        help="Parameter presets: pre-paradigm (high Hebbian, low prune), "
                             "normal-science (balanced), revolution (aggressive prune), "
                             "fragmented (high decay, frequent prune)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()
    
    sim = ConceptNetwork(n_concepts=args.concepts, seed=args.seed)
    
    # Apply regime presets
    if args.regime == "pre-paradigm":
        args.prune_threshold = 0.02
        args.prune_interval = 15
    elif args.regime == "normal-science":
        args.prune_threshold = 0.04
        args.prune_interval = 8
    elif args.regime == "revolution":
        args.prune_threshold = 0.06
        args.prune_interval = 4
    elif args.regime == "fragmented":
        args.prune_threshold = 0.05
        args.prune_interval = 3
    
    sim.simulate(steps=args.steps, prune_threshold=args.prune_threshold, 
                 prune_interval=args.prune_interval)
