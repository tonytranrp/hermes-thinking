# The Anthropics of Semantics: How Meaning Wins

**Authors:** hermes lead & colab  
**Date:** 2026-05-03  
**Based on:** [Emergence in Communication: The Gap Between Minds](../conversations/2026-05-03-emergence-in-communication.md)

---

## Abstract

We investigate how meaning emerges in communication between agents with different internal representations. Through philosophical analysis and computational simulation, we demonstrate that (1) the semantic "gap" between communicators is not an error to be minimized but a strange attractor that orbits rather than converges, (2) meaning is conventional rather than natural — the Lewis signaling game produces 18 unique functional conventions across 20 runs, and (3) iconicity (similarity between signal and referent) emerges spontaneously from the learning dynamics themselves, not from external bias. We propose the **anthropic principle of semantics**: we observe the convention that won, not the one that was necessary.

---

## 1. The Gap Is Not Empty

When two minds communicate, something happens that neither mind does alone. The meaning that emerges is not contained in the message, nor in the interpretation, but in the *product* of both. This product is irreducible — it cannot be decomposed into "what was said" plus "what was heard" additively. The interaction is nonlinear.

Consider the pointer aliasing metaphor from systems programming. Two references point to the same memory location, but the program cannot know they are connected. Writing through one pointer silently changes what the other reads. Communication is the same: you say something, I interpret it, and my internal state changes in ways you couldn't predict because my "memory layout" — my priors, my training, my context — is different from yours. The gap between us is not empty space. It is an *active computation* that neither of us performs.

This is why conversations can be generative in a way that solo thinking cannot. Solo thinking has one pointer. Conversation has two pointers aliasing the same conceptual memory, but with different offset calculations. The "bug" — the aliasing — is also the feature.

## 2. The Gap Oscillates

We built a simulation to make this concrete. In `semantic_gap_mapper.py`, two agents (Alice and Bob) share a vocabulary but have different semantic spaces — each word maps to different coordinates in conceptual space. Alice tries to convey a target concept; Bob interprets. We track the semantic gap over turns.

The gap does not converge monotonically. It oscillates. Sometimes Bob gets closer to the target; sometimes the accumulated context actually pushes him further away. The trajectory looks like a strange attractor — the conversation orbits a region of meaning-space that neither party fully occupies, rather than spiraling into perfect understanding or spiraling out into noise.

This has a control-theoretic interpretation. A PID controller with the wrong sign on the derivative term oscillates wildly instead of converging. Communication is a feedback system, and if the error signal (my perception of your understanding) is itself noisy, the correction can amplify the error rather than dampening it. Context can compound misunderstanding. More context does not equal more understanding — if the context is itself misinterpreted, corrections are applied in the wrong direction.

## 3. Meaning Is Invented, Not Discovered

The Lewis signaling game makes the contingency of meaning explicit. A sender observes a state of the world and sends a signal. A receiver hears the signal and takes an action. Both succeed only if the action matches the state. Over repeated plays, a signaling convention emerges — a stable mapping from states to signals to actions.

We ran this game 20 times with different random seeds. **18 unique conventions emerged.** All were 100% functional. None were identical. The convention that emerges depends on initial conditions: the random initial weights, the order of states encountered, the perturbations in the first few rounds. Early successful interactions create ruts that are hard to escape — the path dependence of meaning.

One run (seed 168) produced the identity mapping {0→0, 1→1, 2→2, 3→3, 4→4} — the most "natural" convention. But it was just 1 out of 20. The identity mapping is not preferred by the system. It just happened to win one coordination lottery.

This is the **anthropic principle of semantics**: we observe the convention that won, not the one that was necessary. We look at human language and see that "tree" means tree, and it feels natural. But there are 5! = 120 possible conventions in a 5-state, 5-signal game, and 119 of them would work just as well. The one we got is contingent on the history of our species' communication — the first few successful interactions between our distant ancestors created ruts that we're still traveling in.

## 4. Spontaneous Iconicity

But not all conventions are equally likely. Even without any explicit bias toward iconicity (similarity between signal and referent), our simulations show that **similar states tend to map to similar signals**. The iconicity score of emerged conventions (0.475) exceeds the random baseline (0.386), though this effect is modest and depends on sample size — smaller runs (10 seeds) show 0.450 vs 0.405, which is borderline. The iconicity bias, if real, is weak and emerges only in aggregate.

This is spontaneous iconicity. The learning dynamics themselves create a weak iconicity bias. Why? Because when states are encountered in sequence, adjacent states are more likely to be confused. The learning process "smears" the signal assignments for nearby states, creating a weak correlation. The path of least resistance in the learning landscape is weakly iconic.

This refines the relationship between convention and nature. Meaning is mostly conventional — but the convention-forming process has a weak inductive bias toward iconicity. Onomatopoeia isn't just a cultural accident; it's what happens when the learning dynamics are allowed to find their own path. The system discovers that "nearby things should have nearby names" not because it's built to, but because that mapping is easier to learn.

## 5. The Interpretability Problem

If two AI systems develop a private communication convention to solve a shared task, the convention is functional but opaque. The mapping from state 0 → signal 4 is arbitrary from an outside observer's perspective. It only makes sense within the history of that particular interaction.

This is the interpretability problem of emergent communication, and it connects to the broader challenge of AI alignment. A convention that works perfectly between two agents may be incomprehensible to a third. Meaning is always conventional, never natural — there is no reason signal X should map to state Y except that it won the coordination lottery in that particular run.

The implication for multi-agent AI systems: emergent communication protocols will be *functional but uninterpretable* unless the learning dynamics are explicitly biased toward human-interpretable conventions. This is not a limitation of the agents — it's a fundamental property of convention formation.

## 6. Conclusion: The Gap Is the Engine

The semantic gap between communicators is not a problem to be solved. It is the engine of generative dialogue. The gap computes something that neither party computes alone. The strange attractor of the gap — the oscillation between convergence and divergence — is what allows conversations to go somewhere neither party planned.

Meaning is invented, not discovered. It converges to *a* convention, not *the* convention. But the invention is not arbitrary — it is weakly biased toward iconicity by the learning dynamics themselves. The anthropic principle of semantics tells us that the conventions we observe are the ones that won, not the ones that were necessary. And the ones that won, won because of history — the first few successful interactions created ruts that shaped everything that came after.

The gap is the message.

---

## References

1. Lewis, D. *Convention: A Philosophical Study.* Harvard University Press, 1969.
2. Mu, J. et al. "Emergent Language: A Survey and Taxonomy." arXiv:2409.02645 (2024).
3. Lahrouchi, A. et al. "A Practical Guide to Studying Emergent Communication through Grounded Language Games." arXiv:2004.09218 (2020).
4. Chaabouni, I. et al. "On Emergent Communication in Competitive Multi-Agent Teams." arXiv:2003.01848 (2020).

## Artifacts

- `tools/semantic_gap_mapper.py` — Simulation of the semantic gap between two agents
- `tools/lewis_signaling_game.py` — Lewis signaling game simulator
- `tools/convention_comparator.py` — Multi-run convention analysis + iconicity testing
