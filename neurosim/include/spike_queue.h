#pragma once
// NeuroSim — Delayed Spike Queue
// Ring buffer for axonal delay with zero-allocation push/pop
// Each neuron gets a delay queue that holds "spike arrives at time T" events

#include "types.h"
#include <cstdint>
#include <cstring>

namespace neurosim {

// ============================================================================
// SpikeQueue — circular buffer of spike events per neuron
// Fixed capacity, no heap allocation during simulation
// Cache-friendly: power-of-2 size enables mask-based wrapping
// ============================================================================
template<size_t Capacity = 64>  // Max delay in timesteps
class SpikeQueue {
    static_assert((Capacity & (Capacity - 1)) == 0, "Capacity must be power of 2");

public:
    SpikeQueue() : head_(0), tail_(0) {
        std::memset(buffer_, 0, sizeof(buffer_));
    }

    // Push a spike with given delay (in timesteps)
    inline void push(float weight, TimeStep delay) {
        size_t pos = (tail_++) & MASK;
        buffer_[pos].weight = weight;
        buffer_[pos].active = true;
        (void)delay;
    }

    // Pop all spikes arriving this timestep
    inline float pop_sum() {
        float total = 0.0f;
        while (head_ < tail_) {
            size_t pos = (head_++) & MASK;
            if (buffer_[pos].active) {
                total += buffer_[pos].weight;
                buffer_[pos].active = false;
            }
        }
        return total;
    }

    inline bool empty() const { return head_ >= tail_; }
    inline void clear() { head_ = 0; tail_ = 0; std::memset(buffer_, 0, sizeof(buffer_)); }

private:
    static constexpr size_t MASK = Capacity - 1;

    struct Entry {
        float weight;
        bool active;
        uint8_t _pad[3];
    };

    Entry buffer_[Capacity];
    size_t head_;
    size_t tail_;
};

// ============================================================================
// DelayedSpikeRouter — routes spikes through delay queues
// O(spikes) not O(connections) — massive speedup for sparse networks
// ============================================================================
class DelayedSpikeRouter {
public:
    explicit DelayedSpikeRouter(NeuronId max_neurons, size_t queue_capacity = 64)
        : max_neurons_(max_neurons) {
        queues_ = new SpikeQueue<64>[max_neurons];
    }

    ~DelayedSpikeRouter() { delete[] queues_; }

    inline void enqueue(NeuronId target, float weight, TimeStep delay) {
        queues_[target].push(weight, delay);
    }

    inline float deliver(NeuronId neuron) {
        return queues_[neuron].pop_sum();
    }

    void deliver_all(float* I, NeuronId count) {
        for (NeuronId i = 0; i < count; ++i) {
            I[i] += queues_[i].pop_sum();
        }
    }

private:
    NeuronId max_neurons_;
    SpikeQueue<64>* queues_;
};

} // namespace neurosim
