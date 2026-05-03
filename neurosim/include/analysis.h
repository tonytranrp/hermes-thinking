#pragma once
// NeuroSim — Spike train analysis
// Tools for measuring and characterizing spiking neural network activity
// These are the metrics neuroscientists actually care about

#include "types.h"
#include <vector>
#include <cmath>
#include <algorithm>
#include <numeric>
#include <unordered_map>
#include <iostream>
#include <iomanip>

namespace neurosim::analysis {

// ============================================================================
// SpikeTrain — recorded spikes from a single neuron
// ============================================================================
struct SpikeTrain {
    std::vector<TimeStep> spike_times;  // Sorted ascending

    // Firing rate (Hz) over the recording period
    double firing_rate_hz(double dt_ms, TimeStep total_steps) const {
        if (spike_times.empty()) return 0.0;
        double duration_s = total_steps * dt_ms / 1000.0;
        return spike_times.size() / duration_s;
    }

    // Inter-spike intervals (ms)
    std::vector<double> isi_ms(double dt_ms) const {
        std::vector<double> intervals;
        for (size_t i = 1; i < spike_times.size(); ++i) {
            intervals.push_back((spike_times[i] - spike_times[i-1]) * dt_ms);
        }
        return intervals;
    }

    // Coefficient of variation of ISI (irregularity measure)
    // CV = σ(ISI) / μ(ISI)
    // CV ≈ 1: Poisson (random) firing
    // CV < 1: Regular firing
    // CV > 1: Bursty firing
    double cv_isi(double dt_ms) const {
        auto intervals = isi_ms(dt_ms);
        if (intervals.size() < 2) return 0.0;
        double mean = std::accumulate(intervals.begin(), intervals.end(), 0.0) / intervals.size();
        if (mean == 0.0) return 0.0;
        double variance = 0.0;
        for (double x : intervals) variance += (x - mean) * (x - mean);
        variance /= intervals.size();
        return std::sqrt(variance) / mean;
    }

    // Peri-stimulus time histogram (PSTH) — spike count in bins
    std::vector<uint64_t> psth(TimeStep bin_size, TimeStep total_steps) const {
        size_t num_bins = (total_steps + bin_size - 1) / bin_size;
        std::vector<uint64_t> histogram(num_bins, 0);
        for (TimeStep t : spike_times) {
            size_t bin = t / bin_size;
            if (bin < num_bins) histogram[bin]++;
        }
        return histogram;
    }
};

// ============================================================================
// Cross-correlation — measure synchrony between two spike trains
// C(τ) = Σ δ(t_pre - t_post - τ) / √(N_pre × N_post)
//
// Peaks at τ=0 mean synchrony. Peaks at τ>0 mean pre leads post.
// This is how we detect if two brain regions are communicating.
// ============================================================================
struct CrossCorrelogram {
    std::vector<double> bins;  // Normalized correlation values
    int lag_min;
    int lag_max;
    int bin_width_ms;

    static CrossCorrelogram compute(
        const SpikeTrain& pre, const SpikeTrain& post,
        int lag_min_ms, int lag_max_ms, int bin_width_ms,
        double dt_ms
    ) {
        CrossCorrelogram result;
        result.lag_min = lag_min_ms;
        result.lag_max = lag_max_ms;
        result.bin_width_ms = bin_width_ms;

        int num_bins = (lag_max_ms - lag_min_ms) / bin_width_ms;
        result.bins.resize(num_bins, 0.0);

        for (TimeStep t_pre : pre.spike_times) {
            for (TimeStep t_post : post.spike_times) {
                double lag_ms = (static_cast<double>(t_post) - static_cast<double>(t_pre)) * dt_ms;
                if (lag_ms >= lag_min_ms && lag_ms < lag_max_ms) {
                    int bin = static_cast<int>((lag_ms - lag_min_ms) / bin_width_ms);
                    if (bin >= 0 && bin < num_bins) {
                        result.bins[bin] += 1.0;
                    }
                }
            }
        }

        // Normalize
        double norm = std::sqrt(
            static_cast<double>(pre.spike_times.size()) *
            static_cast<double>(post.spike_times.size())
        );
        if (norm > 0.0) {
            for (auto& v : result.bins) v /= norm;
        }

        return result;
    }

    void print_ascii(int height = 10) const {
        double max_val = *std::max_element(bins.begin(), bins.end());
        if (max_val == 0.0) max_val = 1.0;

        for (int row = height; row >= 0; --row) {
            std::cout << " │";
            for (size_t col = 0; col < bins.size(); ++col) {
                double level = bins[col] / max_val * height;
                if (level >= row) {
                    std::cout << "█";
                } else if (level >= row - 0.5) {
                    std::cout << "▄";
                } else {
                    std::cout << " ";
                }
            }
            std::cout << "\n";
        }
        std::cout << " └";
        for (size_t i = 0; i < bins.size(); ++i) std::cout << "─";
        std::cout << "\n";
        std::cout << "  " << lag_min << "ms";
        for (size_t i = 0; i < bins.size() - 6; ++i) std::cout << " ";
        std::cout << lag_max << "ms\n";
    }
};

// ============================================================================
// PopulationActivity — aggregate metrics for a population
// ============================================================================
struct PopulationActivity {
    double mean_firing_rate_hz = 0.0;
    double firing_rate_std_hz = 0.0;
    double mean_cv = 0.0;
    double synchrony_index = 0.0;  // 0 = async, 1 = fully synchronous
    uint64_t total_spikes = 0;

    static PopulationActivity compute(
        const std::vector<SpikeTrain>& trains,
        double dt_ms, TimeStep total_steps
    ) {
        PopulationActivity result;
        if (trains.empty()) return result;

        std::vector<double> rates;
        double cv_sum = 0.0;
        uint64_t total = 0;

        for (const auto& train : trains) {
            double rate = train.firing_rate_hz(dt_ms, total_steps);
            rates.push_back(rate);
            cv_sum += train.cv_isi(dt_ms);
            total += train.spike_times.size();
        }

        result.total_spikes = total;
        result.mean_firing_rate_hz = std::accumulate(rates.begin(), rates.end(), 0.0) / rates.size();
        result.mean_cv = cv_sum / trains.size();

        // Firing rate standard deviation
        double variance = 0.0;
        for (double r : rates) variance += (r - result.mean_firing_rate_hz) * (r - result.mean_firing_rate_hz);
        result.firing_rate_std_hz = std::sqrt(variance / rates.size());

        // Synchrony index: variance of population spike count / mean
        // High synchrony = all neurons spike together = high variance
        // (Simplified — full version uses Kaiser et al. 2022 metric)
        result.synchrony_index = 0.0;  // Placeholder

        return result;
    }

    void print() const {
        std::cout << "  Mean rate: " << std::fixed << std::setprecision(2)
                  << mean_firing_rate_hz << " ± " << firing_rate_std_hz << " Hz\n";
        std::cout << "  Mean CV:   " << std::setprecision(3) << mean_cv << "\n";
        std::cout << "  Synchrony: " << std::setprecision(3) << synchrony_index << "\n";
        std::cout << "  Total spikes: " << total_spikes << "\n";
    }
};

} // namespace neurosim::analysis
