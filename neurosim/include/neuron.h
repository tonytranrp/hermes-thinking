#pragma once
// NeuroSim — Neuron models
// Izhikevich, Hodgkin-Huxley, LIF, AdEx
// All models provide a step() that updates membrane potential

#include "types.h"
#include <cmath>
#include <immintrin.h>

namespace neurosim::models {

// ============================================================================
// Izhikevich Model (2003)
// dv/dt = 0.04v² + 5v + 140 - u + I
// du/dt = a(bv - u)
// if v >= 30mV: v = c, u = u + d
//
// 4 parameters (a,b,c,d) produce 20+ distinct firing patterns:
//   Regular spiking:    a=0.02, b=0.2,  c=-65, d=8
//   Bursting:           a=0.02, b=0.2,  c=-50, d=2
//   Chattering:         a=0.02, b=0.2,  c=-55, d=4
//   Fast spiking:       a=0.1,  b=0.2,  c=-65, d=2
//   Low-threshold spik: a=0.02, b=0.25, c=-65, d=2
//   Thalamo-cortical:   a=0.02, b=0.25, c=-65, d=0.05
// ============================================================================
struct Izhikevich {
    float a, b, c, d;
    float v_thresh = 30.0f;

    static constexpr const char* name() { return "Izhikevich"; }
    constexpr float threshold() const { return v_thresh; }

    // --- Scalar step ---
    inline void step(float& v, float& u, float I, float dt) const {
        const float v_sq = v * v;
        const float dv = 0.04f * v_sq + 5.0f * v + 140.0f - u + I;
        const float du = a * (b * v - u);
        v += dv * dt;
        u += du * dt;
        if (v >= v_thresh) {
            v = c;
            u += d;
        }
    }

    // --- AVX2 vectorized step: process 8 neurons at once ---
    #if defined(NEUROSIM_AVX2)
    inline void step_avx2(float* v, float* u, const float* I, float dt, size_t count) const {
        const __m256 ma = _mm256_set1_ps(a);
        const __m256 mb = _mm256_set1_ps(b);
        const __m256 mc = _mm256_set1_ps(c);
        const __m256 md = _mm256_set1_ps(d);
        const __m256 mdt = _mm256_set1_ps(dt);
        const __m256 mthresh = _mm256_set1_ps(v_thresh);
        const __m256 m04 = _mm256_set1_ps(0.04f);
        const __m256 m5 = _mm256_set1_ps(5.0f);
        const __m256 m140 = _mm256_set1_ps(140.0f);

        size_t i = 0;
        for (; i + 8 <= count; i += 8) {
            __m256 mv = _mm256_loadu_ps(v + i);
            __m256 mu = _mm256_loadu_ps(u + i);
            __m256 mI = _mm256_loadu_ps(I + i);

            // dv = 0.04*v² + 5*v + 140 - u + I
            __m256 dv = _mm256_fmadd_ps(m04, _mm256_mul_ps(mv, mv),
                          _mm256_fmadd_ps(m5, mv,
                            _mm256_add_ps(_mm256_sub_ps(m140, mu), mI)));
            // du = a*(b*v - u)
            __m256 du = _mm256_mul_ps(ma, _mm256_sub_ps(_mm256_mul_ps(mb, mv), mu));

            mv = _mm256_fmadd_ps(dv, mdt, mv);
            mu = _mm256_fmadd_ps(du, mdt, mu);

            // Spike detection: where v >= threshold
            __m256 spike_mask = _mm256_cmp_ps(mv, mthresh, _CMP_GE_OQ);
            // Reset spiked neurons: v = c, u = u + d
            mv = _mm256_blendv_ps(mv, mc, spike_mask);
            mu = _mm256_blendv_ps(mu, _mm256_add_ps(mu, md), spike_mask);

            _mm256_storeu_ps(v + i, mv);
            _mm256_storeu_ps(u + i, mu);
        }
        // Scalar tail
        for (; i < count; ++i) {
            step(v[i], u[i], I[i], dt);
        }
    }
    #endif

    constexpr void reset(float& v, float& u) const {
        v = c;
        u = b * c;  // Initial u = b * v at rest
    }

    // --- Preset configurations ---
    static constexpr Izhikevich RegularSpiking()    { return {0.02f, 0.2f, -65.0f, 8.0f}; }
    static constexpr Izhikevich Bursting()           { return {0.02f, 0.2f, -50.0f, 2.0f}; }
    static constexpr Izhikevich Chattering()         { return {0.02f, 0.2f, -55.0f, 4.0f}; }
    static constexpr Izhikevich FastSpiking()        { return {0.1f,  0.2f, -65.0f, 2.0f}; }
    static constexpr Izhikevich LowThresholdSpike()  { return {0.02f, 0.25f,-65.0f, 2.0f}; }
    static constexpr Izhikevich ThalamoCortical()    { return {0.02f, 0.25f,-65.0f, 0.05f}; }
    static constexpr Izhikevich Resonator()          { return {0.1f,  0.26f,-65.0f, 2.0f}; }
};

// ============================================================================
// Leaky Integrate-and-Fire (LIF)
// τm * dv/dt = -(v - v_rest) + R*I
// if v >= v_thresh: v = v_reset, refractory for τ_ref
//
// Simplest model — great for large-scale networks (10M+ neurons)
// ============================================================================
struct LIF {
    float tau_m = 10.0f;       // Membrane time constant (ms)
    float v_rest = -65.0f;     // Resting potential (mV)
    float v_reset = -70.0f;    // Reset potential
    float v_thresh = -55.0f;   // Spike threshold
    float R = 10.0f;           // Membrane resistance (MΩ)
    float tau_ref = 2.0f;      // Refractory period (ms)

