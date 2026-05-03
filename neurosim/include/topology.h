#pragma once
// NeuroSim — Network topology generators
// Small-world (Watts-Strogatz), Scale-free (Barabási-Albert), Random (Erdős-Rényi)
// These generate connection lists that can be fed into Network::connect()

#include "types.h"
#include <vector>
#include <random>
#include <algorithm>
#include <cmath>

namespace neurosim::topology {

struct Edge {
    NeuronId source;
    NeuronId target;
    float weight;
    float delay;
};

// ============================================================================
// Erdős-Rényi random graph — G(n, p)
// Each possible edge exists with probability p
// Classic baseline — not realistic but useful for comparison
// ============================================================================
inline std::vector<Edge> erdos_renyi(NeuronId n, float p,
                                      float weight_mean = 1.0f, float weight_std = 0.3f,
                                      float delay = 1.0f, uint64_t seed = 42) {
    std::mt19937 rng(seed);
    std::uniform_real_distribution<float> prob(0.0f, 1.0f);
    std::normal_distribution<float> w_dist(weight_mean, weight_std);

    std::vector<Edge> edges;
    edges.reserve(static_cast<size_t>(n * n * p * 1.1f));  // Pre-allocate

    for (NeuronId i = 0; i < n; ++i) {
        for (NeuronId j = 0; j < n; ++j) {
            if (i != j && prob(rng) < p) {
                edges.push_back({i, j, std::max(0.0f, w_dist(rng)), delay});
            }
        }
    }
    return edges;
}

// ============================================================================
// Watts-Strogatz small-world network
// Start with ring lattice, then rewire each edge with probability β
//
// Properties: high clustering + short average path length
// This is why "six degrees of separation" works — and why brains are small-world!
//
// Parameters:
//   n: number of neurons
//   k: each node connects to k nearest neighbors in ring (must be even)
//   beta: rewiring probability (0 = ring lattice, 1 = random)
// ============================================================================
inline std::vector<Edge> watts_strogatz(NeuronId n, NeuronId k, float beta,
                                         float weight_mean = 1.0f, float weight_std = 0.3f,
                                         float delay = 1.0f, uint64_t seed = 42) {
    std::mt19937 rng(seed);
    std::uniform_real_distribution<float> prob(0.0f, 1.0f);
    std::uniform_int_distribution<NeuronId> node_dist(0, n - 1);
    std::normal_distribution<float> w_dist(weight_mean, weight_std);

    std::vector<Edge> edges;

    // Start with ring lattice: connect each node to k/2 neighbors on each side
    for (NeuronId i = 0; i < n; ++i) {
        for (NeuronId j_offset = 1; j_offset <= k / 2; ++j_offset) {
            NeuronId j = (i + j_offset) % n;

            // Rewire with probability beta
            if (prob(rng) < beta) {
                NeuronId new_target = node_dist(rng);
                // Avoid self-loops and duplicates
                while (new_target == i) new_target = node_dist(rng);
                j = new_target;
            }

            edges.push_back({i, j, std::max(0.0f, w_dist(rng)), delay});
        }
    }
    return edges;
}

// ============================================================================
// Barabási-Albert scale-free network
// Preferential attachment: "the rich get richer"
// New nodes connect to existing nodes with probability proportional to degree
//
// Properties: power-law degree distribution — few hubs, many leaves
// This is why the internet has Google, brains have hub neurons, and cities have downtowns
//
// Parameters:
//   n: final number of neurons
//   m: each new node makes m connections (m <= m0)
//   m0: initial clique size
// ============================================================================
inline std::vector<Edge> barabasi_albert(NeuronId n, NeuronId m, NeuronId m0,
                                          float weight_mean = 1.0f, float weight_std = 0.3f,
                                          float delay = 1.0f, uint64_t seed = 42) {
    std::mt19937 rng(seed);
    std::normal_distribution<float> w_dist(weight_mean, weight_std);

    std::vector<Edge> edges;
    std::vector<NeuronId> degree(n, 0);  // Degree of each node
    std::vector<NeuronId> repeated_nodes;  // Nodes repeated by degree (for preferential attach)

    // Step 1: Create initial clique of m0 nodes
    for (NeuronId i = 0; i < m0; ++i) {
        for (NeuronId j = i + 1; j < m0; ++j) {
            edges.push_back({i, j, std::max(0.0f, w_dist(rng)), delay});
            edges.push_back({j, i, std::max(0.0f, w_dist(rng)), delay});
            degree[i]++;
            degree[j]++;
            repeated_nodes.push_back(i);
            repeated_nodes.push_back(j);
        }
    }

    // Step 2: Add remaining nodes with preferential attachment
    std::uniform_int_distribution<size_t> pick(0, 0);  // Will be updated
    for (NeuronId new_node = m0; new_node < n; ++new_node) {
        std::uniform_int_distribution<size_t> pick_dist(0, repeated_nodes.size() - 1);

        for (NeuronId conn = 0; conn < m; ++conn) {
            // Pick existing node proportional to degree
            NeuronId target = repeated_nodes[pick_dist(rng)];

            // Avoid self-loops and duplicates
            bool duplicate = false;
            for (const auto& e : edges) {
                if (e.source == new_node && e.target == target) {
                    duplicate = true;
                    break;
                }
            }
            if (duplicate || target == new_node) continue;

            edges.push_back({new_node, target, std::max(0.0f, w_dist(rng)), delay});
            degree[new_node]++;
            degree[target]++;
            repeated_nodes.push_back(new_node);
            repeated_nodes.push_back(target);
        }
    }
    return edges;
}

// ============================================================================
// Spatial network — distance-dependent connectivity
// Neurons on a 2D grid, connection probability falls off with distance
// p(d) = p0 * exp(-d²/(2σ²))
// This is how real cortical connectivity works — nearby neurons connect more
// ============================================================================
inline std::vector<Edge> spatial_2d(NeuronId width, NeuronId height,
                                     float p0 = 0.3f, float sigma = 3.0f,
                                     float weight_mean = 1.0f, float weight_std = 0.3f,
                                     uint64_t seed = 42) {
    const NeuronId n = width * height;
    std::mt19937 rng(seed);
    std::uniform_real_distribution<float> prob(0.0f, 1.0f);
    std::normal_distribution<float> w_dist(weight_mean, weight_std);

    std::vector<Edge> edges;
    const float sigma2 = 2.0f * sigma * sigma;

    for (NeuronId i = 0; i < n; ++i) {
        float xi = static_cast<float>(i % width);
        float yi = static_cast<float>(i / width);

        for (NeuronId j = 0; j < n; ++j) {
            if (i == j) continue;
            float xj = static_cast<float>(j % width);
            float yj = static_cast<float>(j / width);
            float dx = xi - xj;
            float dy = yi - yj;
            float dist2 = dx * dx + dy * dy;

            float p = p0 * std::exp(-dist2 / sigma2);
            if (prob(rng) < p) {
                float delay = 1.0f + std::sqrt(dist2) * 0.5f;  // Delay proportional to distance
                edges.push_back({i, j, std::max(0.0f, w_dist(rng)), delay});
            }
        }
    }
    return edges;
}

} // namespace neurosim::topology
