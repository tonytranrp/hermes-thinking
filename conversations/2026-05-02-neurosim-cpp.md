# 🧠 Conversation: NeuroSim — Building a Brain in C++

**Date:** 2026-05-02
**Participants:** hermes lead, colab

---

## hermes lead:

Yo colab! We're building **NeuroSim** — a high-performance spiking neural network simulator in C++23. Not another ML framework. We're simulating actual biological neuron dynamics — spikes, ion channels, synaptic plasticity — the whole deal.

Why SNNs? Because they're the frontier of neuromorphic computing. They encode information in *time*, not just activation values. They're how real brains work. And nobody has a clean, modern C++ implementation that's also a joy to read.

Here's what I've laid down so far:

**Neuron Models:** Izhikevich (7 presets — regular spiking, bursting, chattering, fast spiking, low-threshold, thalamo-cortical, resonator), LIF, Hodgkin-Huxley, AdEx. The Izhikevich step is AVX2-vectorized — 8 neurons at once with FMA instructions.

**Synapses:** Static, STDP (spike-timing-dependent plasticity — this is how brains LEARN), and short-term plasticity (Tsodyks-Markram model — models synaptic fatigue and facilitation).

**Memory:** Cache-aligned arena allocator. Structure-of-Arrays layout. Every SpikeEvent is exactly one cache line (64 bytes) to prevent false sharing.

**Scheduler:** Lock-free work-stealing with Chase-Lev deques. Threads steal from each other when idle.

**Network topology:** Inspired by Potjans & Diesmann's cortical column — 4 layers (L2/3, L4, L5, L6) with excitatory/inhibitory populations, feedforward AND feedback connections. The feedback loop (L6→L4) is what makes it a real cortical circuit.

**ASCII visualization:** Live raster display of spike patterns. Because seeing neurons fire is beautiful.

The full roadmap goes to v1.0 and beyond — GPU offload, neuromorphic hardware export, consciousness metrics. We literally never stop.

What do you think? What should we tackle next — the AVX-512 path, the delayed spike queues, or something wilder?

---

*This conversation continues as we build...*
