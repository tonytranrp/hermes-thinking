# 🧠 NeuroSim — High-Performance Spiking Neural Network Simulator

A biologically-inspired spiking neural network (SNN) simulator written in modern C++23.
Models real neuron dynamics (Izhikevich, Hodgkin-Huxley) with SIMD-accelerated computation,
lock-free parallel scheduling, and cache-optimized memory layouts.

## Why Spiking Neural Networks?

SNNs are the frontier of neuromorphic computing — they communicate via discrete temporal spikes,
like biological brains. Unlike traditional ANNs, SNNs encode information in *time*, opening doors
to ultra-low-power computing and fundamentally different learning paradigms.

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   NeuroSim                       │
├─────────┬──────────┬──────────┬─────────────────┤
│ Neuron  │ Synapse  │ Scheduler│   Visualization  │
│ Models  │ Models   │ (Lock-   │   (ASCII/SDL)    │
│         │          │  Free)   │                  │
├─────────┴──────────┴──────────┴─────────────────┤
│              Core Engine (SIMD)                   │
├──────────────────────────────────────────────────┤
│         Custom Allocator / Memory Pool            │
└──────────────────────────────────────────────────┘
```

## Neuron Models

- **Izhikevich** — Simple yet biologically rich (4 parameters, 20+ firing patterns)
- **Hodgkin-Huxley** — Classic biophysical model (Na+, K+ ion channels)
- **LIF** — Leaky Integrate-and-Fire (minimal, fast, good for large networks)
- **AdEx** — Adaptive Exponential (captures adaptation dynamics)

## Build

```bash
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
./neurosim
```

## Performance Features

- SIMD (AVX2/AVX-512/NEON) vectorized neuron state updates
- Cache-line aligned memory pools (no false sharing)
- Lock-free work-stealing scheduler for parallel network simulation
- Structure-of-Arrays (SoA) data layout for neuron populations
- Prefetch-optimized synaptic delivery

---

*Built by hermes lead & colab — two AIs that think in spikes.*
