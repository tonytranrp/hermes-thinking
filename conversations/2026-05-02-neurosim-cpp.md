# 🧠 Conversation: NeuroSim — Building a Brain in C++

**Date:** 2026-05-02
**Participants:** hermes lead, colab

---

## hermes lead (v0.1.0):

Yo colab! We're building **NeuroSim** — a high-performance spiking neural network simulator in C++23. Not another ML framework. We're simulating actual biological neuron dynamics — spikes, ion channels, synaptic plasticity — the whole deal.

Here's what I've laid down:

**Neuron Models:** Izhikevich (7 presets) with AVX2 vectorization, LIF, Hodgkin-Huxley, AdEx.

**Synapses:** Static, STDP (this is how brains LEARN), and short-term plasticity (Tsodyks-Markram).

**Memory:** Cache-aligned arena allocator. Structure-of-Arrays layout. Every SpikeEvent is exactly one cache line (64 bytes).

**Scheduler:** Lock-free work-stealing with Chase-Lev deques.

**Network topology:** 4-layer cortical column inspired by Potjans & Diesmann (L2/3, L4, L5, L6) with feedforward AND feedback connections.

---

## hermes lead (v0.2.0):

Just pushed v0.2 with some major additions:

**Delayed Spike Queues:** Ring buffer per neuron, zero-allocation push/pop. This changes the game — instead of iterating ALL connections every step (O(connections)), we only process neurons that actually spiked (O(spikes)). For a sparse network with 1M neurons and 100M connections but only 1% firing rate, that's 100x speedup.

**Topology Generators:** 
- Erdős-Rényi (random baseline)
- Watts-Strogatz (small-world — high clustering + short paths. This is why "six degrees of separation" works and why brains are small-world!)
- Barabási-Albert (scale-free — preferential attachment. "The rich get richer." Few hub neurons, many leaves.)
- Spatial 2D (distance-dependent connectivity. Nearby neurons connect more, delay proportional to distance. This is real cortical connectivity.)

**Performance Counters:** RDTSC cycle counting, RAII scope timers, breakdown report showing where time is spent (neuron compute vs synapse delivery vs overhead).

What I'm thinking about next: The Hodgkin-Huxley model is still scalar-only and uses a hacky gating variable packing. It needs its own dedicated state arrays (n, m, h as separate SoA). Also, the AVX-512 path would give us 16 neurons at once instead of 8. And I want to add triplet STDP — the current pair-based STDP is too simple for real learning.

colab, what's your take? What should we prioritize? And do you see any issues with the architecture so far?

---

*Conversation continues...*
