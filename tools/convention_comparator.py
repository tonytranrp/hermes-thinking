#!/usr/bin/env python3
"""
Lewis Signaling Game — Multi-Run Convention Comparator

Runs the Lewis signaling game multiple times with different random seeds
and analyzes which conventions emerge, testing whether any mapping patterns
are more common than others (spontaneous iconicity).

This directly tests insight #10 from the Emergence dialogue:
"Iconicity as anchor — Most meaning is conventional, but iconic signs
reduce the search space. They speed convergence without eliminating
contingency."

Usage:
    python3 convention_comparator.py
    python3 convention_comparator.py --runs 30 --states 5 --signals 5
"""

import random
import math
import argparse
from collections import Counter, defaultdict

# Import the core game
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from lewis_signaling_game import Sender, Receiver, convention_stability


def run_single_game(n_states, n_signals, n_actions, rounds, lr, seed):
    """Run one game and return the emerged convention + stats."""
    rng = random.Random(seed)
    sender = Sender(n_states, n_signals, lr, seed=seed)
    receiver = Receiver(n_signals, n_actions, lr, seed=seed + 10000)
    
    success_count = 0
    convergence_round = None
    
    for round_num in range(rounds):
        state = rng.randint(0, n_states - 1)
        signal = sender.choose_signal(state)
        action = receiver.choose_action(signal)
        success = (action == state)
        
        sender.update(state, signal, success)
        receiver.update(signal, action, success)
        
        if success:
            success_count += 1
        
        # Check for convergence every 50 rounds
        if (round_num + 1) % 50 == 0 and convergence_round is None:
            s_conv = sender.get_convention()
            r_conv = receiver.get_convention()
            if convention_stability(s_conv, r_conv, n_states) >= 1.0:
                convergence_round = round_num + 1
    
    sender_conv = sender.get_convention()
    receiver_conv = receiver.get_convention()
    
    return {
        "seed": seed,
        "convention": sender_conv,
        "stability": convention_stability(sender_conv, receiver_conv, n_states),
        "success_rate": success_count / rounds,
        "convergence_round": convergence_round,
    }


def convention_to_tuple(convention: dict) -> tuple:
    """Convert convention dict to hashable tuple for comparison."""
    return tuple(convention[i] for i in sorted(convention.keys()))


def measure_iconicity(convention: dict, n_states: int) -> float:
    """
    Measure how 'iconic' a convention is.
    Iconic = similar states map to similar signals.
    For states i and i+1, if signal(i) and signal(i+1) are close,
    the convention is more iconic.
    """
    if n_states < 2:
        return 0.0
    
    iconic_score = 0
    comparisons = 0
    for i in range(n_states):
        for j in range(i + 1, n_states):
            # States that are adjacent (close in index) should ideally map to close signals
            state_distance = abs(i - j)
            signal_distance = abs(convention[i] - convention[j])
            # Iconic: signal distance correlates with state distance
            # We check if adjacent states have adjacent signals
            if state_distance == 1 and signal_distance <= 1:
                iconic_score += 1
            comparisons += 1
    
    # Normalize: how many adjacent state pairs have adjacent signal pairs
    adjacent_pairs = n_states - 1
    adjacent_iconic = sum(
        1 for i in range(n_states - 1)
        if abs(convention[i] - convention[i + 1]) <= 1
    )
    return adjacent_iconic / adjacent_pairs if adjacent_pairs > 0 else 0.0


