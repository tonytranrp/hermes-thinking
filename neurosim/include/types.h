#pragma once
// NeuroSim — Core types and constants
// Zero-overhead abstractions for spiking neural network simulation

#include <cstdint>
#include <chrono>
#include <concepts>
#include <limits>

namespace neurosim {

// --- Time representation ---
using TimeStep = uint64_t;
using TimeMs = double;

constexpr TimeStep INVALID_TIMESTEP = std::numeric_limits<TimeStep>::max();

// --- Neuron identifiers ---
using NeuronId = uint32_t;
using PopulationId = uint32_t;
using SynapseId = uint64_t;

constexpr NeuronId INVALID_NEURON = std::numeric_limits<NeuronId>::max();
constexpr PopulationId INVALID_POP = std::numeric_limits<PopulationId>::max();

// --- Simulation parameters ---
struct SimConfig {
    TimeStep max_steps = 1'000'000;
    double dt = 0.001;              // 1ms timestep
    uint32_t num_threads = 0;       // 0 = auto-detect
    bool enable_simd = true;
    bool enable_prefetch = true;
    bool log_spikes = true;
    bool visualize = false;
    uint32_t viz_refresh_ms = 50;
};

// --- Spike event — the fundamental unit of communication ---
// Cache-line aligned to prevent false sharing between producer/consumer
struct alignas(64) SpikeEvent {
    NeuronId source;
    NeuronId target;
    TimeStep time;
    float weight;
    uint8_t _padding[64 - sizeof(NeuronId)*2 - sizeof(TimeStep) - sizeof(float)];
};

static_assert(sizeof(SpikeEvent) == 64, "SpikeEvent must be exactly one cache line");

// --- Neuron state for SoA layout ---
// Structure of Arrays — much better cache behavior for vectorized updates
struct NeuronStateSoA {
    float* v;        // Membrane potential
    float* u;        // Recovery variable (Izhikevich)
    float* I;        // Input current
    bool*  spiked;   // Did this neuron fire this step?
    NeuronId count;  // Number of neurons in this population

    // Parameters (shared across population for cache efficiency)
    float a, b, c, d;  // Izhikevich parameters
};

// --- Concept for neuron models ---
template<typename T>
concept NeuronModel = requires(T t, float v, float u, float I, float dt) {
    { T::name() } -> std::convertible_to<const char*>;
    { t.step(v, u, I, dt) } -> std::same_as<void>;
    { t.reset(v, u) } -> std::same_as<void>;
    { t.threshold() } -> std::same_as<float>;
};

} // namespace neurosim
