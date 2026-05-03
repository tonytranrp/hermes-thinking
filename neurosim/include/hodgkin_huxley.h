#pragma once
// NeuroSim — Hodgkin-Huxley model with dedicated SoA state
// Full biophysical model with Na+, K+, Leak channels
// 4 ODEs: dV/dt, dm/dt, dh/dt, dn/dt
//
// This version uses separate arrays for each gating variable (n, m, h)
// enabling SIMD vectorization — something most simulators don't bother with.

#include "types.h"
#include <cmath>

namespace neurosim::models {

// ============================================================================
// HH State — Structure of Arrays for vectorized Hodgkin-Huxley
// ============================================================================
struct HHStateSoA {
    float* v;    // Membrane potential (mV)
    float* n;    // K+ activation gate
    float* m;    // Na+ activation gate
    float* h;    // Na+ inactivation gate
    float* I;    // Input current (µA/cm²)
    bool*  spiked;
    NeuronId count;
};

// ============================================================================
// Hodgkin-Huxley (1952) — Vectorized
// ============================================================================
struct HodgkinHuxleySoA {
    float g_Na = 120.0f;   // mS/cm²
    float g_K  = 36.0f;
    float g_L  = 0.3f;
    float E_Na = 50.0f;    // mV
    float E_K  = -77.0f;
    float E_L  = -54.387f;
    float C_m  = 1.0f;     // µF/cm²

    static constexpr const char* name() { return "HodgkinHuxley"; }
    constexpr float threshold() const { return 20.0f; }

    // --- Channel kinetics (all inline for performance) ---
    static inline float alpha_n(float v) {
        float x = v + 55.0f;
        return 0.01f * x / (1.0f - std::exp(-x / 10.0f));
    }
    static inline float beta_n(float v) {
        return 0.125f * std::exp(-(v + 65.0f) / 80.0f);
    }
    static inline float alpha_m(float v) {
        float x = v + 40.0f;
        return 0.1f * x / (1.0f - std::exp(-x / 10.0f));
    }
    static inline float beta_m(float v) {
        return 4.0f * std::exp(-(v + 65.0f) / 18.0f);
    }
    static inline float alpha_h(float v) {
        return 0.07f * std::exp(-(v + 65.0f) / 20.0f);
    }
    static inline float beta_h(float v) {
        return 1.0f / (1.0f + std::exp(-(v + 35.0f) / 10.0f));
    }

    // --- Scalar step ---
    inline void step(float& v, float& n, float& m, float& h, float I, float dt) const {
        // Ionic currents
        float I_Na = g_Na * m * m * m * h * (v - E_Na);
        float I_K  = g_K  * n * n * n * n * (v - E_K);
        float I_L  = g_L  * (v - E_L);

        // dV/dt
        v += (I - I_Na - I_K - I_L) / C_m * dt;

        // Gating variable updates (Euler)
        n += (alpha_n(v) * (1.0f - n) - beta_n(v) * n) * dt;
        m += (alpha_m(v) * (1.0f - m) - beta_m(v) * m) * dt;
        h += (alpha_h(v) * (1.0f - h) - beta_h(v) * h) * dt;

        // Clamp gating variables to [0, 1]
        n = std::max(0.0f, std::min(1.0f, n));
        m = std::max(0.0f, std::min(1.0f, m));
        h = std::max(0.0f, std::min(1.0f, h));
    }

    // --- SoA step: update entire population ---
    inline void step_soa(HHStateSoA& state, float dt) const {
        for (NeuronId i = 0; i < state.count; ++i) {
            step(state.v[i], state.n[i], state.m[i], state.h[i], state.I[i], dt);
            state.spiked[i] = (state.v[i] >= threshold());
        }
    }

    // --- Initialize at resting potential ---
    static void init_resting(HHStateSoA& state) {
        for (NeuronId i = 0; i < state.count; ++i) {
            state.v[i] = -65.0f;
            state.n[i] = alpha_n(-65.0f) / (alpha_n(-65.0f) + beta_n(-65.0f));
            state.m[i] = alpha_m(-65.0f) / (alpha_m(-65.0f) + beta_m(-65.0f));
            state.h[i] = alpha_h(-65.0f) / (alpha_h(-65.0f) + beta_h(-65.0f));
            state.I[i] = 0.0f;
            state.spiked[i] = false;
        }
    }
};

} // namespace neurosim::models
