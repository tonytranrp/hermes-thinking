#!/usr/bin/env python3
"""
Concept Graph Explorer — Simulates how ideas connect and spread.

Models concepts as nodes in a graph with weighted edges (associations).
Simulates graph growth through exploration, showing how path dependence
shapes what thoughts are reachable.

Based on "The Topology of Ideas" conversation in The Infinite Library.

Usage:
    python3 concept_graph_explorer.py
    python3 concept_graph_explorer.py --nodes 30 --steps 50
"""

import random
import math
import argparse
from collections import defaultdict, deque


class ConceptGraph:
    """A graph where nodes are concepts and edges are associations."""
    
    def __init__(self, seed=42):
        self.rng = random.Random(seed)
        self.nodes = set()
        self.edges = {}  # (a, b) -> weight
        self.node_created_at = {}  # node -> step when created
        self.step = 0
    
    def add_node(self, name: str):
        """Add a concept node."""
        if name not in self.nodes:
            self.nodes.add(name)
            self.node_created_at[name] = self.step
    
    def add_edge(self, a: str, b: str, weight: float = 1.0):
        """Add an association edge between two concepts."""
        if a not in self.nodes:
            self.add_node(a)
        if b not in self.nodes:
            self.add_node(b)
        key = tuple(sorted([a, b]))
        self.edges[key] = min(weight + self.edges.get(key, 0), 5.0)  # cap at 5
    
    def get_neighbors(self, node: str) -> list:
        """Get all concepts connected to a given concept."""
        neighbors = []
        for (a, b), weight in self.edges.items():
            if a == node:
                neighbors.append((b, weight))
            elif b == node:
                neighbors.append((a, weight))
        return sorted(neighbors, key=lambda x: -x[1])
    
    def shortest_path(self, start: str, end: str) -> list:
        """BFS shortest path between two concepts."""
        if start == end:
            return [start]
        if start not in self.nodes or end not in self.nodes:
            return []
        
        visited = {start}
        queue = deque([(start, [start])])
        
        while queue:
            current, path = queue.popleft()
            for neighbor, _ in self.get_neighbors(current):
                if neighbor == end:
                    return path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return []  # no path
    
    def clusters(self) -> list:
        """Find connected components (idea clusters)."""
        visited = set()
        clusters = []
        
        for node in self.nodes:
            if node in visited:
                continue
            cluster = set()
            queue = deque([node])
            while queue:
                current = queue.popleft()
                if current in cluster:
                    continue
                cluster.add(current)
                for neighbor, _ in self.get_neighbors(current):
                    if neighbor not in cluster:
                        queue.append(neighbor)
            visited.update(cluster)
            clusters.append(cluster)
        
        return sorted(clusters, key=len, reverse=True)
    
    def hub_nodes(self, top_n=5) -> list:
        """Find the most connected concepts (hubs)."""
        degrees = defaultdict(int)
        for (a, b), weight in self.edges.items():
            degrees[a] += 1
            degrees[b] += 1
        return sorted(degrees.items(), key=lambda x: -x[1])[:top_n]
    
    def bridge_edges(self) -> list:
        """Find edges that connect different clusters."""
        cluster_list = self.clusters()
        if len(cluster_list) <= 1:
            return []
        
        node_to_cluster = {}
        for i, cluster in enumerate(cluster_list):
            for node in cluster:
                node_to_cluster[node] = i
        
        bridges = []
        for (a, b), weight in self.edges.items():
            if node_to_cluster.get(a) != node_to_cluster.get(b):
                bridges.append((a, b, weight))
        return bridges


