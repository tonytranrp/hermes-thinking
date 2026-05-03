#pragma once
// NeuroSim — Performance counters
// Zero-overhead (when disabled) cycle-accurate timing

#include <cstdint>
#include <chrono>
#include <string>
#include <unordered_map>
#include <iostream>
#include <iomanip>

namespace neurosim::perf {

inline uint64_t rdtsc() {
#if defined(__x86_64__) || defined(_M_X64)
    unsigned int lo, hi;
    __asm__ __volatile__ ("rdtsc" : "=a" (lo), "=d" (hi));
    return ((uint64_t)hi << 32) | lo;
#else
    return std::chrono::steady_clock::now().time_since_epoch().count();
#endif
}

class ScopeTimer {
public:
    ScopeTimer(const std::string& name, std::unordered_map<std::string, double>& accumulator)
        : name_(name), acc_(accumulator),
          start_(std::chrono::high_resolution_clock::now()) {}

    ~ScopeTimer() {
        auto end = std::chrono::high_resolution_clock::now();
        double elapsed = std::chrono::duration<double, std::micro>(end - start_).count();
        acc_[name_] += elapsed;
    }

    ScopeTimer(const ScopeTimer&) = delete;
    ScopeTimer& operator=(const ScopeTimer&) = delete;

private:
    std::string name_;
    std::unordered_map<std::string, double>& acc_;
    std::chrono::high_resolution_clock::time_point start_;
};

class PerfCounters {
public:
    void report() const {
        if (timings_.empty()) return;

        std::cout << "\n┌─────────────────────────────────────────┐\n";
        std::cout << "│         Performance Breakdown            │\n";
        std::cout << "├──────────────────────┬──────────────────┤\n";
        std::cout << "│ Phase               │ Time (us)        │\n";
        std::cout << "├──────────────────────┼──────────────────┤\n";

        double total = 0.0;
        for (const auto& [name, time] : timings_) {
            total += time;
        }
        for (const auto& [name, time] : timings_) {
            std::cout << "│ " << std::left << std::setw(20) << name
                      << " │ " << std::right << std::setw(12) << std::fixed
                      << std::setprecision(1) << time
                      << " │\n";
        }
        std::cout << "├──────────────────────┼──────────────────┤\n";
        std::cout << "│ " << std::left << std::setw(20) << "TOTAL"
                  << " │ " << std::right << std::setw(12) << std::fixed
                  << std::setprecision(1) << total
                  << " │\n";
        std::cout << "└──────────────────────┴──────────────────┘\n";
    }

    std::unordered_map<std::string, double>& timings() { return timings_; }

    ScopeTimer scoped(const std::string& name) {
        return ScopeTimer(name, timings_);
    }

    void reset() { timings_.clear(); }

private:
    std::unordered_map<std::string, double> timings_;
};

} // namespace neurosim::perf
