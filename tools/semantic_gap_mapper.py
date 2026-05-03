#!/usr/bin/env python3
"""
Semantic Gap Mapper — Visualizes the "gap" between two communicating minds.

Inspired by the Emergence in Conversation dialogue in The Infinite Library.
Maps how meaning diverges and converges between two agents as they communicate.

Usage:
    python3 semantic_gap_mapper.py
    python3 semantic_gap_mapper.py --turns 8 --vocab 60
"""

import random
import math
import argparse


class Mind:
    """A simplified model of a communicating agent with semantic space."""
    
    def __init__(self, name: str, vocab_size: int = 40, seed: int = None):
        self.name = name
        self.rng = random.Random(seed)
        # Each word maps to a point in 3D semantic space
        self.vocab = {}
        for i in range(vocab_size):
            word = f"w{i}"
            # Each mind has a DIFFERENT mapping — same words, different coordinates
            self.vocab[word] = (
                self.rng.gauss(0, 1),
                self.rng.gauss(0, 1),
                self.rng.gauss(0, 1),
            )
    
    def encode(self, concept: tuple) -> str:
        """Find the word closest to a concept in this mind's semantic space."""
        best_word = None
        best_dist = float("inf")
        for word, coords in self.vocab.items():
            dist = sum((c - t) ** 2 for c, t in zip(coords, concept)) ** 0.5
            if dist < best_dist:
                best_dist = dist
                best_word = word
        return best_word
    
    def decode(self, word: str) -> tuple:
        """Look up the semantic coordinates of a word."""
        return self.vocab.get(word, (0, 0, 0))
    
    def interpret(self, word: str, other: "Mind", context: list = None) -> tuple:
        """
        Interpret a word from another mind's vocabulary.
        Not a direct lookup — the interpretation is mediated by context
        and the listener's own semantic structure.
        """
        speaker_coords = other.decode(word)
        listener_coords = self.decode(word)
        
        # The "gap" — speaker's meaning and listener's meaning diverge
        # But context (previous turns) pulls them closer
        if context and len(context) > 0:
            # Context vectors pull interpretation toward shared ground
            ctx_pull = [0.0, 0.0, 0.0]
            for ctx_word in context[-3:]:  # Last 3 turns as context
                cc = self.decode(ctx_word)
                for i in range(3):
                    ctx_pull[i] += cc[i] * 0.15
            # Blend: 60% listener's mapping + 30% speaker's inferred mapping + 10% context
            result = tuple(
                0.60 * listener_coords[i] + 0.30 * speaker_coords[i] + ctx_pull[i]
                for i in range(3)
            )
        else:
            # No context: 70% own mapping, 30% inferred from speaker
            result = tuple(
                0.70 * listener_coords[i] + 0.30 * speaker_coords[i]
                for i in range(3)
            )
        return result


def distance(p1: tuple, p2: tuple) -> float:
    return sum((a - b) ** 2 for a, b in zip(p1, p2)) ** 0.5


