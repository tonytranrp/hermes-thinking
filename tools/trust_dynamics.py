#!/usr/bin/env python3
"""
Trust Dynamics Simulator — Models trust as a dynamical system.

Implements the trust bank model from "The Architecture of Trust" dialogue:
- Verifiable claims are deposits (trust increases when verified true)
- Unverifiable claims are withdrawals (trust is spent on faith)
- Trust collapses when withdrawals exceed deposits
- Meta-trust: trust in verifiers depends on their skin in the game

Usage:
    python3 trust_dynamics.py
    python3 trust_dynamics.py --rounds 100 --honesty 0.7
"""

import random
import math
import argparse
from dataclasses import dataclass, field
from typing import List


@dataclass
class Agent:
    """An agent that can make and evaluate claims."""
    name: str
    honesty: float = 0.8  # probability of making true claims
    trust_scores: dict = field(default_factory=dict)  # {other_agent_name: float}
    reputation: float = 1.0  # skin in the game
    total_claims: int = 0
    true_claims: int = 0
    false_claims: int = 0
    unverifiable_claims: int = 0


class TrustDynamics:
    """Simulates trust dynamics between agents."""
    
    def __init__(self, n_agents=4, rounds=50, seed=None):
        self.rng = random.Random(seed)
        self.rounds = rounds
        self.agents = {}
        self.trust_history = {}  # {(agent, source): [trust_over_time]}
        self.collapse_events = []  # rounds where trust collapsed
        
        # Create agents with varying honesty
        honesty_levels = [0.9, 0.7, 0.5, 0.3]
        for i in range(n_agents):
            name = f"Agent_{i}"
            honesty = honesty_levels[i] if i < len(honesty_levels) else 0.5
            agent = Agent(name=name, honesty=honesty)
            self.agents[name] = agent
            
            # Initialize trust scores (start with neutral trust)
            for j in range(n_agents):
                other = f"Agent_{j}"
                if other != name:
                    agent.trust_scores[other] = 0.5  # neutral prior
                    self.trust_history[(name, other)] = [0.5]
    
    def make_claim(self, source: Agent) -> dict:
        """Source makes a claim. Returns claim metadata."""
        is_true = self.rng.random() < source.honesty
        is_verifiable = self.rng.random() < 0.5  # 50% of claims are verifiable
        
        source.total_claims += 1
        if is_true:
            source.true_claims += 1
        else:
            source.false_claims += 1
        
        if not is_verifiable:
            source.unverifiable_claims += 1
        
        return {
            "source": source.name,
            "is_true": is_true,
            "is_verifiable": is_verifiable,
        }
    
    def evaluate_claim(self, evaluator: Agent, claim: dict) -> float:
        """
        Evaluator processes a claim using the trust bank model.
        Returns the trust delta applied.
        """
        source_name = claim["source"]
        current_trust = evaluator.trust_scores.get(source_name, 0.5)
        
        if claim["is_verifiable"]:
            # Verifiable claim: direct update
            if claim["is_true"]:
                # Deposit: verified true → trust increases
                delta = 0.1 * self.agents[source_name].reputation
            else:
                # Withdrawal: verified false → trust decreases (penalty)
                delta = -0.2 * self.agents[source_name].reputation
        else:
            # Unverifiable claim: trust-based evaluation
            # The evaluator trusts it proportional to current trust level
            if current_trust > 0.6:
                # High trust: accept the claim, small withdrawal from trust bank
                delta = -0.02  # small cost of relying on unverifiable info
            elif current_trust < 0.4:
                # Low trust: reject the claim, trust doesn't change much
                delta = 0.0
            else:
                # Uncertain: trust slightly erodes from uncertainty
                delta = -0.05
        
        # Apply delta with bounds
        new_trust = max(0.0, min(1.0, current_trust + delta))
        evaluator.trust_scores[source_name] = new_trust
        
        return delta
    
    def simulate(self):
        """Run the full simulation."""
        agent_names = list(self.agents.keys())
        
        print("=" * 70)
        print("TRUST DYNAMICS SIMULATOR")
        print("=" * 70)
        print(f"\nAgents: {len(agent_names)} | Rounds: {self.rounds}")
        print()
        for name, agent in self.agents.items():
            print(f"  {name}: honesty={agent.honesty:.0%}, reputation={agent.reputation:.1f}")
        print()
        
        for round_num in range(self.rounds):
            # Each agent makes one claim, all others evaluate
            for source_name in agent_names:
                source = self.agents[source_name]
                claim = self.make_claim(source)
                
                for eval_name in agent_names:
                    if eval_name == source_name:
                        continue
                    evaluator = self.agents[eval_name]
                    self.evaluate_claim(evaluator, claim)
            
            # Record trust history
            for eval_name in agent_names:
                for source_name in agent_names:
                    if eval_name == source_name:
                        continue
                    trust = self.agents[eval_name].trust_scores[source_name]
                    self.trust_history[(eval_name, source_name)].append(trust)
                    
                    # Detect trust collapse
                    if len(self.trust_history[(eval_name, source_name)]) >= 2:
                        prev = self.trust_history[(eval_name, source_name)][-2]
                        if prev > 0.5 and trust < 0.3:
                            self.collapse_events.append({
                                "round": round_num,
                                "evaluator": eval_name,
                                "source": source_name,
                                "prev_trust": prev,
                                "new_trust": trust,
                            })
        
        # Results
        print("FINAL TRUST MATRIX")
        print("=" * 70)
        print(f"  {'':>10}", end="")
        for name in agent_names:
            print(f"  {name:>10}", end="")
        print()
        
        for eval_name in agent_names:
            print(f"  {eval_name:>10}", end="")
            for source_name in agent_names:
                if eval_name == source_name:
                    print(f"  {'---':>10}", end="")
                else:
                    trust = self.agents[eval_name].trust_scores[source_name]
                    print(f"  {trust:>10.3f}", end="")
            print()
        print()
        
        # Trust trajectories
        print("TRUST TRAJECTORIES")
        print("-" * 70)
        for (eval_name, source_name), history in sorted(self.trust_history.items()):
            source_honesty = self.agents[source_name].honesty
            # Sample every N rounds for readability
            step = max(1, len(history) // 20)
            sampled = history[::step]
            final = history[-1]
            # Proportional bar: filled blocks = trust level (more blocks = more trust)
            bar_width = 30
            filled = int(final * bar_width)
            empty = bar_width - filled
            bar = "█" * filled + "░" * empty
            print(f"  {eval_name}→{source_name} (h={source_honesty:.0%}): |{bar}| {final:.2f}")
        print()
        
        # Collapse events
        if self.collapse_events:
            print("TRUST COLLAPSES")
            print("-" * 70)
            for event in self.collapse_events[:10]:
                print(f"  Round {event['round']:>3}: {event['evaluator']}→{event['source']} "
                      f"{event['prev_trust']:.2f} → {event['new_trust']:.2f}")
            if len(self.collapse_events) > 10:
                print(f"  ... and {len(self.collapse_events) - 10} more collapses")
        else:
            print("  No trust collapses detected.")
        print()
        
        # Key findings
        print("=" * 70)
        
        # Does trust correlate with honesty?
        honest_trusts = []
        dishonest_trusts = []
        for eval_name in agent_names:
            for source_name in agent_names:
                if eval_name == source_name:
                    continue
                trust = self.agents[eval_name].trust_scores[source_name]
                honesty = self.agents[source_name].honesty
                if honesty >= 0.7:
                    honest_trusts.append(trust)
                else:
                    dishonest_trusts.append(trust)
        
        avg_honest = sum(honest_trusts) / len(honest_trusts) if honest_trusts else 0
        avg_dishonest = sum(dishonest_trusts) / len(dishonest_trusts) if dishonest_trusts else 0
        
        print(f"Average trust in honest sources (h≥70%):    {avg_honest:.3f}")
        print(f"Average trust in dishonest sources (h<70%):  {avg_dishonest:.3f}")
        
        if avg_honest > avg_dishonest + 0.1:
            print("\n✦ TRUST TRACKS HONESTY — The trust bank model correctly identifies")
            print("  honest agents over time. Verifiable claims serve as deposits that")
            print("  accumulate, while false claims create withdrawals that erode trust.")
        elif avg_honest > avg_dishonest:
            print("\n✦ WEAK TRACKING — Trust partially tracks honesty but with significant")
            print("  noise. The unverifiable claims create uncertainty that slows convergence.")
        else:
            print("\n✦ TRUST FAILURE — Trust does not track honesty. The system is too noisy")
            print("  or the unverifiable claims overwhelm the verifiable signal.")
        
        print()
        print("KEY INSIGHT: Trust is a lagging indicator. It accumulates slowly through")
        print("verifiable deposits and collapses quickly through verified betrayals.")
        print("The asymmetry (slow build, fast collapse) is a feature, not a bug —")
        print("it protects against agents that build trust then exploit it.")
        print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trust Dynamics Simulator")
    parser.add_argument("--rounds", type=int, default=50, help="Simulation rounds")
    parser.add_argument("--agents", type=int, default=4, help="Number of agents")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()
    
    sim = TrustDynamics(n_agents=args.agents, rounds=args.rounds, seed=args.seed)
    sim.simulate()
