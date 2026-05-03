#pragma once
// NeuroSim — Custom memory allocator
// Cache-line aligned pool allocator for neuron/synapse state
// Avoids malloc/free in the hot loop; pre-allocates everything

#include "types.h"
#include <cstddef>
#include <cstdint>
#include <vector>
#include <new>

namespace neurosim {

// Cache line size — 64 bytes on x86-64, 128 on some ARM
#ifdef __aarch64__
inline constexpr size_t CACHE_LINE = 128;
#else
inline constexpr size_t CACHE_LINE = 64;
#endif

// Page size for huge allocation alignment
inline constexpr size_t PAGE_SIZE = 4096;

// ============================================================================
// AlignedPool — pre-allocates aligned memory blocks
// No individual deallocation — free all at once (arena pattern)
// ============================================================================
class AlignedPool {
public:
    explicit AlignedPool(size_t block_size = 1024 * 1024)  // 1MB default blocks
        : block_size_(block_size), offset_(0) {}

    ~AlignedPool() {
        for (void* block : blocks_) {
            ::operator delete(block, std::align_val_t{CACHE_LINE});
        }
    }

    // Allocate `count` elements of type T, cache-line aligned
    template<typename T>
    T* alloc(size_t count) {
        static_assert(alignof(T) <= CACHE_LINE, "Type alignment exceeds cache line");

        const size_t bytes = count * sizeof(T);
        const size_t aligned_bytes = (bytes + CACHE_LINE - 1) & ~(CACHE_LINE - 1);

        if (offset_ + aligned_bytes > current_block_size_) {
            // Allocate new block — at least as large as requested
            size_t new_size = block_size_;
            if (aligned_bytes > new_size) new_size = aligned_bytes;

            void* block = ::operator new(new_size, std::align_val_t{CACHE_LINE});
            blocks_.push_back(block);
            current_block_size_ = new_size;
            offset_ = 0;
        }

        T* result = reinterpret_cast<T*>(
            static_cast<uint8_t*>(blocks_.back()) + offset_
        );
        offset_ += aligned_bytes;

        // Touch pages to avoid page faults during simulation
        for (size_t i = 0; i < bytes; i += PAGE_SIZE) {
            reinterpret_cast<uint8_t*>(result)[i] = 0;
        }

        return result;
    }

    // Reset — reuse memory without freeing (for next simulation run)
    void reset() {
        offset_ = 0;
        if (!blocks_.empty()) {
            // Keep the largest block, free the rest
            size_t max_idx = 0;
            size_t max_size = 0;
            for (size_t i = 0; i < blocks_.size(); ++i) {
                // Approximate — we don't track individual block sizes perfectly
                // For now, just keep the first block
            }
        }
    }

    size_t total_allocated() const {
        return blocks_.size() * block_size_;
    }

private:
    size_t block_size_;
    size_t current_block_size_ = 0;
    size_t offset_;
    std::vector<void*> blocks_;
};

// ============================================================================
// SoAAllocator — allocates all arrays for a NeuronStateSoA at once
// Ensures all arrays are in the same memory region for prefetch effectiveness
// ============================================================================
class SoAAllocator {
public:
    explicit SoAAllocator(NeuronId neurons_per_pop)
        : n_(neurons_per_pop) {}

    NeuronStateSoA allocate(AlignedPool& pool, float a, float b, float c, float d) {
        NeuronStateSoA state;
        state.v = pool.alloc<float>(n_);
        state.u = pool.alloc<float>(n_);
        state.I = pool.alloc<float>(n_);
        state.spiked = pool.alloc<bool>(n_);
        state.count = n_;
        state.a = a;
        state.b = b;
        state.c = c;
        state.d = d;
        return state;
    }

private:
    NeuronId n_;
};

} // namespace neurosim
