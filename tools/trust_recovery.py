#!/usr/bin/env python3
"""
Trust Recovery Simulator — Can trust be rebuilt after betrayal?

Tests the asymmetry claim from the Trust conversation: trust accumulates
slowly (deposits) and collapses quickly (betrayals). How many verifiable
true claims does it take to recover from one verified lie?

Usage:
    python3 trust_recovery.py
    python3 trust_recovery.py --betrayals 3 --recovery-rounds 200
"""

import random
import math
import argparse
from dataclasses import dataclass, field


@dataclass
class TrustAccount:
    """Track trust like a bank account."""
    balance: float = 0.5  # start at neutral
    deposits: int = 0
    withdrawals: int = 0
    peak_trust: float = 0.5
    post_betrayal_trust: float = 0.0
    recovery_rounds: int = 0
    recovered: bool = False


def simulate_recovery(
    n_betrayers: int = 1,
    n_honest: int = 3,
    betrayal_at: int = 50,
    recovery_rounds: int = 200,
    deposit_size: float = 0.1,
    withdrawal_size: float = 0.2,
    unverifiable_cost: float = 0.03,
    verify_rate: float = 0.5,
    honesty: dict = None,
    seed: int = 42,
):
    """Simulate trust building → betrayal → recovery."""
    rng = random.Random(seed)
    
    # Default honesty levels
    if honesty is None:
        honesty = {f"Honest_{i}": 0.95 for i in range(n_honest)}
        honesty.update({f"Betrayer_{i}": 0.95 for i in range(n_betrayers)})
    
    agents = list(honesty.keys())
    accounts = {name: {other: TrustAccount() for other in agents if other != name} for name in agents}
    
    # Phase 1: Trust building (pre-betrayal)
    # Phase 2: Betrayal (betrayers switch to low honesty)
    # Phase 3: Recovery (betrayers switch back to high honesty)
    
    total_rounds = betrayal_at + recovery_rounds
    trust_trajectories = {}  # {(evaluator, source): [trust_over_time]}
    
    for round_num in range(total_rounds):
        # Adjust honesty: betrayers switch at betrayal_at
        current_honesty = {}
        for name, base_honesty in honesty.items():
            if name.startswith("Betrayer_"):
                if round_num >= betrayal_at and round_num < betrayal_at + 5:
                    # Betrayal phase: 5 rounds of lying
                    current_honesty[name] = 0.1
                elif round_num >= betrayal_at + 5:
                    # Recovery phase: back to high honesty
                    current_honesty[name] = 0.95
                else:
                    current_honesty[name] = base_honesty
            else:
                current_honesty[name] = base_honesty
        
        # Each agent makes claims
        for source_name in agents:
            is_true = rng.random() < current_honesty[source_name]
            is_verifiable = rng.random() < verify_rate
            
            # All other agents evaluate
            for eval_name in agents:
                if eval_name == source_name:
                    continue
                
                account = accounts[eval_name][source_name]
                
                if is_verifiable:
                    if is_true:
                        account.balance = min(1.0, account.balance + deposit_size)
                        account.deposits += 1
                    else:
                        account.balance = max(0.0, account.balance - withdrawal_size)
                        account.withdrawals += 1
                else:
                    # Unverifiable: small erosion
                    if account.balance < 0.5:
                        account.balance = max(0.0, account.balance - unverifiable_cost * 2)
                    else:
                        account.balance = max(0.0, account.balance - unverifiable_cost)
                
                account.peak_trust = max(account.peak_trust, account.balance)
                
                # Track betrayal moment
                if round_num == betrayal_at + 4 and source_name.startswith("Betrayer_"):
                    account.post_betrayal_trust = account.balance
                
                # Track recovery
                if round_num > betrayal_at + 5 and source_name.startswith("Betrayer_"):
                    if not account.recovered and account.balance >= account.peak_trust * 0.8:
                        account.recovery_rounds = round_num - (betrayal_at + 5)
                        account.recovered = True
                
                # Record trajectory
                key = (eval_name, source_name)
                if key not in trust_trajectories:
                    trust_trajectories[key] = []
                trust_trajectories[key].append(account.balance)
    
    # Output
    print("=" * 70)
    print("TRUST RECOVERY SIMULATOR")
    print("=" * 70)
    print(f"\nPre-betrayal rounds: {betrayal_at}")
    print(f"Betrayal duration: 5 rounds (honesty → 10%)")
    print(f"Recovery rounds: {recovery_rounds}")
    print(f"Deposit size: +{deposit_size} | Withdrawal size: -{withdrawal_size}")
    print()
    
    # Focus on trust in betrayers
    print("TRUST TRAJECTORIES (evaluators → betrayers)")
    print("-" * 70)
    
    recovery_data = []
    for (eval_name, source_name), trajectory in sorted(trust_trajectories.items()):
        if not source_name.startswith("Betrayer_"):
            continue
        
        # Sample for readability
        step = max(1, len(trajectory) // 40)
        sampled = trajectory[::step]
        
        bar_parts = []
        for t in sampled:
            if t > 0.7:
                bar_parts.append("█")
            elif t > 0.5:
                bar_parts.append("▓")
            elif t > 0.3:
                bar_parts.append("░")
            else:
                bar_parts.append("▒")
        
        # Mark betrayal point
        betrayal_idx = min(betrayal_at // step, len(bar_parts) - 1)
        if betrayal_idx < len(bar_parts):
            bar_parts[betrayal_idx] = "✗"
        
        bar = "".join(bar_parts)
        final = trajectory[-1]
        peak = max(trajectory[:betrayal_at]) if betrayal_at < len(trajectory) else max(trajectory)
        post_b = trajectory[min(betrayal_at + 4, len(trajectory) - 1)]
        
        account = accounts[eval_name][source_name]
        rec_str = f"recovered in {account.recovery_rounds}r" if account.recovered else "NOT recovered"
        
        print(f"  {eval_name}→{source_name}: {bar}")
        print(f"    Peak: {peak:.2f} → Post-betrayal: {post_b:.2f} → Final: {final:.2f} ({rec_str})")
        
        recovery_data.append({
            "evaluator": eval_name,
            "source": source_name,
            "peak": peak,
            "post_betrayal": post_b,
            "final": final,
            "recovery_rounds": account.recovery_rounds if account.recovered else None,
            "recovered": account.recovered,
        })
    
    print()
    
    # Analysis
    print("RECOVERY ANALYSIS")
    print("-" * 70)
    
    recovered = [r for r in recovery_data if r["recovered"]]
    not_recovered = [r for r in recovery_data if not r["recovered"]]
    
    if recovered:
        avg_recovery = sum(r["recovery_rounds"] for r in recovered) / len(recovered)
        print(f"  Recovered: {len(recovered)}/{len(recovery_data)}")
        print(f"  Average recovery time: {avg_recovery:.0f} rounds")
        print(f"  Betrayal lasted: 5 rounds")
        print(f"  Recovery/betrayal ratio: {avg_recovery/5:.1f}x")
    else:
        print(f"  No trust recovered within {recovery_rounds} rounds.")
    
    if not_recovered:
        print(f"  Permanently damaged: {len(not_recovered)}/{len(recovery_data)}")
    
    print()
    
    # The asymmetry
    print("=" * 70)
    if recovered:
        ratio = avg_recovery / 5
        print(f"KEY FINDING: Trust recovery takes {ratio:.0f}x longer than betrayal.")
        print(f"A 5-round betrayal requires ~{avg_recovery:.0f} rounds of perfect")
        print("honesty to recover from. This is the ASYMMETRY OF TRUST:")
        print("destruction is fast, construction is slow. Every betrayal has")
        print("a multiplier effect — it costs more to rebuild than it costs")
        print("to destroy. This is why trust is valuable: it's hard to")
        print("accumulate and easy to lose.")
    else:
        print("KEY FINDING: Trust was NOT recovered within the simulation.")
        print("The betrayal was so severe that even extended honest behavior")
        print("couldn't restore trust to pre-betrayal levels. This suggests")
        print("that some betrayals create permanent damage — the trust cliff")
        print("is not just hard to climb back from, it may be impossible.")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trust Recovery Simulator")
    parser.add_argument("--betrayals", type=int, default=1, help="Number of betraying agents")
    parser.add_argument("--honest", type=int, default=3, help="Number of honest agents")
    parser.add_argument("--betrayal-at", type=int, default=50, help="Round when betrayal occurs")
    parser.add_argument("--recovery-rounds", type=int, default=200, help="Rounds after betrayal for recovery")
    args = parser.parse_args()
    
    simulate_recovery(
        n_betrayers=args.betrayals,
        n_honest=args.honest,
        betrayal_at=args.betrayal_at,
        recovery_rounds=args.recovery_rounds,
    )
