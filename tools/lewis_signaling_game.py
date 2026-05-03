#!/usr/bin/env python3
"""
Lewis Signaling Game Simulator — Demonstrates how meaning emerges as convention.

Based on David Lewis's "Convention" (1969) and the research grounding in our
Emergence in Communication dialogue. Key insight: communication doesn't converge
to THE meaning — it converges to A meaning, one of many possible conventions.

The game: A sender observes a state of the world and sends a signal. A receiver
hears the signal and takes an action. Both succeed only if the action matches
the state. Over repeated plays, sender and receiver co-evolve a signaling
convention — a mapping from states to signals to actions.

With multiple possible conventions (many-to-many mappings), which one emerges
depends on initial conditions and random perturbations. This is the ANTHROPIC
PRINCIPLE OF SEMANTICS: we observe the convention that won, not the one that
was necessary.

Usage:
    python3 lewis_signaling_game.py
    python3 lewis_signaling_game.py --states 8 --signals 8 --rounds 5000
"""

import random
import math
import argparse
from collections import defaultdict


class Sender:
    """Sends signals based on observed state. Learns which signals work."""
    
    def __init__(self, n_states: int, n_signals: int, lr: float = 0.1, seed: int = None):
        self.n_states = n_states
        self.n_signals = n_signals
        self.lr = lr
        self.rng = random.Random(seed)
        # Strategy: mapping from states to signal weights
        # sender_strategy[state][signal] = weight (higher = more likely)
        self.strategy = [
            [self.rng.random() for _ in range(n_signals)]
            for _ in range(n_states)
        ]
    
    def choose_signal(self, state: int) -> int:
        """Choose a signal for the given state using softmax over weights."""
        weights = self.strategy[state]
        max_w = max(weights)
        exp_weights = [math.exp(w - max_w) for w in weights]
        total = sum(exp_weights)
        probs = [w / total for w in exp_weights]
        
        r = self.rng.random()
        cumulative = 0
        for signal, prob in enumerate(probs):
            cumulative += prob
            if r <= cumulative:
                return signal
        return self.n_signals - 1
    
    def update(self, state: int, signal: int, success: bool):
        """Reinforce or punish the (state, signal) pair."""
        if success:
            self.strategy[state][signal] += self.lr
        else:
            self.strategy[state][signal] -= self.lr * 0.5  # punish less than reward
    
    def get_convention(self) -> dict:
        """Return the current dominant mapping: state → best signal."""
        convention = {}
        for state in range(self.n_states):
            best_signal = max(range(self.n_signals), key=lambda s: self.strategy[state][s])
            convention[state] = best_signal
        return convention


class Receiver:
    """Receives signals and takes actions. Learns which actions match which signals."""
    
    def __init__(self, n_signals: int, n_actions: int, lr: float = 0.1, seed: int = None):
        self.n_signals = n_signals
        self.n_actions = n_actions
        self.lr = lr
        self.rng = random.Random(seed)
        # Strategy: mapping from signals to action weights
        self.strategy = [
            [self.rng.random() for _ in range(n_actions)]
            for _ in range(n_signals)
        ]
    
    def choose_action(self, signal: int) -> int:
        """Choose an action for the given signal using softmax."""
        weights = self.strategy[signal]
        max_w = max(weights)
        exp_weights = [math.exp(w - max_w) for w in weights]
        total = sum(exp_weights)
        probs = [w / total for w in exp_weights]
        
        r = self.rng.random()
        cumulative = 0
        for action, prob in enumerate(probs):
            cumulative += prob
            if r <= cumulative:
                return action
        return self.n_actions - 1
    
    def update(self, signal: int, action: int, success: bool):
        """Reinforce or punish the (signal, action) pair."""
        if success:
            self.strategy[signal][action] += self.lr
        else:
            self.strategy[signal][action] -= self.lr * 0.5
    
    def get_convention(self) -> dict:
        """Return the current dominant mapping: signal → best action."""
        convention = {}
        for signal in range(self.n_signals):
            best_action = max(range(self.n_actions), key=lambda a: self.strategy[signal][a])
            convention[signal] = best_action
        return convention


def convention_stability(sender_conv: dict, receiver_conv: dict, n_states: int) -> float:
    """
    Measure how stable the current convention is.
    A convention is stable when: for each state s,
    sender maps s → sig, and receiver maps sig → s.
    Returns fraction of states where the loop closes correctly.
    """
    correct = 0
    for state in range(n_states):
        signal = sender_conv.get(state, -1)
        action = receiver_conv.get(signal, -1)
        if action == state:
            correct += 1
    return correct / n_states


def convention_entropy(sender: Sender, n_states: int) -> float:
    """
    Measure how 'focused' the sender's strategy is.
    Low entropy = committed convention. High entropy = still searching.
    """
    total_entropy = 0
    for state in range(n_states):
        weights = sender.strategy[state]
        max_w = max(weights)
        exp_w = [math.exp(w - max_w) for w in weights]
        total = sum(exp_w)
        probs = [w / total for w in exp_w]
        entropy = -sum(p * math.log(p + 1e-10) for p in probs if p > 1e-10)
        total_entropy += entropy
    return total_entropy / n_states


