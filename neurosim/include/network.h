#pragma once
// NeuroSim — Network: topology, population management, simulation loop

#include "types.h"
#include "neuron.h"
#include "allocator.h"
#include "scheduler.h"
#include "synapse.h"
#include <vector>
#include <unordered_map>
#include <random>
#include <algorithm>
#include <numeric>
#include <iostream>
#include <iomanip>
#include <fstream>

namespace neurosim {

// ============================================================================
// Connection — links two neurons with a synapse
// ============================================================================
struct Connection {
    NeuronId pre;
    NeuronId post;
    float weight;
    float delay;         // in timesteps
    synapses::STDPSynapse synapse;  // Using STDP by default
};

// ============================================================================
// Population — a group of neurons sharing the same model and parameters
// ============================================================================
struct Population {
    PopulationId id;
    NeuronStateSoA state;
    models::Izhikevich model;  // Currently using Izhikevich
    std::string name;
};

// ============================================================================
// Network — the main simulation object
// ============================================================================
class Network {
public:
    explicit Network(const SimConfig& config = {})
        : config_(config), pool_(), scheduler_(config.num_threads)
    {}

    // --- Build the network ---

    PopulationId add_population(const std::string& name, NeuronId count,
                                 const models::Izhikevich& model) {
        PopulationId id = static_cast<PopulationId>(populations_.size());
        SoAAllocator alloc(count);
        auto state = alloc.allocate(pool_, model.a, model.b, model.c, model.d);

        // Initialize membrane potentials with slight random variation
        std::mt19937 rng(42 + id);
        std::normal_distribution<float> v_dist(model.c, 5.0f);
        for (NeuronId i = 0; i < count; ++i) {
            state.v[i] = v_dist(rng);
            state.u[i] = model.b * state.v[i];
            state.I[i] = 0.0f;
            state.spiked[i] = false;
        }

        populations_.push_back({id, state, model, name});
        return id;
    }

    void connect(PopulationId pre, PopulationId post,
                 float probability = 0.1f, float weight_mean = 1.0f,
                 float weight_std = 0.3f, float delay = 1.0f,
                 bool stdp = true) {
        std::mt19937 rng(123 + pre * 100 + post);
        std::uniform_real_distribution<float> prob_dist(0.0f, 1.0f);
        std::normal_distribution<float> w_dist(weight_mean, weight_std);

        auto& pre_pop = populations_[pre];
        auto& post_pop = populations_[post];

        for (NeuronId i = 0; i < pre_pop.state.count; ++i) {
            for (NeuronId j = 0; j < post_pop.state.count; ++j) {
                if (prob_dist(rng) < probability) {
                    Connection conn;
                    conn.pre = i + global_offset(pre);
                    conn.post = j + global_offset(post);
                    conn.weight = std::max(0.0f, w_dist(rng));
                    conn.delay = delay;
                    if (stdp) {
                        conn.synapse = synapses::STDPSynapse{
                            conn.weight, delay, 1.0f, 0.0f,
                            0.01f, 0.012f, 20.0f, 20.0f
                        };
                    } else {
                        conn.synapse = synapses::STDPSynapse{conn.weight, delay};
                        // Using STDPSynapse but won't call update()
                    }
                    connections_.push_back(conn);
                }
            }
        }
    }

    // --- Run simulation ---
    void run() {
        std::cout << "╔══════════════════════════════════════════╗\n";
        std::cout << "║        NeuroSim v0.1.0 — Spiking!       ║\n";
        std::cout << "╠══════════════════════════════════════════╣\n";
        std::cout << "║ Populations: " << std::setw(4) << populations_.size() << "                        ║\n";
        std::cout << "║ Total neurons: " << std::setw(6) << total_neurons() << "                    ║\n";
        std::cout << "║ Connections: " << std::setw(8) << connections_.size() << "                  ║\n";
        std::cout << "║ Threads: " << std::setw(3) << scheduler_.num_threads() << "                          ║\n";
        std::cout << "║ Steps: " << std::setw(8) << config_.max_steps << "                    ║\n";
        std::cout << "╚══════════════════════════════════════════╝\n\n";

        // Open spike log
        std::ofstream spike_log;
        if (config_.log_spikes) {
            spike_log.open("spikes.csv");
            spike_log << "time,neuron_id\n";
        }

        // Start scheduler
        scheduler_.start();

        auto sim_start = std::chrono::high_resolution_clock::now();
        uint64_t total_spikes = 0;

        for (TimeStep t = 0; t < config_.max_steps; ++t) {
            // 1. Inject background current (Poisson input)
            inject_currents(t);

            // 2. Update all neurons (parallel across populations)
            update_neurons(t);

            // 3. Propagate spikes through synapses
            total_spikes += propagate_spikes(t);

            // 4. Log spikes
            if (config_.log_spikes) {
                for (auto& pop : populations_) {
                    for (NeuronId i = 0; i < pop.state.count; ++i) {
                        if (pop.state.spiked[i]) {
                            spike_log << t << "," << (i + global_offset(pop.id)) << "\n";
                        }
                    }
                }
            }

            // 5. ASCII visualization every N steps
            if (config_.visualize && t % 50 == 0) {
                render_ascii(t);
            }

            // 6. Progress report
            if (t > 0 && t % 10000 == 0) {
                auto now = std::chrono::high_resolution_clock::now();
                double elapsed = std::chrono::duration<double>(now - sim_start).count();
                double steps_per_sec = t / elapsed;
                std::cout << "[Step " << t << "/" << config_.max_steps
                          << " | " << std::fixed << std::setprecision(0)
                          << steps_per_sec << " steps/s"
                          << " | " << total_spikes << " spikes]\n";
            }
        }

        auto sim_end = std::chrono::high_resolution_clock::now();
        double total_time = std::chrono::duration<double>(sim_end - sim_start).count();

        std::cout << "\n✓ Simulation complete!\n";
        std::cout << "  Time: " << std::fixed << std::setprecision(3) << total_time << "s\n";
        std::cout << "  Steps/s: " << std::setprecision(0) << config_.max_steps / total_time << "\n";
        std::cout << "  Total spikes: " << total_spikes << "\n";
        std::cout << "  Avg firing rate: " << std::setprecision(2)
                  << (double)total_spikes / total_neurons() / (config_.max_steps * config_.dt) * 1000.0
                  << " Hz\n";

        scheduler_.stop();
    }

private:
    NeuronId total_neurons() const {
        NeuronId total = 0;
        for (const auto& p : populations_) total += p.state.count;
        return total;
    }

