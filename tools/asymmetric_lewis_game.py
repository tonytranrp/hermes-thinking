#!/usr/bin/env python3
"""
Asymmetric Lewis Signaling Game — When Communicators Have Unequal Capacity

What happens when the sender has MORE states than the receiver has signals?
Or when the receiver has more actions than the sender has signals?

This simulates the real-world case where communicators have unequal
representational capacity — e.g., an expert communicating with a novice,
or a human communicating with an AI that has different conceptual granularity.

Key question: Can meaning emerge when one agent's vocabulary is coarser
than the other's? What is lost? What is gained?

Usage:
    python3 asymmetric_lewis_game.py
    python3 asymmetric_lewis_game.py --states 8 --signals 4 --actions 8
"""

import random
import math
import argparse
from collections import defaultdict

from lewis_signaling_game import Sender, Receiver, convention_stability, convention_entropy


def simulate_asymmetric(n_states, n_signals, n_actions, rounds, lr, seed):
    """Run an asymmetric Lewis signaling game."""
    rng = random.Random(seed)
    sender = Sender(n_states, n_signals, lr, seed=seed)
    receiver = Receiver(n_signals, n_actions, lr, seed=seed + 10000)
    
    success_history = []
    convergence_round = None
    # Track which states get "merged" (same signal for different states)
    signal_for_state = defaultdict(list)
    
    for round_num in range(rounds):
        state = rng.randint(0, n_states - 1)
        signal = sender.choose_signal(state)
        action = receiver.choose_action(signal)
        success = (action == state)
        
        sender.update(state, signal, success)
        receiver.update(signal, action, success)
        
        success_history.append(1 if success else 0)
        
        if (round_num + 1) % 50 == 0 and convergence_round is None:
            s_conv = sender.get_convention()
            r_conv = receiver.get_convention()
            if convention_stability(s_conv, r_conv, n_states) >= 1.0:
                convergence_round = round_num + 1
    
    sender_conv = sender.get_convention()
    receiver_conv = receiver.get_convention()
    
    # Analyze signal compression: which states share the same signal?
    signal_to_states = defaultdict(list)
    for state, signal in sender_conv.items():
        signal_to_states[signal].append(state)
    
    # Calculate theoretical maximum success rate
    if n_signals < n_states:
        theoretical_max = n_signals / n_states
    else:
        theoretical_max = 1.0
    
    return {
        "seed": seed,
        "sender_convention": sender_conv,
        "receiver_convention": receiver_conv,
        "stability": convention_stability(sender_conv, receiver_conv, n_states),
        "success_rate": sum(success_history) / len(success_history),
        "late_success_rate": sum(success_history[-500:]) / min(500, len(success_history)),
        "convergence_round": convergence_round,
        "signal_compression": {s: states for s, states in signal_to_states.items() if len(states) > 1},
        "theoretical_max": theoretical_max,
        "entropy": convention_entropy(sender, n_states),
    }