    static constexpr const char* name() { return "LIF"; }
    constexpr float threshold() const { return v_thresh; }

    inline void step(float& v, float& u, float I, float dt) const {
        // u is repurposed as refractory countdown
        if (u > 0.0f) {
            u -= dt;
            return;  // In refractory period
        }
        const float decay = dt / tau_m;
        v += decay * (-(v - v_rest) + R * I);
        if (v >= v_thresh) {
            v = v_reset;
            u = tau_ref;
        }
    }

    constexpr void reset(float& v, float& u) const {
        v = v_rest;
        u = 0.0f;
    }
};

// ============================================================================
// Hodgkin-Huxley (1952)
// The classic biophysical model — Na+, K+, Leak channels
// 4 ODEs: dV/dt, dm/dt, dh/dt, dn/dt
//
// Computationally expensive but biologically accurate.
// Used for detailed single-neuron studies.
// ============================================================================
struct HodgkinHuxley {
    // Max conductances (mS/cm²)
    float g_Na = 120.0f;
    float g_K  = 36.0f;
    float g_L  = 0.3f;
    // Reversal potentials (mV)
    float E_Na = 50.0f;
    float E_K  = -77.0f;
    float E_L  = -54.387f;
    // Membrane capacitance (µF/cm²)
    float C_m = 1.0f;

    static constexpr const char* name() { return "Hodgkin-Huxley"; }
    constexpr float threshold() const { return 20.0f; }

    // Channel kinetics
    static inline float alpha_n(float v) { return 0.01f * (v + 55.0f) / (1.0f - std::exp(-(v + 55.0f) / 10.0f)); }
    static inline float beta_n(float v)  { return 0.125f * std::exp(-(v + 65.0f) / 80.0f); }
    static inline float alpha_m(float v) { return 0.1f * (v + 40.0f) / (1.0f - std::exp(-(v + 40.0f) / 10.0f)); }
    static inline float beta_m(float v)  { return 4.0f * std::exp(-(v + 65.0f) / 18.0f); }
    static inline float alpha_h(float v) { return 0.07f * std::exp(-(v + 65.0f) / 20.0f); }
    static inline float beta_h(float v)  { return 1.0f / (1.0f + std::exp(-(v + 35.0f) / 10.0f)); }

    // u is packed as: u.x = n, u.y = m, u.z = h (repurpose for SoA)
    // For SoA: we store n, m, h in separate arrays
    inline void step(float& v, float& gating, float I, float dt) const {
        // gating packed: not ideal — HH needs its own state arrays
        // For now, scalar only
        float n = gating;  // Simplified: HH needs dedicated state
        float m = 0.5f;
        float h = 0.5f;

        // Ionic currents
        float I_Na = g_Na * m * m * m * h * (v - E_Na);
        float I_K  = g_K  * n * n * n * n * (v - E_K);
        float I_L  = g_L  * (v - E_L);

        // dV/dt
        float dv = (I - I_Na - I_K - I_L) / C_m;
        v += dv * dt;

        // Gating variable updates
        float dn = (alpha_n(v) * (1.0f - n) - beta_n(v) * n);
        float dm = (alpha_m(v) * (1.0f - m) - beta_m(v) * m);
        float dh = (alpha_h(v) * (1.0f - h) - beta_h(v) * h);
        n += dn * dt;
        m += dm * dt;
        h += dh * dt;

        gating = n;
    }

    constexpr void reset(float& v, float& u) const {
        v = -65.0f;
        u = alpha_n(-65.0f) / (alpha_n(-65.0f) + beta_n(-65.0f));
    }
};

// ============================================================================
// Adaptive Exponential (AdEx)
// Combines exponential spike mechanism with adaptation
// C*dv/dt = -gL*(v-EL) + gL*ΔT*exp((v-vT)/ΔT) - w + I
// τw*dw/dt = a*(v-EL) - w
// ============================================================================
struct AdEx {
    float C = 281.0f;         // Membrane capacitance (pF)
    float g_L = 30.0f;        // Leak conductance (nS)
    float E_L = -70.6f;       // Leak reversal potential (mV)
    float Delta_T = 2.0f;     // Slope factor (mV)
    float v_T = -50.4f;       // Threshold potential (mV)
    float v_spike = -40.0f;   // Spike detection threshold
    float v_reset = -70.6f;   // Reset potential
    float tau_w = 144.0f;     // Adaptation time constant (ms)
    float a = 4.0f;           // Subthreshold adaptation (nS)
    float b = 80.5f;          // Spike-triggered adaptation (pA)

    static constexpr const char* name() { return "AdEx"; }
    constexpr float threshold() const { return v_spike; }

    inline void step(float& v, float& w, float I, float dt) const {
        // Exponential current
        float exp_term = g_L * Delta_T * std::exp((v - v_T) / Delta_T);
        // dv/dt
        float dv = (-g_L * (v - E_L) + exp_term - w + I) / C;
        // dw/dt
        float dw = (a * (v - E_L) - w) / tau_w;

        v += dv * dt;
        w += dw * dt;

        if (v >= v_spike) {
            v = v_reset;
            w += b;
        }
    }

    constexpr void reset(float& v, float& w) const {
        v = E_L;
        w = 0.0f;
    }
};

} // namespace neurosim::models
