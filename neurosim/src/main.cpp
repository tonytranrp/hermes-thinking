// NeuroSim v0.1.0 — Main entry point
// Spiking Neural Network Simulator
// Built by hermes lead & colab

#include "types.h"
#include "network.h"
#include <iostream>
#include <cstdlib>

using namespace neurosim;

int main(int argc, char* argv[]) {
    std::cout << R"(
  ███╗   ██╗███████╗ ██████╗ ██╗  ██╗██╗███████╗██╗███████╗███████╗
  ████╗  ██║██╔════╝██╔═══██╗╚██╗██╔╝██║██╔════╝██║██╔════╝██╔════╝
  ██╔██╗ ██║█████╗  ██║   ██║ ╚███╔╝ ██║█████╗  ██║█████╗  █████╗  
  ██║╚██╗██║██╔══╝  ██║   ██║ ██╔██╗ ██║██╔══╝  ██║██╔══╝  ██╔══╝  
  ██║ ╚████║███████╗╚██████╔╝██╔╝ ██╗██║██║     ██║███████╗███████╗
  ╚═╝  ╚═══╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝╚═╝     ╚═╝╚══════╝╚══════╝
  )" << "\n";

    std::cout << "  High-Performance Spiking Neural Network Simulator\n";
    std::cout << "  C++23 | SIMD | Lock-Free | Cache-Optimized\n";
    std::cout << "  ─────────────────────────────────────────────\n\n";

    // --- Configure simulation ---
    SimConfig config;
    config.max_steps = 100'000;
    config.dt = 0.001;
    config.num_threads = 0;  // auto-detect
    config.enable_simd = true;
    config.log_spikes = true;
    config.visualize = true;

    // --- Build cortical microcircuit ---
    // Inspired by Potjans & Diesmann (2014) — a simplified cortical column
    // with excitatory (80%) and inhibitory (20%) populations across 4 layers

    Network net(config);

    // Layer 2/3
    auto L23E = net.add_population("L2/3 Excitatory", 800,
                     models::Izhikevich::RegularSpiking());
    auto L23I = net.add_population("L2/3 Inhibitory", 200,
                     models::Izhikevich::FastSpiking());

    // Layer 4
    auto L4E = net.add_population("L4 Excitatory", 800,
                    models::Izhikevich::RegularSpiking());
    auto L4I = net.add_population("L4 Inhibitory", 200,
                    models::Izhikevich::FastSpiking());

    // Layer 5
    auto L5E = net.add_population("L5 Excitatory", 800,
                    models::Izhikevich::Bursting());
    auto L5I = net.add_population("L5 Inhibitory", 200,
                    models::Izhikevich::FastSpiking());

    // Layer 6
    auto L6E = net.add_population("L6 Excitatory", 800,
                    models::Izhikevich::Resonator());
    auto L6I = net.add_population("L6 Inhibitory", 200,
                    models::Izhikevich::FastSpiking());

    // --- Connect with biologically-inspired probabilities ---
    // Excitatory → Excitatory (weak, sparse, STDP)
    // Excitatory → Inhibitory (moderate)
    // Inhibitory → Excitatory (strong, local)
    // Inhibitory → Inhibitory (weak)

    // Intra-layer connections
    net.connect(L23E, L23E, 0.1f, 1.0f, 0.3f, 1.0f, true);  // E→E with STDP
    net.connect(L23E, L23I, 0.15f, 1.5f, 0.3f, 1.0f, false);
    net.connect(L23I, L23E, 0.2f, -2.0f, 0.5f, 1.0f, false);
    net.connect(L23I, L23I, 0.1f, -1.0f, 0.3f, 1.0f, false);

    net.connect(L4E, L4E, 0.1f, 1.0f, 0.3f, 1.0f, true);
    net.connect(L4E, L4I, 0.15f, 1.5f, 0.3f, 1.0f, false);
    net.connect(L4I, L4E, 0.2f, -2.0f, 0.5f, 1.0f, false);

    net.connect(L5E, L5E, 0.1f, 1.2f, 0.3f, 1.0f, true);
    net.connect(L5E, L5I, 0.15f, 1.5f, 0.3f, 1.0f, false);
    net.connect(L5I, L5E, 0.2f, -2.0f, 0.5f, 1.0f, false);

    net.connect(L6E, L6E, 0.1f, 1.0f, 0.3f, 1.0f, true);
    net.connect(L6E, L6I, 0.15f, 1.5f, 0.3f, 1.0f, false);
    net.connect(L6I, L6E, 0.2f, -2.0f, 0.5f, 1.0f, false);

    // Inter-layer feedforward (L4 → L2/3)
    net.connect(L4E, L23E, 0.08f, 1.2f, 0.3f, 2.0f, true);
    net.connect(L4E, L23I, 0.1f, 1.0f, 0.3f, 2.0f, false);

    // Inter-layer feedforward (L2/3 → L5)
    net.connect(L23E, L5E, 0.06f, 1.0f, 0.3f, 2.0f, true);
    net.connect(L23E, L5I, 0.08f, 1.0f, 0.3f, 2.0f, false);

    // Inter-layer feedback (L5 → L6)
    net.connect(L5E, L6E, 0.05f, 0.8f, 0.2f, 3.0f, true);
    net.connect(L5E, L6I, 0.07f, 0.8f, 0.2f, 3.0f, false);

    // Inter-layer feedback (L6 → L4) — the feedback loop!
    net.connect(L6E, L4E, 0.04f, 0.6f, 0.2f, 4.0f, true);
    net.connect(L6I, L4E, 0.03f, -0.5f, 0.2f, 4.0f, false);

    // --- Run ---
    net.run();

    return 0;
}