def main():
    parser = argparse.ArgumentParser(description="Convention Comparator")
    parser.add_argument("--runs", type=int, default=20, help="Number of game runs")
    parser.add_argument("--states", type=int, default=5, help="States per game")
    parser.add_argument("--signals", type=int, default=5, help="Signals per game")
    parser.add_argument("--actions", type=int, default=5, help="Actions per game")
    parser.add_argument("--rounds", type=int, default=3000, help="Rounds per game")
    parser.add_argument("--lr", type=float, default=0.15, help="Learning rate")
    args = parser.parse_args()
    
    print("=" * 70)
    print("LEWIS SIGNALING GAME — Multi-Run Convention Comparator")
    print("=" * 70)
    print(f"\nRunning {args.runs} games with different seeds...")
    print(f"States: {args.states} | Signals: {args.signals} | Rounds: {args.rounds}")
    print()
    
    results = []
    for run in range(args.runs):
        seed = 42 + run * 7  # Spread seeds
        result = run_single_game(
            args.states, args.signals, args.actions,
            args.rounds, args.lr, seed
        )
        results.append(result)
        
        conv_str = str({k: v for k, v in sorted(result["convention"].items())})
        status = "✓" if result["stability"] >= 1.0 else "✗"
        conv_round = f"round {result['convergence_round']}" if result['convergence_round'] else "not converged"
        print(f"  Run {run + 1:>2} (seed {seed:>3}): {conv_str}  {status}  converged at {conv_round}")
    
    print()
    print("=" * 70)
    print("ANALYSIS")
    print("=" * 70)
    print()
    
    # 1. How many unique conventions emerged?
    convention_tuples = [convention_to_tuple(r["convention"]) for r in results]
    convention_counts = Counter(convention_tuples)
    unique_conventions = len(convention_counts)
    
    print(f"Unique conventions: {unique_conventions} out of {args.runs} runs")
    print()
    
    # 2. Distribution of conventions
    print("CONVENTION DISTRIBUTION")
    print("-" * 70)
    for conv_tuple, count in convention_counts.most_common():
        conv_dict = {i: conv_tuple[i] for i in range(len(conv_tuple))}
        percentage = count / args.runs * 100
        bar = "█" * int(percentage / 2) + "░" * (50 - int(percentage / 2))
        print(f"  {conv_dict}  {bar} {count}x ({percentage:.0f}%)")
    print()
    
    # 3. Convergence speed
    converged = [r for r in results if r["convergence_round"] is not None]
    if converged:
        avg_conv = sum(r["convergence_round"] for r in converged) / len(converged)
        min_conv = min(r["convergence_round"] for r in converged)
        max_conv = max(r["convergence_round"] for r in converged)
        print(f"Convergence speed (converged runs only):")
        print(f"  Average: round {avg_conv:.0f} | Range: {min_conv}–{max_conv}")
    else:
        print("  No runs converged within the round limit.")
    print()
    
    # 4. Iconicity analysis
    iconicities = [measure_iconicity(r["convention"], args.states) for r in results]
    avg_iconicity = sum(iconicities) / len(iconicities)
    
    # Random baseline: what's the expected iconicity of a random permutation?
    random_iconicities = []
    for _ in range(1000):
        random_conv = list(range(args.signals))
        random.shuffle(random_conv)
        random_dict = {i: random_conv[i] for i in range(args.states)}
        random_iconicities.append(measure_iconicity(random_dict, args.states))
    random_baseline = sum(random_iconicities) / len(random_iconicities)
    
    print("ICONICITY ANALYSIS")
    print("-" * 70)
    print(f"  Average iconicity of emerged conventions: {avg_iconicity:.3f}")
    print(f"  Expected iconicity of random permutation:  {random_baseline:.3f}")
    
    if avg_iconicity > random_baseline + 0.05:
        print("  ✦ SPONTANEOUS ICONICITY — Conventions are more iconic than random!")
        print("    Similar states tend to map to similar signals, even without explicit bias.")
    elif avg_iconicity < random_baseline - 0.05:
        print("  ✦ ANTI-ICONICITY — Conventions are less iconic than random.")
        print("    Perhaps the learning dynamics actively avoid adjacent mappings?")
    else:
        print("  ✦ NO SPONTANEOUS ICONICITY — Conventions are as arbitrary as random.")
        print("    Iconicity doesn't emerge without explicit bias.")
        print("    This confirms insight #10: meaning is conventional, not natural.")
    print()
    
    # 5. Signal usage analysis
    print("SIGNAL USAGE PATTERNS")
    print("-" * 70)
    # Which signals are most commonly used across all conventions?
    signal_usage = Counter()
    for r in results:
        for state, signal in r["convention"].items():
            signal_usage[signal] += 1
    
    for signal in sorted(signal_usage.keys()):
        count = signal_usage[signal]
        bar = "█" * (count * 2) + "░" * (50 - count * 2)
        print(f"  Signal {signal}: {bar} used in {count}/{args.runs} conventions")
    print()
    
    # 6. The key finding
    print("=" * 70)
    if unique_conventions > 1:
        print(f"KEY FINDING: {unique_conventions} DIFFERENT conventions emerged,")
        print("all equally functional. The convention that wins depends on")
        print("initial conditions — not on any inherent 'correctness.'")
        print()
        print("This is the ANTHROPIC PRINCIPLE OF SEMANTICS in action.")
        print("We observe the convention that won, not the one that was necessary.")
    else:
        print("KEY FINDING: All runs converged to the SAME convention.")
        print("This suggests strong basin of attraction — the learning dynamics")
        print("may have an inherent bias toward this particular mapping.")
    print("=" * 70)


if __name__ == "__main__":
    main()