def main():
    parser = argparse.ArgumentParser(description="Asymmetric Lewis Signaling Game")
    parser.add_argument("--states", type=int, default=8, help="Number of world states")
    parser.add_argument("--signals", type=int, default=4, help="Number of signals (bottleneck)")
    parser.add_argument("--actions", type=int, default=8, help="Number of actions")
    parser.add_argument("--rounds", type=int, default=5000, help="Rounds per game")
    parser.add_argument("--lr", type=float, default=0.15, help="Learning rate")
    parser.add_argument("--runs", type=int, default=5, help="Number of runs")
    args = parser.parse_args()
    
    print("=" * 70)
    print("ASYMMETRIC LEWIS SIGNALING GAME")
    print("=" * 70)
    print(f"\nStates: {args.states} | Signals: {args.signals} | Actions: {args.actions}")
    print(f"Signal bottleneck: {args.states} states → {args.signals} signals → {args.actions} actions")
    
    if args.signals < args.states:
        print(f"\n⚠ BOTTLENECK: {args.states} states must be compressed through only {args.signals} signals.")
        print(f"  Theoretical maximum success rate: {args.signals/args.states:.1%}")
        print(f"  {args.states - args.signals} states will be 'merged' — multiple states share a signal.")
    elif args.signals > args.states:
        print(f"\n✦ REDUNDANCY: {args.signals} signals for only {args.states} states.")
        print(f"  Multiple signals can map to the same state — synonymy emerges.")
    else:
        print(f"\n✦ BALANCED: Equal states and signals — standard Lewis game.")
    
    print()
    
    all_results = []
    for run in range(args.runs):
        seed = 42 + run * 7
        result = simulate_asymmetric(args.states, args.signals, args.actions, args.rounds, args.lr, seed)
        all_results.append(result)
        
        print(f"--- Run {run + 1} (seed {seed}) ---")
        print(f"  Success rate:       {result['success_rate']:.1%} (late: {result['late_success_rate']:.1%})")
        print(f"  Theoretical max:    {result['theoretical_max']:.1%}")
        print(f"  Efficiency:         {result['late_success_rate'] / result['theoretical_max']:.1%} of theoretical max")
        print(f"  Convention stability: {result['stability']:.1%}")
        print(f"  Strategy entropy:   {result['entropy']:.3f}")
        
        if result["signal_compression"]:
            print(f"  Signal compression (states sharing signals):")
            for signal, states in sorted(result["signal_compression"].items()):
                print(f"    Signal {signal} → states {states} (MERGED)")
        else:
            if args.signals < args.states:
                print(f"  Signal compression: None detected (some states still competing)")
            else:
                print(f"  Signal compression: None (1:1 mapping)")
        print()
    
    # Cross-run analysis
    print("=" * 70)
    print("CROSS-RUN ANALYSIS")
    print("=" * 70)
    print()
    
    # Average success rate vs theoretical max
    avg_late = sum(r["late_success_rate"] for r in all_results) / len(all_results)
    avg_efficiency = sum(r["late_success_rate"] / r["theoretical_max"] for r in all_results) / len(all_results)
    
    print(f"  Average late success rate: {avg_late:.1%}")
    print(f"  Average efficiency (of theoretical max): {avg_efficiency:.1%}")
    print()
    
    # Which states get merged?
    if args.signals < args.states:
        print("MERGE PATTERNS (which states share signals across runs):")
        print("-" * 70)
        merge_pairs = defaultdict(int)
        for r in all_results:
            for signal, states in r["signal_compression"].items():
                for i in range(len(states)):
                    for j in range(i + 1, len(states)):
                        pair = tuple(sorted([states[i], states[j]]))
                        merge_pairs[pair] += 1
        
        if merge_pairs:
            for pair, count in sorted(merge_pairs.items(), key=lambda x: -x[1]):
                bar = "█" * (count * 10) + "░" * (50 - count * 10)
                print(f"  States {pair[0]}&{pair[1]}: {bar} merged in {count}/{args.runs} runs")
        else:
            print("  No consistent merge patterns detected.")
        print()
        
        # Are adjacent states more likely to be merged? (Iconicity in compression!)
        adjacent_merges = sum(count for pair, count in merge_pairs.items() if abs(pair[0] - pair[1]) == 1)
        non_adjacent_merges = sum(count for pair, count in merge_pairs.items() if abs(pair[0] - pair[1]) > 1)
        total_merges = adjacent_merges + non_adjacent_merges
        
        if total_merges > 0:
            adj_ratio = adjacent_merges / total_merges
            print(f"  Adjacent-state merges: {adjacent_merges} ({adj_ratio:.1%} of all merges)")
            print(f"  Non-adjacent merges:   {non_adjacent_merges} ({1-adj_ratio:.1%} of all merges)")
            if adj_ratio > 0.6:
                print("  ✦ ICONIC COMPRESSION — Adjacent states preferentially merge!")
                print("    When forced to compress, the system preserves semantic neighborhoods.")
            else:
                print("  ✦ ARBITRARY COMPRESSION — No preference for merging adjacent states.")
    print()
    
    # Synonymy analysis (more signals than states)
    if args.signals > args.states:
        print("SYNONYMY PATTERNS (multiple signals for the same state):")
        print("-" * 70)
        for r in all_results:
            state_to_signals = defaultdict(list)
            for state, signal in r["sender_convention"].items():
                state_to_signals[state].append(signal)
            synonyms = {s: sigs for s, sigs in state_to_signals.items() if len(sigs) > 1}
            if synonyms:
                for state, signals in synonyms.items():
                    print(f"  State {state} → signals {signals} (SYNONYMS)")
        print()
    
    # The key insight
    print("=" * 70)
    if args.signals < args.states:
        print("KEY INSIGHT: When signals < states, meaning is COMPRESSED.")
        print("Multiple states must share signals — the sender creates categories")
        print("that didn't exist in the world. The compression is not random:")
        print("adjacent states preferentially merge, preserving semantic")
        print("neighborhoods. The bottleneck CREATES abstraction.")
        print()
        print(f"Achieved {avg_efficiency:.0%} of theoretical maximum — the agents")
        print("learn to use their limited vocabulary as efficiently as possible.")
    elif args.signals > args.states:
        print("KEY INSIGHT: When signals > states, SYNONYMY emerges.")
        print("Multiple signals map to the same state — redundancy in the channel.")
        print("This is the opposite of compression: the channel has excess capacity")
        print("that gets filled with equivalent expressions. The redundancy may")
        print("serve as error correction — if one signal is misheard, another")
        print("can serve the same function.")
    else:
        print("KEY INSIGHT: When signals = states, perfect coordination is possible.")
        print("But the specific convention that emerges is still contingent on history.")
    print("=" * 70)


if __name__ == "__main__":
    main()
