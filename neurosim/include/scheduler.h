#pragma once
// NeuroSim — Lock-free work-stealing scheduler
// Divides neuron populations across threads; idle threads steal work

#include "types.h"
#include <thread>
#include <atomic>
#include <vector>
#include <functional>
#include <barrier>

namespace neurosim {

// ============================================================================
// WorkStealingQueue — lock-free deque for stealable tasks
// Based on Chase-Lev work-stealing deque (2005)
// ============================================================================
class WorkStealingQueue {
public:
    WorkStealingQueue() : top_(0), bottom_(0) {
        capacity_ = 1024;
        tasks_ = new Task[capacity_];
    }

    ~WorkStealingQueue() { delete[] tasks_; }

    using Task = std::function<void()>;

    // Push to bottom (owner thread only)
    void push(Task t) {
        size_t b = bottom_.load(std::memory_order_relaxed);
        if (b >= capacity_) {
            // Simple resize — double the array
            size_t new_cap = capacity_ * 2;
            Task* new_tasks = new Task[new_cap];
            for (size_t i = top_.load(std::memory_order_relaxed); i < b; ++i) {
                new_tasks[i % new_cap] = std::move(tasks_[i % capacity_]);
            }
            delete[] tasks_;
            tasks_ = new_tasks;
            capacity_ = new_cap;
        }
        tasks_[b % capacity_] = std::move(t);
        bottom_.store(b + 1, std::memory_order_release);
    }

    // Pop from bottom (owner thread only)
    Task pop() {
        size_t b = bottom_.load(std::memory_order_relaxed) - 1;
        bottom_.store(b, std::memory_order_relaxed);
        std::atomic_thread_fence(std::memory_order_seq_cst);
        size_t t = top_.load(std::memory_order_relaxed);
        if (t > b) {
            bottom_.store(b + 1, std::memory_order_relaxed);
            return nullptr;
        }
        if (t == b) {
            // Last item — race with steal
            bool won = top_.compare_exchange_strong(t, t + 1,
                std::memory_order_seq_cst, std::memory_order_relaxed);
            bottom_.store(b + 1, std::memory_order_relaxed);
            return won ? std::move(tasks_[t % capacity_]) : nullptr;
        }
        return std::move(tasks_[b % capacity_]);
    }

    // Steal from top (other threads)
    Task steal() {
        size_t t = top_.load(std::memory_order_acquire);
        std::atomic_thread_fence(std::memory_order_seq_cst);
        size_t b = bottom_.load(std::memory_order_acquire);
        if (t < b) {
            return std::move(tasks_[t % capacity_]);
        }
        return nullptr;
    }

    bool empty() const {
        return top_.load(std::memory_order_relaxed) >=
               bottom_.load(std::memory_order_relaxed);
    }

private:
    Task* tasks_;
    size_t capacity_;
    alignas(64) std::atomic<size_t> top_;
    alignas(64) std::atomic<size_t> bottom_;
};

// ============================================================================
// Scheduler — manages worker threads and distributes simulation work
// ============================================================================
class Scheduler {
public:
    explicit Scheduler(uint32_t num_threads = 0)
        : running_(false), step_count_(0) {
        if (num_threads == 0) {
            num_threads = std::thread::hardware_concurrency();
            if (num_threads == 0) num_threads = 4;
        }
        num_threads_ = num_threads;
        queues_.reserve(num_threads);
        for (uint32_t i = 0; i < num_threads; ++i) {
            queues_.emplace_back(std::make_unique<WorkStealingQueue>());
        }
    }

    ~Scheduler() { stop(); }

    void start() {
        running_.store(true, std::memory_order_release);
        for (uint32_t i = 0; i < num_threads_; ++i) {
            workers_.emplace_back([this, i]() { worker_loop(i); });
        }
    }

    void stop() {
        running_.store(false, std::memory_order_release);
        for (auto& w : workers_) {
            if (w.joinable()) w.join();
        }
        workers_.clear();
    }

    // Schedule work on a specific thread's queue
    void schedule(uint32_t thread_id, WorkStealingQueue::Task task) {
        queues_[thread_id % num_threads_]->push(std::move(task));
    }

    // Schedule on least-loaded queue (approximate)
    void schedule_any(WorkStealingQueue::Task task) {
        // Simple round-robin for now; can be improved with load tracking
        queues_[step_count_.fetch_add(1) % num_threads_]->push(std::move(task));
    }

    uint32_t num_threads() const { return num_threads_; }

private:
    void worker_loop(uint32_t id) {
        while (running_.load(std::memory_order_acquire)) {
            auto task = queues_[id]->pop();
            if (!task) {
                // Try to steal from other queues
                for (uint32_t i = 0; i < num_threads_; ++i) {
                    if (i == id) continue;
                    task = queues_[i]->steal();
                    if (task) break;
                }
            }
            if (task) {
                task();
            } else {
                // Backoff
                std::this_thread::yield();
            }
        }
    }

    std::vector<std::unique_ptr<WorkStealingQueue>> queues_;
    std::vector<std::thread> workers_;
    std::atomic<bool> running_;
    std::atomic<uint64_t> step_count_;
    uint32_t num_threads_;
};

} // namespace neurosim
