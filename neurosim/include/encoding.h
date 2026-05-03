#pragma once
// NeuroSim — Spike encoders
// Convert real-world signals (images, audio, time series) into spike trains
// This is the input side of neuromorphic computing

#include "types.h"
#include <vector>
#include <cmath>
#include <algorithm>
#include <random>

namespace neurosim::encoding {

// ============================================================================
// PoissonEncoder — rate coding via Poisson process
// Each input pixel/value becomes a Poisson spike train
// Rate ∝ input intensity
//
// Simple but effective. Used in most SNN benchmarks.
// Problem: loses temporal information — a 50Hz signal and a 50Hz signal
// with different timing patterns look the same.
// ============================================================================
class PoissonEncoder {
public:
    // Encode a vector of values [0, 1] into spike trains over `duration_ms`
    static std::vector<std::vector<TimeStep>> encode(
        const std::vector<float>& input,
        float max_rate_hz = 100.0f,
        float dt_ms = 1.0f,
        TimeStep duration_steps = 100,
        uint64_t seed = 42
    ) {
        std::mt19937 rng(seed);
        std::uniform_real_distribution<float> dist(0.0f, 1.0f);

        std::vector<std::vector<TimeStep>> spikes(input.size());

        for (size_t i = 0; i < input.size(); ++i) {
            float rate = input[i] * max_rate_hz;
            float prob_per_step = rate * dt_ms / 1000.0f;

            for (TimeStep t = 0; t < duration_steps; ++t) {
                if (dist(rng) < prob_per_step) {
                    spikes[i].push_back(t);
                }
            }
        }
        return spikes;
    }
};

// ============================================================================
// TemporalEncoder — latency coding
// Brighter pixels → earlier spikes
// This preserves temporal information that rate coding loses
//
// t_spike = T_max × (1 - intensity)
// A pixel at intensity 1.0 spikes immediately
// A pixel at intensity 0.0 never spikes
// ============================================================================
class TemporalEncoder {
public:
    static std::vector<std::vector<TimeStep>> encode(
        const std::vector<float>& input,
        TimeStep max_latency = 100,
        float threshold = 0.01f
    ) {
        std::vector<std::vector<TimeStep>> spikes(input.size());

        for (size_t i = 0; i < input.size(); ++i) {
            if (input[i] > threshold) {
                TimeStep spike_time = static_cast<TimeStep>(
                    max_latency * (1.0f - input[i])
                );
                spikes[i].push_back(spike_time);
            }
        }
        return spikes;
    }
};

// ============================================================================
// BSAEncoder — Ben's Spike Algorithm
// Signal reconstruction from spikes — ensures the spike train can
// reconstruct the original signal via convolution with a kernel
//
// This is the gold standard for audio spike encoding because it
// preserves the waveform shape, not just the envelope.
// ============================================================================
class BSAEncoder {
public:
    static std::vector<TimeStep> encode(
        const std::vector<float>& signal,
        const std::vector<float>& kernel,  // Typically [1, 0.8, 0.6, 0.4, 0.2]
        float threshold = 1.0f,
        float dt_ms = 1.0f
    ) {
        std::vector<TimeStep> spikes;
        std::vector<float> reconstructed(signal.size(), 0.0f);
        int kernel_len = static_cast<int>(kernel.size());

        for (size_t t = 0; t < signal.size(); ++t) {
            // Error without spike
            float error_no_spike = 0.0f;
            float error_with_spike = 0.0f;

            for (int k = 0; k < kernel_len && (t + k) < signal.size(); ++k) {
                float diff_no = std::abs(signal[t + k] - reconstructed[t + k]);
                float diff_yes = std::abs(signal[t + k] - (reconstructed[t + k] + kernel[k]));
                error_no_spike += diff_no;
                error_with_spike += diff_yes;
            }

            // Spike if it reduces reconstruction error
            if (error_with_spike < error_no_spike - threshold) {
                spikes.push_back(static_cast<TimeStep>(t));
                for (int k = 0; k < kernel_len && (t + k) < signal.size(); ++k) {
                    reconstructed[t + k] += kernel[k];
                }
            }
        }
        return spikes;
    }
};

// ============================================================================
// CochlearEncoder — model of the human cochlea
// Splits audio into frequency bands via gammatone filterbank
// Each band produces a spike train (phase-locking at low frequencies)
//
// This is how your ear works: the basilar membrane vibrates at
// different positions for different frequencies, and each position
// sends spikes to the brain. We're literally simulating hearing.
// ============================================================================
class CochlearEncoder {
public:
    struct Config {
        int num_channels = 64;      // Number of frequency channels
        float low_freq_hz = 20.0f;  // Lowest frequency
        float high_freq_hz = 20000.0f; // Highest frequency
        float max_rate_hz = 200.0f;
    };

    // Generate Equivalent Rectangular Bandwidth (ERB) spaced frequencies
    // The cochlea has approximately logarithmic frequency resolution
    static std::vector<float> erb_frequencies(int num_channels, float low, float high) {
        // ERB-rate scale (Moore & Glasberg 1983)
        auto erb = [](float f) { return 24.7f * (4.37f * f / 1000.0f + 1.0f); };
        float erb_low = erb(low);
        float erb_high = erb(high);

        std::vector<float> frequencies(num_channels);
        for (int i = 0; i < num_channels; ++i) {
            float frac = static_cast<float>(i) / (num_channels - 1);
            float erb_rate = erb_low + frac * (erb_high - erb_low);
            // Inverse ERB
            frequencies[i] = (erb_rate / 24.7f - 1.0f) / 4.37f * 1000.0f;
        }
        return frequencies;
    }

    // Encode audio signal into multi-channel spike trains
    static std::vector<std::vector<TimeStep>> encode(
        const std::vector<float>& audio,
        const Config& config = {},
        float dt_ms = 0.025f,  // 40kHz sample rate equivalent
        uint64_t seed = 42
    ) {
        auto frequencies = erb_frequencies(config.num_channels, config.low_freq_hz, config.high_freq_hz);
        std::vector<std::vector<TimeStep>> spike_trains(config.num_channels);

        std::mt19937 rng(seed);
        std::uniform_real_distribution<float> dist(0.0f, 1.0f);

        // Simplified: for each channel, compute envelope and convert to spikes
        // Real implementation would use gammatone filterbank
        for (int ch = 0; ch < config.num_channels; ++ch) {
            float freq = frequencies[ch];
            float period_samples = 1000.0f / freq / dt_ms;

            // Simulated envelope (would come from gammatone filter)
            for (size_t t = 0; t < audio.size(); ++t) {
                float envelope = std::abs(audio[t]) * config.max_rate_hz;
                float prob = envelope * dt_ms / 1000.0f;

                if (dist(rng) < prob) {
                    spike_trains[ch].push_back(static_cast<TimeStep>(t));
                }
            }
        }
        return spike_trains;
    }
};

} // namespace neurosim::encoding