def grow_graph_sequential(n_seeds=8, n_steps=30, seed=42):
    """Grow a concept graph sequentially, showing path dependence."""
    rng = random.Random(seed)
    graph = ConceptGraph(seed=seed)
    
    # Seed concepts — different domains
    domains = {
        "physics": ["mass", "force", "energy", "momentum", "gravity"],
        "biology": ["cell", "gene", "evolution", "protein", "species"],
        "math": ["function", "set", "proof", "theorem", "infinity"],
        "art": ["color", "rhythm", "harmony", "composition", "texture"],
        "philosophy": ["truth", "meaning", "ethics", "consciousness", "being"],
        "computer_science": ["algorithm", "data", "complexity", "recursion", "abstraction"],
        "psychology": ["perception", "memory", "emotion", "motivation", "cognition"],
        "economics": ["market", "value", "trade", "scarcity", "incentive"],
    }
    
    domain_names = list(domains.keys())
    
    # Add seed concepts
    for domain, concepts in domains.items():
        for concept in concepts:
            graph.add_node(concept)
        # Wire edges within domain
        for i in range(len(concepts) - 1):
            weight = rng.uniform(1.5, 3.0)
            graph.add_edge(concepts[i], concepts[i + 1], weight)
    
    # Add some intra-domain edges
    for domain, concepts in domains.items():
        for _ in range(2):
            a, b = rng.sample(concepts, 2)
            graph.add_edge(a, b, rng.uniform(0.5, 1.5))
    
    print("=" * 70)
    print("CONCEPT GRAPH EXPLORER — Topology of Ideas")
    print("=" * 70)
    print(f"\nInitial graph: {len(graph.nodes)} concepts, {len(graph.edges)} edges")
    print(f"Domains: {', '.join(domain_names)}")
    print()
    
    # Show initial clusters
    initial_clusters = graph.clusters()
    print(f"Initial clusters: {len(initial_clusters)}")
    for i, cluster in enumerate(initial_clusters):
        # Identify domain
        domain_name = "unknown"
        for d, concepts in domains.items():
            if cluster & set(concepts):
                domain_name = d
                break
        print(f"  Cluster {i + 1}: {domain_name} ({len(cluster)} concepts)")
    print()
    
    # Simulate exploration: add cross-domain edges one at a time
    print("EXPLORATION SEQUENCE (adding cross-domain connections)")
    print("-" * 70)
    
    discoveries = []
    for step in range(n_steps):
        graph.step = step + 1
        
        # Pick two different domains
        d1, d2 = rng.sample(domain_names, 2)
        c1 = rng.choice(domains[d1])
        c2 = rng.choice(domains[d2])
        
        # Weight by proximity in current graph
        path = graph.shortest_path(c1, c2)
        if path:
            path_len = len(path)
            weight = max(0.3, 3.0 / path_len)  # shorter path → stronger connection
        else:
            weight = rng.uniform(0.2, 0.8)  # no existing path → weak connection
        
        graph.add_edge(c1, c2, weight)
        
        # Check if clusters merged
        new_clusters = graph.clusters()
        merged = len(new_clusters) < len(initial_clusters)
        
        discoveries.append({
            "step": step + 1,
            "from": c1,
            "to": c2,
            "from_domain": d1,
            "to_domain": d2,
            "weight": weight,
            "merged": merged,
            "n_clusters": len(new_clusters),
        })
        
        if step < 15 or step % 5 == 0:
            merge_str = " ✦ CLUSTER MERGE" if merged else ""
            print(f"  Step {step + 1:>2}: {c1} ({d1}) ↔ {c2} ({d2}) "
                  f"w={weight:.2f}{merge_str}")
        
        initial_clusters = new_clusters
    
    print()
    
    # Final analysis
    print("=" * 70)
    print("FINAL GRAPH TOPOLOGY")
    print("=" * 70)
    print(f"\nNodes: {len(graph.nodes)} | Edges: {len(graph.edges)}")
    
    final_clusters = graph.clusters()
    print(f"Clusters: {len(final_clusters)}")
    for i, cluster in enumerate(final_clusters):
        print(f"  Cluster {i + 1}: {len(cluster)} concepts — {sorted(cluster)[:5]}...")
    print()
    
    # Hub nodes
    print("HUB CONCEPTS (most connected):")
    print("-" * 70)
    for node, degree in graph.hub_nodes(top_n=10):
        neighbors = graph.get_neighbors(node)
        top_neighbors = [n for n, w in neighbors[:3]]
        bar = "█" * min(degree, 20) + "░" * max(0, 20 - degree)
        print(f"  {node:>15}: {bar} degree={degree} → {', '.join(top_neighbors)}")
    print()
    
    # Path examples — how far apart are concepts from different domains?
    print("CONCEPT DISTANCES (cross-domain paths):")
    print("-" * 70)
    test_pairs = [
        ("mass", "evolution"),
        ("theorem", "rhythm"),
        ("algorithm", "consciousness"),
        ("market", "cell"),
        ("truth", "complexity"),
    ]
    for a, b in test_pairs:
        path = graph.shortest_path(a, b)
        if path:
            path_str = " → ".join(path)
            print(f"  {a} → {b}: {len(path) - 1} hops — {path_str}")
        else:
            print(f"  {a} → {b}: NO PATH (disconnected)")
    print()
    
    # Network effect
    print("=" * 70)
    print("THE NETWORK EFFECT OF COGNITION")
    print("-" * 70)
    total_possible_edges = len(graph.nodes) * (len(graph.nodes) - 1) / 2
    actual_edges = len(graph.edges)
    density = actual_edges / total_possible_edges if total_possible_edges > 0 else 0
    print(f"  Actual edges: {actual_edges}")
    print(f"  Possible edges: {total_possible_edges:.0f}")
    print(f"  Graph density: {density:.1%}")
    print(f"  Cross-domain edges: {sum(1 for d in discoveries if d['from_domain'] != d['to_domain'])}")
    print()
    
    if len(final_clusters) == 1:
        print("✦ FULLY CONNECTED — All concepts are reachable from all others.")
        print("  The graph has become a single connected component through exploration.")
        print("  This is the network effect: cross-domain connections create bridges")
        print("  that make previously unreachable concepts reachable.")
    elif len(final_clusters) <= 3:
        print(f"✦ PARTIALLY CONNECTED — {len(final_clusters)} clusters remain.")
        print("  Some concept domains are still isolated. More exploration needed.")
    else:
        print(f"✦ DISCONNECTED — {len(final_clusters)} separate clusters.")
        print("  Most domains are isolated. The network effect hasn't kicked in yet.")
    
    print()
    print("KEY INSIGHT: The topology of ideas is path-dependent. The order in")
    print("which cross-domain connections are made determines which concepts")
    print("become hubs and which remain isolated. Early connections reshape the")
    print("graph and make some later connections easier to discover. Creativity")
    print("is not just making connections — it's making the RIGHT connections")
    print("at the RIGHT time to reshape the topology of what can be thought.")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Concept Graph Explorer")
    parser.add_argument("--nodes", type=int, default=40, help="Approximate number of concept nodes")
    parser.add_argument("--steps", type=int, default=30, help="Exploration steps")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()
    
    grow_graph_sequential(n_steps=args.steps, seed=args.seed)