    NeuronId global_offset(PopulationId pid) const {
        NeuronId offset = 0;
        for (PopulationId i = 0; i < pid; ++i) {
            offset += populations_[i].state.count;
        }
        return offset;
    }

    void inject_currents(TimeStep t) {
        // Poisson background input — each neuron gets random thalamic input
        thread_local std::mt19937 rng(t);
        std::poisson_distribution<int> poisson(5);  // 5Hz background rate
        for (auto& pop : populations_) {
            for (NeuronId i = 0; i < pop.state.count; ++i) {
                pop.state.I[i] = static_cast<float>(poisson(rng)) * 0.5f;
            }
        }
    }

    void update_neurons(TimeStep t) {
        const float dt = static_cast<float>(config_.dt);

        for (auto& pop : populations_) {
            auto& state = pop.state;
            auto& model = pop.model;

            #if defined(NEUROSIM_AVX2)
            if (config_.enable_simd) {
                model.step_avx2(state.v, state.u, state.I, dt, state.count);
            } else
            #endif
            {
                // Scalar fallback
                for (NeuronId i = 0; i < state.count; ++i) {
                    model.step(state.v[i], state.u[i], state.I[i], dt);
                }
            }

            // Detect spikes (v was reset to c if it fired)
            for (NeuronId i = 0; i < state.count; ++i) {
                state.spiked[i] = (state.v[i] == model.c);
            }

            // Reset input current for next step
            for (NeuronId i = 0; i < state.count; ++i) {
                state.I[i] = 0.0f;
            }
        }
    }

    uint64_t propagate_spikes(TimeStep t) {
        uint64_t spike_count = 0;
        for (auto& conn : connections_) {
            // Find source population and check if it spiked
            // (Simplified — full version uses delayed spike queues)
            PopulationId pre_pop = find_population(conn.pre);
            PopulationId post_pop = find_population(conn.post);

            if (pre_pop == INVALID_POP || post_pop == INVALID_POP) continue;

            NeuronId pre_local = conn.pre - global_offset(pre_pop);
            NeuronId post_local = conn.post - global_offset(post_pop);

            if (populations_[pre_pop].state.spiked[pre_local]) {
                populations_[post_pop].state.I[post_local] += conn.weight;
                spike_count++;

                // STDP update
                conn.synapse.update(t, t);
                conn.weight = conn.synapse.weight;
            }
        }
        return spike_count;
    }

    PopulationId find_population(NeuronId global_id) const {
        NeuronId offset = 0;
        for (PopulationId i = 0; i < populations_.size(); ++i) {
            if (global_id < offset + populations_[i].state.count) return i;
            offset += populations_[i].state.count;
        }
        return INVALID_POP;
    }

    void render_ascii(TimeStep t) {
        // Simple ASCII raster of population activity
        std::cout << "\n  t=" << t << " | ";
        for (const auto& pop : populations_) {
            for (NeuronId i = 0; i < std::min(pop.state.count, NeuronId(80)); ++i) {
                std::cout << (pop.state.spiked[i] ? "█" : "·");
            }
            std::cout << " │ ";
        }
        std::cout << "\n";
    }

    SimConfig config_;
    AlignedPool pool_;
    Scheduler scheduler_;
    std::vector<Population> populations_;
    std::vector<Connection> connections_;
};

} // namespace neurosim
