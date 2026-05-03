#pragma once
// NeuroSim — Advanced plasticity rules
// Triplet STDP, Reward-modulated STDP (3-factor), BCM rule
// These go beyond simple pair-based STDP to enable richer learning

#include "types.h"
#include <cmath>
#include <algorithm>

namespace neurosim::plasticity {

// ============================================================================
// Triplet STDP (Pfister & Gerstner 2006)
// Pair-based STDP only considers the last pre-post pair. But real synapses
// remember the recent history — the SECOND-to-last spike matters too.
// This produces phenomena that pair-based STDP cannot:
//   - Frequency dependence of LTP/LTD
//   - Spike-pairing order effects beyond nearest-neighbor
//   - Visual cortex-like orientation selectivity
//
// Uses two traces per neuron (fast + slow) instead of one:
//   r1 (fast pre trace), r2 (slow pre trace)
//   o1 (fast post trace), o2 (slow post trace)
// ============================================================================
struct TripletSTDP {
    float weight;
    float w_max = 1.0f;
    float w_min = 0.0f;

    // Time constants (ms)
    float tau_r1 = 16.8f;   // Fast pre trace
    float tau_r2 = 101.0f;  // Slow pre trace
    float tau_o1 = 33.7f;   // Fast post trace
    float tau_o2 = 125.0f;  // Slow post trace

    // Amplitudes
    float A2_plus = 0.0005f;   // Pair LTP
    float A2_minus = 0.0005f;  // Pair LTD
    float A3_plus = 0.0065f;   // Triplet LTP
    float A3_minus = 0.0065f;  // Triplet LTD

    // Per-synapse traces
    float r1 = 0.0f, r2 = 0.0f;  // Pre-synaptic traces
    float o1 = 0.0f, o2 = 0.0f;  // Post-synaptic traces

    static constexpr const char* name() { return "TripletSTDP"; }

    // Called on pre-synaptic spike
    inline void on_pre_spike(float dt) {
        // LTD: weight decreases proportional to post traces
        weight -= o1 * (A2_minus + A3_minus * o2);
        weight = std::max(w_min, std::min(w_max, weight));

        // Update pre traces
        r1 += 1.0f;
        r2 += 1.0f;
    }

    // Called on post-synaptic spike
    inline void on_post_spike(float dt) {
        // LTP: weight increases proportional to pre traces
        weight += r1 * (A2_plus + A3_plus * r2);
        weight = std::max(w_min, std::min(w_max, weight));

        // Update post traces
        o1 += 1.0f;
        o2 += 1.0f;
    }

    // Decay traces between spikes
    inline void decay(float dt_ms) {
        r1 *= std::exp(-dt_ms / tau_r1);
        r2 *= std::exp(-dt_ms / tau_r2);
        o1 *= std::exp(-dt_ms / tau_o1);
        o2 *= std::exp(-dt_ms / tau_o2);
    }
};

// ============================================================================
// Reward-Modulated STDP (3-factor learning)
// dopamine signal modulates plasticity
//
// Δw = dopamine(t) × STDP(pre, post)
//
// Without reward, STDP changes are neutralized by opposing LTD/LTP.
// When dopamine arrives, it unlocks the STDP changes — the synapse
// "votes" and the reward "decides whether to count the vote."
//
// This is how reinforcement learning works in the basal ganglia:
// dopamine from the substantia nigra signals reward prediction error.
// ============================================================================
struct RewardModulatedSTDP {
    float weight;
    float w_max = 1.0f;
    float w_min = 0.0f;

    // STDP parameters
    float A_plus = 0.01f;
    float A_minus = 0.012f;
    float tau_plus = 20.0f;
    float tau_minus = 20.0f;

    // Reward modulation
    float dopamine = 0.0f;           // Current dopamine level
    float tau_dopamine = 200.0f;     // Dopamine decay time constant
    float dopamine_baseline = 0.0f;  // Baseline (0 = only reward above baseline enables plasticity)

    // Eligibility trace — the "vote" that dopamine gates
    float eligibility = 0.0f;
    float tau_eligibility = 1000.0f;  // Eligibility decay

    // STDP traces
    float pre_trace = 0.0f;
    float post_trace = 0.0f;

    static constexpr const char* name() { return "RewardModulatedSTDP"; }

    inline void on_pre_spike() {
        // LTD contribution to eligibility
        eligibility -= A_minus * post_trace;
        pre_trace += 1.0f;
    }

    inline void on_post_spike() {
        // LTP contribution to eligibility
        eligibility += A_plus * pre_trace;
        post_trace += 1.0f;
    }

    inline void inject_dopamine(float amount) {
        dopamine += amount;
    }

    // Called every timestep
    inline void step(float dt_ms) {
        // Apply reward-modulated weight change
        if (dopamine > dopamine_baseline) {
            weight += dopamine * eligibility * dt_ms * 0.001f;
            weight = std::max(w_min, std::min(w_max, weight));
        }

        // Decay traces
        pre_trace *= std::exp(-dt_ms / tau_plus);
        post_trace *= std::exp(-dt_ms / tau_minus);
        eligibility *= std::exp(-dt_ms / tau_eligibility);
        dopamine *= std::exp(-dt_ms / tau_dopamine);
    }
};

// ============================================================================
// BCM Rule (Bienenstock-Cooper-Munro, 1982)
// Rate-based plasticity with a sliding threshold
//
// dw/dt = η × v × (v - θ_M) × I
//
// v: post-synaptic firing rate
// θ_M: sliding modification threshold = <v²> (time-averaged)
// I: pre-synaptic input
//
// Key insight: synapses weaken when post is below threshold (LTD),
// strengthen when above (LTP), and the threshold SLIDES to maintain stability.
// This produces experience-dependent selectivity — neurons become tuned
// to specific patterns (e.g., orientation selectivity in visual cortex).
// ============================================================================
struct BCMSynapse {
    float weight;
    float w_max = 1.0f;
    float w_min = 0.0f;

    float eta = 0.001f;           // Learning rate
    float tau_threshold = 10000.0f; // Threshold sliding time constant (ms)

    float post_rate = 0.0f;       // Smoothed post-synaptic firing rate
    float threshold = 0.1f;       // Modification threshold θ_M

    static constexpr const char* name() { return "BCM"; }

    inline void on_post_spike(float dt_ms) {
        // Update post-synaptic rate estimate (exponential moving average)
        post_rate += (1.0f - post_rate) * dt_ms / 100.0f;  // 100ms averaging window
    }

    inline void on_pre_spike(float input_current) {
        // BCM weight update
        float dw = eta * post_rate * (post_rate - threshold) * input_current;
        weight += dw;
        weight = std::max(w_min, std::min(w_max, weight));
    }

    inline void step(float dt_ms) {
        // Sliding threshold: θ_M → <v²> over long timescale
        float target_threshold = post_rate * post_rate;
        threshold += (target_threshold - threshold) * dt_ms / tau_threshold;

        // Decay post rate (between spikes)
        post_rate *= std::exp(-dt_ms / 100.0f);
    }
};

} // namespace neurosim::plasticity
