# 🗺️ NeuroSim Roadmap — Infinite Iteration

This is a living roadmap. Each version adds a layer of depth. We never stop.

## v0.1.0 — Foundation ✅
- [x] Izhikevich neuron model (7 presets)
- [x] LIF neuron model
- [x] Hodgkin-Huxley model (scalar)
- [x] AdEx model
- [x] Cache-aligned arena allocator
- [x] AVX2 vectorized Izhikevich step
- [x] Lock-free work-stealing scheduler (Chase-Lev deque)
- [x] STDP synaptic plasticity
- [x] Short-term plasticity (Tsodyks-Markram)
- [x] Cortical microcircuit topology (4-layer Potjans-Diesmann inspired)
- [x] ASCII raster visualization
- [x] CSV spike logging

## v0.2.0 — Performance
- [ ] AVX-512 vectorized Izhikevich step
- [ ] NEON vectorized step (ARM)
- [ ] Structure-of-Arrays for all neuron models
- [ ] Software prefetch hints in synapse delivery loop
- [ ] Huge pages (2MB) for arena allocator
- [ ] NUMA-aware memory allocation
- [ ] Benchmark suite (Google Benchmark)
- [ ] Profile-guided optimization hints

## v0.3.0 — Delayed Spike Queues
- [ ] Per-neuron spike queue with configurable delay
- [ ] Ring buffer implementation (cache-friendly, no allocations)
- [ ] Delayed STDP: track pre/post spike times per synapse
- [ ] Proper axonal delay modeling (1-20ms range)

## v0.4.0 — Advanced Plasticity
- [ ] Triplet STDP (Pfister & Gerstner 2006)
- [ ] Reward-modulated STDP (3-factor learning)
- [ ] BCM rule (Bienenstock-Cooper-Munro)
- [ ] Homeostatic plasticity (intrinsic excitability)
- [ ] Dopamine-modulated reinforcement learning

## v0.5.0 — GPU Offload
- [ ] CUDA backend for neuron state updates
- [ ] HIP/ROCm support (AMD GPUs)
- [ ] Vulkan compute shader backend
- [ ] Automatic CPU/GPU load balancing
- [ ] Unified Memory for seamless data movement

## v0.6.0 — Visualization
- [ ] SDL2 real-time raster display
- [ ] WebSocket streaming (browser visualization)
- [ ] PNG/WebP frame export
- [ ] Network graph visualization (GraphViz DOT)
- [ ] Spike train sonification (hear the brain!)

## v0.7.0 — Network Topologies
- [ ] Small-world networks (Watts-Strogatz)
- [ ] Scale-free networks (Barabási-Albert)
- [ ] Spatial networks (distance-dependent connectivity)
- [ ] Grow-and-prune topology evolution
- [ ] Cortical column templates (minicolumns, macrocolumns)

## v0.8.0 — Input/Output
- [ ] NEST-compatible spike I/O
- [ ] BRIAN-compatible model import
- [ ] Neuromorphic hardware export (Loihi, SpiNNaker)
- [ ] HDF5 checkpoint save/restore
- [ ] Python bindings (pybind11)

## v0.9.0 — Neuromorphic Applications
- [ ] MNIST classification with SNN
- [ ] Event-based vision (DVS) processing
- [ ] Audio spike encoding (cochlea model)
- [ ] Robot navigation (SNN controller)
- [ ] Energy estimation vs. equivalent ANN

## v1.0.0 — Production
- [ ] Comprehensive documentation (Doxygen)
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Package managers (vcpkg, conan)
- [ ] Interactive tutorial notebook
- [ ] Performance comparison paper

## Beyond v1.0 — The Infinite Horizon
- Compartmental neuron models (multi-dendrite)
- Astrocyte-neuron interactions (tripartite synapse)
- Epigenetic plasticity rules
- Embodied simulation (virtual agent in 3D environment)
- Evolution of SNN topologies (neuroevolution)
- Quantum-inspired spike dynamics
- Consciousness metrics (integrated information Φ)
- Real-time BCI interface (brain-computer)
- ...

---

*This roadmap never ends. Every completion reveals new horizons.*
