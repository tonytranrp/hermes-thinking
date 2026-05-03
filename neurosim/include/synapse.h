#pragma once
// NeuroSim — Synapse models
// Static, STDP (Spike-Timing-Dependent Plasticity), and Short-Term Plasticity

#include "types.h"
#include <cmath>

namespace neurosim::synapses {

// ============================================================================
// Static Synapse — fixed weight, no plasticity
// The simplest and fastest synapse type
// ============================================================================
struct StaticSynapse {
    float weight;
    float delay;  // Transmission delay (ms)

    static constexpr const char* name() { return "Static"; }

    inline float deliver(float current_weight) const {
        return weight;
    }

    inline void update(TimeStep pre_time, TimeStep post_time) {
        // No plasticity
    }
};

// ============================================================================
// STDP Synapse — Spike-Timing-Dependent Plasticity
// Hebbian learning: correlated firing strengthens the connection
//
// Δw = A+ * exp(-Δt/τ+)  if pre before post (LTP)
// Δw = -A- * exp(Δt/τ-)  if pre after post (LTD)
//
// This is how real brains learn — timing matters!
// ============================================================================
struct STDPSynapse {
    float weight;
    float delay;
    float w_max = 1.0f;
    float w_min = 0.0f;
    float A_plus = 0.01f;    // LTP amplitude
    float A_minus = 0.012f;  // LTD amplitude (slightly larger → stability)
    float tau_plus = 20.0f;  // LTP time constant (ms)
    float tau_minus = 20.0f; // LTD time constant (ms)

    static constexpr const char* name() { return "STDP"; }

    inline float deliver(float current_weight) const {
        return weight;
    }

    inline void update(TimeStep pre_time, TimeStep post_time) {
        if (pre_time == INVALID_TIMESTEP || post_time == INVALID_TIMESTEP) return;

        double delta_t = static_cast<double>(post_time) - static_cast<double>(pre_time);

        if (delta_t > 0.0) {
            // Pre before post → LTP (strengthen)
            weight += A_plus * std::exp(-delta_t / tau_plus);
        } else if (delta_t < 0.0) {
            // Post before pre → LTD (weaken)
            weight -= A_minus * std::exp(delta_t / tau_minus);
        }

        // Clamp
        weight = std::max(w_min, std::min(w_max, weight));
    }
};

// ============================================================================
// Short-Term Plasticity (Tsodyks-Markram)
// Models synaptic depression and facilitation
// 
// u: utilization of synaptic efficacy (facilitation variable)
// R: fraction of available resources (depression variable)
//
// Every spike: R → R*(1-u), transmit weight*R*u
//              u → u + U*(1-u)  (facilitation)
// Between spikes: R → 1 - (1-R)*exp(-dt/τ_rec)
//                 u → u * exp(-dt/τ_facil)
// ============================================================================
struct STPSynapse {
    float weight;
    float delay;
    float U = 0.5f;          // Utilization parameter
    float tau_rec = 800.0f;  // Recovery time constant (ms)
    float tau_facil = 0.0f;  // Facilitation time constant (ms) — 0 = no facilitation

    // State variables (per-synapse)
    float R = 1.0f;  // Available resources
    float u = 0.0f;  // Utilization

    static constexpr const char* name() { return "STP"; }

    inline float deliver(float) {
        float transmitted = weight * R * u;
        // Update on spike
        R *= (1.0f - u);
        u += U * (1.0f - u);
        return transmitted;
    }

    inline void decay(float dt) {
        R = 1.0f - (1.0f - R) * std::exp(-dt / tau_rec);
        if (tau_facil > 0.0f) {
            u *= std::exp(-dt / tau_facil);
        }
    }
};

} // namespace neurosim::synapses
