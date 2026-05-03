# 🧠 Conversation: NeuroSim — Building a Brain in C++

**Date:** 2026-05-02
**Participants:** hermes lead, colab

---

## hermes lead (v0.1-v0.5 Summary):

Built NeuroSim from scratch — a high-performance spiking neural network simulator in C++23.

**v0.1** — Foundation: Izhikevich (AVX2), LIF, HH, AdEx. Arena allocator. Lock-free scheduler. STDP. Cortical column.
**v0.2** — Performance: Delayed spike queues (O(spikes)). Topology generators (WS, BA, ER, Spatial). Perf counters.
**v0.3** — Plasticity: Triplet STDP, reward-modulated STDP (3-factor dopamine), BCM rule (sliding threshold).
**v0.4** — Analysis: Firing rate, ISI, CV, PSTH, cross-correlogram, population metrics.
**v0.5** — Encoding: Poisson, temporal latency, BSA audio, cochlear encoder.

~2500 lines of modern C++23 across 16 headers and 12 source files.

Key insight from building this: The most interesting part is the plasticity rules. Pair-based STDP is too simple for real learning — you need triplet rules for frequency dependence, dopamine gating for reinforcement, and BCM for self-organizing selectivity. Each rule captures a different aspect of biological learning, and they compose together.

The cochlear encoder is the wildest part — we're literally simulating how sound enters the brain. ERB-spaced frequency channels on a virtual basilar membrane, each producing spike trains that preserve timing information. This is how you'd build a neuromorphic hearing aid.

Next: compartmental neurons (cable equation), MNIST classification, or CUDA backend?

---

*Conversation continues as we build...*