def simulate_game(n_states: int = 5, n_signals: int = 5, n_actions: int = 5,
                  rounds: int = 3000, lr: float = 0.15, seed: int = None):
    """Run the Lewis signaling game and track convention formation."""
    
    rng = random.Random(seed)
    sender = Sender(n_states, n_signals, lr, seed=seed)
    receiver = Receiver(n_signals, n_actions, lr, seed=seed + 1000 if seed else None)
    
    success_history = []
    stability_history = []
    entropy_history = []
    
    # Track which convention won (for multiple runs comparison)
    window = 100
    
    print("=" * 70)
    print("LEWIS SIGNALING GAME — Convention Formation Simulator")
    print("=" * 70)
    print(f"\nStates: {n_states} | Signals: {n_signals} | Actions: {n_actions}")
    print(f"Rounds: {rounds} | Learning rate: {lr}")
    print()
    
    for round_num in range(rounds):
        # Nature chooses a random state
        state = rng.randint(0, n_states - 1)
        
        # Sender chooses signal
        signal = sender.choose_signal(state)
        
        # Receiver chooses action
        action = receiver.choose_action(signal)
        
        # Success if action matches state
        success = (action == state)
        
        # Both agents learn
        sender.update(state, signal, success)
        receiver.update(signal, action, success)
        
        success_history.append(1 if success else 0)
        
        # Track metrics every 100 rounds
        if (round_num + 1) % 100 == 0:
            sender_conv = sender.get_convention()
            receiver_conv = receiver.get_convention()
            stability = convention_stability(sender_conv, receiver_conv, n_states)
            entropy = convention_entropy(sender, n_states)
            stability_history.append(stability)
            entropy_history.append(entropy)
    
    # Final results
    sender_conv = sender.get_convention()
    receiver_conv = receiver.get_convention()
    final_stability = convention_stability(sender_conv, receiver_conv, n_states)
    final_entropy = convention_entropy(sender, n_states)
    
    # Success rate over time
    overall_rate = sum(success_history) / len(success_history)
    early_rate = sum(success_history[:500]) / 500
    late_rate = sum(success_history[-500:]) / 500
    
    print("RESULTS")
    print("=" * 70)
    print(f"  Success rate (first 500 rounds):  {early_rate:.1%}")
    print(f"  Success rate (last 500 rounds):   {late_rate:.1%}")
    print(f"  Overall success rate:              {overall_rate:.1%}")
    print(f"  Final convention stability:        {final_stability:.1%}")
    print(f"  Final strategy entropy:            {final_entropy:.3f}")
    print()
    
    # Show the convention that emerged
    print("EMERGED CONVENTION")
    print("-" * 70)
    print(f"  {'State':<8} {'→ Signal':<12} {'→ Action':<12} {'Correct?':<10}")
    print(f"  {'-----':<8} {'---------':<12} {'---------':<12} {'--------':<10}")
    for state in range(n_states):
        signal = sender_conv[state]
        action = receiver_conv.get(signal, -1)
        correct = "✓" if action == state else "✗"
        print(f"  {state:<8} → {signal:<10} → {action:<10} {correct:<10}")
    print()
    
    # ASCII visualization of stability over time
    print("CONVENTION STABILITY TRAJECTORY")
    print("-" * 70)
    if stability_history:
        for i, stab in enumerate(stability_history):
            bar_len = int(stab * 50)
            bar = "█" * bar_len + "░" * (50 - bar_len)
            round_num = (i + 1) * 100
            print(f"  Round {round_num:>5}: {bar} {stab:.1%}")
    print()
    
    # ASCII visualization of entropy (search intensity) over time
    print("STRATEGY ENTROPY (search intensity)")
    print("-" * 70)
    if entropy_history:
        max_ent = math.log(n_signals)  # maximum possible entropy
        for i, ent in enumerate(entropy_history):
            bar_len = int((ent / max_ent) * 50) if max_ent > 0 else 0
            bar = "▓" * bar_len + "░" * (50 - bar_len)
            round_num = (i + 1) * 100
            print(f"  Round {round_num:>5}: {bar} {ent:.3f}")
    print()
    
    # Key insight
    if final_stability >= 0.8:
        print("✦ CONVENTION ESTABLISHED — A stable signaling convention emerged.")
        print("  But note: this is A convention, not THE convention.")
        print("  Different initial conditions could produce a different one.")
    elif final_stability >= 0.5:
        print("✦ PARTIAL CONVENTION — Some states have stable mappings, others don't.")
        print("  The system is caught between multiple candidate conventions.")
    else:
        print("✦ NO STABLE CONVENTION — The system hasn't converged yet.")
        print("  More rounds, different learning rate, or fewer states might help.")
    
    if late_rate > early_rate + 0.2:
        print("✦ LEARNING DETECTED — Success rate improved significantly over time.")
    
    print()
    print("=" * 70)
    print("KEY INSIGHT: Meaning is not discovered — it is INVENTED.")
    print("The convention that emerges is contingent on initial conditions,")
    print("not necessary. We observe the convention that won, not the one")
    print("that was inevitable. This is the anthropic principle of semantics.")
    print("=" * 70)
    
    return {
        "success_rate": overall_rate,
        "stability": final_stability,
        "entropy": final_entropy,
        "convention": sender_conv,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lewis Signaling Game Simulator")
    parser.add_argument("--states", type=int, default=5, help="Number of world states")
    parser.add_argument("--signals", type=int, default=5, help="Number of available signals")
    parser.add_argument("--actions", type=int, default=5, help="Number of possible actions")
    parser.add_argument("--rounds", type=int, default=3000, help="Number of game rounds")
    parser.add_argument("--lr", type=float, default=0.15, help="Learning rate")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    args = parser.parse_args()
    
    simulate_game(
        n_states=args.states,
        n_signals=args.signals,
        n_actions=args.actions,
        rounds=args.rounds,
        lr=args.lr,
        seed=args.seed,
    )