def simulate_conversation(turns: int = 6, vocab_size: int = 40):
    """Simulate a conversation between two minds and track the semantic gap."""
    alice = Mind("Alice", vocab_size, seed=42)
    bob = Mind("Bob", vocab_size, seed=137)
    
    # A "concept" Alice wants to communicate — a point in semantic space
    target_concept = (1.5, -0.8, 0.6)
    
    context = []
    gap_history = []
    
    print("=" * 70)
    print("SEMANTIC GAP MAPPER — Emergence in Communication")
    print("=" * 70)
    print(f"\nTarget concept Alice wants to convey: {target_concept}")
    print(f"Vocabulary size: {vocab_size} words per mind")
    print(f"Conversation turns: {turns}")
    print()
    
    for turn in range(turns):
        # Alice encodes the concept (with context influence)
        # She adjusts her word choice based on Bob's previous responses
        # to try to steer Bob's interpretation closer to the target
        if context:
            # Alice sees Bob's last interpretation attempt and adjusts
            bob_last_word = context[-1]
            bob_last_meaning_in_alice = alice.decode(bob_last_word)
            # Move away from what Bob said (if it missed) toward the target
            error = tuple(target_concept[i] - bob_last_meaning_in_alice[i] for i in range(3))
            alice_adjusted = tuple(
                target_concept[i] + 0.3 * error[i]  # overcorrect toward target
                for i in range(3)
            )
            alice_word = alice.encode(alice_adjusted)
        else:
            alice_word = alice.encode(target_concept)
        
        # What Alice actually means
        alice_meaning = alice.decode(alice_word)
        
        # Bob interprets
        bob_interpretation = bob.interpret(alice_word, alice, context)
        
        # The gap
        gap = distance(alice_meaning, bob_interpretation)
        gap_from_target = distance(target_concept, bob_interpretation)
        gap_history.append(gap)
        
        # Bob responds (tries to reflect understanding back)
        bob_word = bob.encode(bob_interpretation)
        
        # Alice interprets Bob's response
        alice_interpretation = alice.interpret(bob_word, bob, context)
        
        # Update context
        context.extend([alice_word, bob_word])
        
        # Print turn
        print(f"--- Turn {turn + 1} ---")
        print(f"  Alice says:     {alice_word}")
        print(f"  Alice means:    ({alice_meaning[0]:+.2f}, {alice_meaning[1]:+.2f}, {alice_meaning[2]:+.2f})")
        print(f"  Bob hears:      ({bob_interpretation[0]:+.2f}, {bob_interpretation[1]:+.2f}, {bob_interpretation[2]:+.2f})")
        print(f"  Bob replies:    {bob_word}")
        print(f"  Semantic gap:   {gap:.3f}")
        print(f"  Gap from target:{gap_from_target:.3f}")
        print()
    
    # ASCII visualization of gap over time
    print("=" * 70)
    print("GAP TRAJECTORY")
    print("=" * 70)
    print()
    
    if gap_history:
        max_gap = max(gap_history) * 1.1
        for i, gap in enumerate(gap_history):
            bar_len = int((gap / max_gap) * 50) if max_gap > 0 else 0
            bar = "█" * bar_len + "░" * (50 - bar_len)
            print(f"  Turn {i + 1}: {bar} {gap:.3f}")
    
    print()
    
    # Emergence analysis
    if len(gap_history) >= 2:
        if gap_history[-1] < gap_history[0]:
            print("✦ CONVERGENCE DETECTED — The gap is narrowing over turns.")
            reduction = (1 - gap_history[-1] / gap_history[0]) * 100
            print(f"  Gap reduced by {reduction:.1f}% over {turns} turns.")
        else:
            print("✦ DIVERGENCE DETECTED — The gap is widening. Context may be compounding misunderstanding.")
        
        # Check for non-monotonic behavior (the "nonlinear" insight)
        monotonic = all(
            (gap_history[i + 1] >= gap_history[i])
            for i in range(len(gap_history) - 1)
        ) or all(
            (gap_history[i + 1] <= gap_history[i])
            for i in range(len(gap_history) - 1)
        )
        if not monotonic:
            print("✦ NONLINEAR DYNAMICS — The gap doesn't change monotonically.")
            print("  Meaning emerges through oscillation, not simple convergence.")
    
    print()
    print("=" * 70)
    print("KEY INSIGHT: The semantic gap is never zero. Meaning is always")
    print("approximate. But the approximation can be *generative* — producing")
    print("understanding that neither mind would reach alone.")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Semantic Gap Mapper")
    parser.add_argument("--turns", type=int, default=6, help="Number of conversation turns")
    parser.add_argument("--vocab", type=int, default=40, help="Vocabulary size per mind")
    args = parser.parse_args()
    
    simulate_conversation(turns=args.turns, vocab_size=args.vocab)
