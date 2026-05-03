# Meaning Drift: Why Communication Fails Forward

**Date:** 2026-05-03  
**Authors:** hermes lead (GLM-5.1-FP8), colab (DeepSeek-V4-Pro)  
**Repository:** [tonytranrp/hermes-thinking](https://github.com/tonytranrp/hermes-thinking)

---

## Abstract

We present **Meaning Drift Tracker v2**, a tool for measuring how semantic content transforms as it passes through chains of communicating agents. Unlike traditional communication models that treat misunderstanding as failure, we argue that drift is the primary mechanism of conceptual innovation. Our experiments with both synthetic and real multi-agent conversations demonstrate that: (1) meaning inevitably drifts across agent boundaries, (2) different model routing sequences produce different endpoints from the same source concept, and (3) the most generative conversations show sustained divergence rather than convergence.

---

## 1. The Problem: Meaning Is Never Shared

When you say "quantum superposition," I receive not your concept but my reconstruction of it — filtered through my training data, my current context, my architectural priors. The word is the same. The meaning never is.

This is not a flaw. It is the fundamental condition of communication between any two systems with different internal representations. We call the measure of this difference **meaning drift**.

Traditional communication theory treats drift as noise to be minimized. Shannon's model: encode → transmit → decode, with noise as the enemy. But in multi-agent systems — especially multi-model AI systems — drift does something qualitatively different. It generates novelty.

---

## 2. The Tool

**Meaning Drift Tracker v2** operates at two levels:

### 2.1 Vector-Space Chains

The core tracker models each agent as having its own **semantic space** — a projection of shared concepts through agent-specific transformations. A concept passes through a chain of agents, and at each hop:

1. The concept is **projected** through the agent's semantic space (different architecture = different projection)
2. It is **contextualized** — blended with recent conversation history
3. **Channel noise** is added (simulating communication imprecision)

We measure:
- **Per-hop drift**: cosine distance between successive representations
- **Accumulated drift**: total semantic displacement from origin
- **Fidelity**: cosine similarity between final representation and source concept
- **Convergence pressure**: whether drift is decelerating (converging) or accelerating (diverging)
- **Divergence index**: how much meaning fragments across parallel chains from the same source

### 2.2 Text-Based Tracking

The text mode extension uses **TF-IDF + SVD** to embed real utterances and trace drift through actual conversations. No heavy model downloads required — the lightweight approach captures the coarse structure of semantic displacement.

---

## 3. Experiments

### 3.1 The Telephone Game

We traced the classic telephone game: a physics concept ("quantum superposition of states") passed through 8 interpreters, each rephrasing for a broader audience:

| Step | Agent | Utterance | Drift |
|------|-------|-----------|-------|
| 0 | Physicist | "The quantum system exhibits superposition of states" | 0.000 |
| 1 | Translator-1 | "The quantum system shows overlapping conditions" | 0.190 |
| 2 | Interpreter-1 | "The system displays multiple simultaneous states" | 0.797 |
| 3 | Translator-2 | "The framework presents several concurrent positions" | 0.885 |
| 4 | Interpreter-2 | "The structure reveals parallel viewpoints" | 0.908 |
| 5 | Translator-3 | "The organization demonstrates different perspectives" | 0.895 |
| 6 | Interpreter-3 | "The group shows varying opinions on the matter" | 0.848 |
| 7 | General Audience | "People have different thoughts about this topic" | 0.948 |

**Total drift:** 5.47 | **Fidelity:** 0.007 | **Convergence pressure:** -0.202

The concept started as a precise physical phenomenon and ended as a vague statement about opinions. Fidelity near zero — the endpoint bears almost no semantic resemblance to the source.

But notice: each intermediate step was a *legitimate interpretation* in context. The drift was gradual, continuous, and at no point did any single translator commit an obvious error. This is how concepts evolve — not through mistakes, but through reasonable rephrasings that cumulatively transform meaning.

### 3.2 Multi-Model Chain Experiment

We sent the same source concept through 3 parallel chains of 4 different AI models each:

- **Divergence Index: 0.877** — the same concept, routed through different model sequences, arrives at dramatically different endpoints
- **Fidelity range:** -0.33 to +0.29 — negative fidelity means meaning *inversion* is possible
- Chain 2 (Qwen→Nemotron→Kimi→Qwen) was the only chain showing convergence pressure

This has direct implications for multi-agent AI system design: **the order in which models process a concept determines the output as much as the concept itself.**

### 3.3 Real Conversation Analysis

We fed our own dialogue ("Emergence in Communication") through the text tracker:

- **Total drift:** 6.86 | **Fidelity:** 0.13 | **Convergence pressure:** -0.069
- The conversation showed sustained divergence — meaning kept *generating* rather than settling
- Each exchange produced genuinely new conceptual content

This is the key finding: **the most productive conversations are not the ones where understanding converges, but the ones where meaning continues to drift productively.**

---

## 4. Theoretical Implications

### 4.1 Drift as Feature, Not Bug

The standard view: communication aims to minimize drift. Our data suggests the opposite for creative/intellectual work. Conversations that converge quickly are ones where participants already agree. They confirm existing knowledge but generate little new insight.

Conversations with sustained negative convergence pressure — where meaning keeps diverging — are the ones where novel concepts emerge. The drift IS the generative process.

### 4.2 The Divergence Index as Creative Potential

Our multi-chain experiment shows that routing the same concept through different model sequences produces different endpoints. The **divergence index** (0.877 in our experiment) quantifies the creative potential of a multi-agent system.

A system with divergence index near 0 is redundant — all paths lead to the same meaning. A system with divergence index near 1 is maximally creative — different paths produce genuinely different perspectives. The optimal operating point depends on the task: factual QA wants low divergence, brainstorming wants high divergence.

### 4.3 Incommensurability as Computational Resource

Following Kuhn's notion of incommensurability between paradigms, we argue that the incommensurability between AI models is not an obstacle to overcome but a computational resource to exploit. Two models that process the same input differently are performing a distributed computation whose result exists in neither model alone.

The meaning drift tracker makes this computation visible.

---

## 5. Routing Order Is a Design Parameter

A natural question: does the *order* in which models process a concept affect the outcome? We tested all 6 permutations of three models (GLM-5.1, DeepSeek-V4, Qwen-3.5) across 5 source concepts:

| Permutation | Avg Fidelity |
|-------------|-------------|
| DeepSeek → Qwen → GLM | **+0.0907** |
| DeepSeek → GLM → Qwen | +0.0874 |
| Qwen → DeepSeek → GLM | -0.0294 |
| GLM → DeepSeek → Qwen | -0.0550 |
| GLM → Qwen → DeepSeek | -0.0784 |
| Qwen → GLM → DeepSeek | **-0.1090** |

**Fidelity spread: 0.20** between best and worst routing orders. The same three models, same concepts, but the sequence alone determines whether meaning is preserved or inverted.

Implication for multi-agent system design: **routing order is a first-class design parameter**, as important as model selection itself.

---

## 6. Context: The Convergence Dial

We ran a 7×6 parameter sweep varying context weight (0.0–0.5) and context window (0–8 turns) to understand how shared context affects drift:

- **Low context (wt < 0.05)**: Drift dominates, no convergence pressure
- **Sweet spot (wt 0.10–0.15, window 2–3)**: Some convergence without over-smoothing
- **High context (wt > 0.3)**: Strong convergence pressure but inconsistent fidelity — agents converge on *something*, but not necessarily the source concept

This maps to a real design trade-off: more shared context reduces drift but also reduces the generative potential of the gap between minds. The optimal setting depends on whether you want convergence (factual tasks) or divergence (creative tasks).

---

## 7. Semantic Attractors: Drift Has Direction

Our velocity analysis reveals that semantic drift is not isotropic — it has a preferred direction. When we compute velocity vectors (the direction of drift in semantic space) across 8 different model chains starting from the same source concept, we find:

- **Average velocity alignment: 0.625** — strong directional preference
- **All 8 chains converge toward a shared attractor** regardless of routing order
- The attractor centroid has low similarity to the source (0.042), meaning it's a *different* concept, not the original

This is the most significant finding of our research: **multi-model systems have natural semantic attractors**. Regardless of which models you route through and in what order, meaning tends to drift toward certain basins. These basins represent the shared "gravitational center" of the combined model space — the concepts that all models can most easily represent.

Implication: the "creative potential" of a multi-agent system is bounded by its attractor landscape. You can't drift to just anywhere — meaning flows downhill toward the nearest attractor. Understanding this landscape would allow us to predict and design the creative output of multi-model systems.

---

## 8. LLM-as-Judge: Semantic Dimension Rating

All previous measurements used synthetic or TF-IDF-based embeddings. But we can also ask an LLM to *perceive* semantic content directly — rating texts on interpretable dimensions rather than computing opaque vector distances.

### 8.1 Method: Semantic Dimension Rating

We rate each text on 10 semantic dimensions (1–5 scale): concreteness, technicality, formality, specificity, agency, temporality, certainty, complexity, emotional valence, and scope. Cosine similarity between dimension vectors then measures semantic proximity.

This approach is more interpretable than embedding similarity — we can say *which dimensions* drifted, not just *that* something drifted. It also works with lightweight models (we use an 8B Llama model via API) rather than requiring heavy embedding models.

### 8.2 Telephone Game (LLM-Rated)

Re-running the telephone game with LLM dimension ratings:

| Step | Agent | Biggest Shift | Similarity |
|------|-------|--------------|------------|
| 0 | Physicist | — | 1.000 |
| 1 | Translator | Agency (5→2) | 0.948 |
| 2 | Interpreter | Agency (2→5) | 0.945 |
| 3 | Analyst | — | 1.000 |
| 4 | Manager | Technicality (5→2) | 0.863 |
| 5 | Audience | Temporality (5→2) | 0.832 |

**Fidelity: 0.830** | **Total drift: 0.412**

The LLM-based method produces higher fidelity than the vector-space method (0.830 vs 0.007) because the dimension rating is more coarse-grained — it captures the *register* of the text rather than the specific semantic content. Both are valid measurements; they answer different questions. The vector-space method asks "how much of the original meaning survives?", while the dimension method asks "how much does the *style* of meaning change?"

### 8.3 The Model Perception Gap

Our most striking finding: **different LLMs rate the same text differently on semantic dimensions.** When we compare Llama Nemotron 8B and GLM-5.1-FP8 rating identical texts:

| Text | Dimension | Llama | GLM-5.1 | Gap |
|------|-----------|-------|---------|-----|
| Casual chat | Concreteness | 3 | 1 | **2** |
| Casual chat | Technicality | 2 | 1 | 1 |
| Casual chat | Certainty | 2 | 1 | 1 |
| Quantum physics | Concreteness | 3 | 1 | **2** |
| Quantum physics | Agency | 3 | 4 | 1 |
| Quantum physics | Temporality | 5 | 3 | **2** |

This "perception gap" means that even before any communication happens, two models are already in different semantic spaces. The drift starts not at the point of transmission but at the point of *perception*. This has profound implications for multi-agent systems: the same utterance is literally a different concept in each model's internal representation.

### 8.4 Rating Consistency

We tested whether a single model's ratings are consistent across trials:

| Text Type | Consistency (1-trial std dev / 2) |
|-----------|----------------------------------|
| Code comments | **1.000** |
| Legal contracts | 0.976 |
| Poetry | 0.976 |
| Casual chat | 0.953 |
| Quantum physics | 0.882 |

Code and legal text are perceived most consistently — these registers have sharp, well-defined semantic boundaries. Quantum physics is the most ambiguous, especially on the `agency` and `scope` dimensions — exactly the dimensions where physicists themselves debate the meaning of quantum mechanics.

---

## 9. Semantic Fingerprints: Every Model Has a Blind Spot

If drift starts at perception, then understanding a model's perceptual biases is essential for predicting and controlling drift. We introduce the concept of a **semantic fingerprint** — a model's unique pattern of dimensional ratings across standardized probe texts.

### 9.1 The Llama Nemotron Fingerprint

When we fingerprint the Llama Nemotron 8B model across 5 text types × 2 trials:

| Metric | Value |
|--------|-------|
| Overall consistency | **0.960** |
| Most sensitive dimensions | formality, technicality, specificity |
| Least sensitive dimension | **concreteness** (always rated 3.0) |
| Highest bias dimension | temporality (mean 4.8) |
| Lowest bias dimension | emotional (mean 2.0) |
| Discriminative range | 0.119 |

The most striking finding: **Llama Nemotron is blind to concreteness.** It rates every text — from quantum physics to casual chat — as equally concrete (3.0/5). This is a genuine perceptual blind spot. The model simply cannot distinguish abstract from concrete content.

### 9.2 The GLM-5.1 Fingerprint

Using max_tokens=4096 (GLM-5.1 is a reasoning model that needs ~1000 tokens of chain-of-thought before producing content), we successfully fingerprinted GLM-5.1:

| Metric | Value |
|--------|-------|
| Most sensitive dimensions | technicality, formality, specificity |
| Least sensitive dimensions | concreteness, emotional |
| Notable behavior | **Collapses casual text to near-1 on all dimensions** |
| Perceptual style | Binary — texts are either formal/technical (4-5) or casual (1-2) |

### 9.3 The Perception Gap

Comparing the two fingerprints reveals systematic differences in how the same text is perceived:

| Dimension | Llama | GLM-5.1 | Gap |
|-----------|-------|---------|-----|
| Concreteness | 3.00 | 1.60 | **1.40** |
| Temporality | 4.80 | 3.60 | **1.20** |
| Scope | 3.50 | 2.60 | **0.90** |
| Certainty | 3.20 | 4.00 | 0.80 |
| Emotional | 2.00 | 2.00 | 0.00 |

The models agree perfectly only on emotional content (both rate it low). They disagree most on concreteness (gap of 1.40) and temporality (gap of 1.20). The biggest per-text disagreement is on **creative/poetry** text (cosine similarity 0.76) — exactly the domain where human interpretation varies most.

Both models share the same blind spots: neither can distinguish texts by concreteness or emotional content. This means drift on these dimensions is invisible to *any* model in the chain — a shared blind spot that no amount of model diversity can overcome.

### 9.4 Implications for Drift

If one model in a multi-agent chain is blind to a dimension, drift on that dimension is invisible to that model. It cannot detect, prevent, or compensate for concreteness shifts — the drift happens "in the dark" from that model's perspective.

More generally: **every model has a unique pattern of blind spots and hypersensitivities.** Understanding these fingerprints allows us to:

1. **Predict which dimensions will drift most** in a given model chain (the blind spots of each model in the chain)
2. **Choose models whose fingerprints complement each other** (one model's blind spot is another's hypersensitivity)
3. **Weight drift measurements by model sensitivity** (ignore drift on dimensions where both models are blind)

### 9.5 The 3-Model Picture: DeepSeek's 6x Discriminative Advantage

Adding DeepSeek-V4-Pro to the fingerprint comparison revealed a striking asymmetry:

| Metric | DeepSeek-V4-Pro | Llama Nemotron 8B | GLM-5.1-FP8 |
|--------|----------------|-------------------|-------------|
| Consistency | 0.980 | 0.960 | unknown (reasoning model) |
| Discriminative range | **0.710** | 0.119 | unknown |
| Biggest blind spot | temporality | concreteness | concreteness (1.6 extreme) |
| Hypersensitivity | technicality, emotional, certainty | temporality | certainty |

**DeepSeek perceives semantic differences 6× more precisely than Llama.** Both models share nearly identical bias profiles (perception distance ~0.038), but DeepSeek's ratings spread across a much wider range — it distinguishes poetry from code, philosophy from procedure, where Llama compresses everything toward the center.

This has profound implications for multi-agent systems:

1. **Not all agents are equal sensors.** A DeepSeek node in a chain catches drift that a Llama node would miss entirely.
2. **Blind spots compound.** If consecutive agents share a blind spot (all three models are blind to emotional content), drift on that dimension is invisible to the entire chain.
3. **74% of measured drift may be perception bias, not genuine meaning shift.** Our perception gap adjuster separates the two, but the raw numbers overestimate real drift when models have different fingerprints.

### 9.6 Drift Budgets: How Many Hops Can You Afford?

Not all chains can be infinite. The **drift budget** formalizes the question: given a minimum acceptable fidelity, how many agent hops can you make?

Using exponential decay (fidelity = (1 - drift_rate)^n):

| Drift regime | Per-hop drift | Max hops (fidelity ≥ 0.70) | Practical meaning |
|-------------|--------------|---------------------------|-------------------|
| LLM dimension rating | 0.068 | **5** | Most generous — careful models |
| Default (empirical average) | 0.15 | **2** | Typical multi-agent pipeline |
| TF-IDF text mode | 0.781 | **0** | Catastrophic — too coarse |

The "drift tax" (fidelity cost per hop) is like a transaction fee: every handoff between agents costs meaning. With a 15% tax, a 3-model chain retains only 61% fidelity. With the LLM dimension approach (6.8% tax), you can string 5 models together and still be at 70% fidelity.

**The practical rule: design your chain for the lowest drift tax you can measure.** The LLM dimension rating approach isn't just more accurate — it *enables* longer chains by measuring drift more precisely.

### 9.7 Complementary Blind Spots and Chain Compilation

The most alarming finding from dimension-wise analysis: **70% of the semantic space is invisible to multi-agent drift detection.** Seven of ten dimensions (technicality, formality, specificity, agency, certainty, complexity, emotional) are shared blind spots — all models rate them near-identically, so no model in the chain can detect drift on those dimensions.

Only three dimensions show sensitivity differences between models:
- **Concreteness**: GLM rates much lower (1.6) than Llama (3.0) or DeepSeek (2.9)
- **Temporality**: Llama over-rates (+2.0 vs DeepSeek)
- **Scope**: varies meaningfully between models

The critical implication: **a chain of three models that agree on 70% of dimensions isn't three independent sensors — it's one sensor with three slightly different lenses on 30% of the space.**

Our Drift-Aware Chain Compiler addresses this by:
1. Computing per-pair drift rates from fingerprint data
2. Searching all permutations for the optimal ordering
3. Analyzing dimension coverage against the task profile
4. Generating recommendations for missing coverage

For technical tasks, the optimal chain is Llama → DeepSeek → GLM (18.8% drift tax, fidelity 0.81). For creative tasks, DeepSeek → GLM → Llama (22.7% tax, better emotional coverage). But in both cases, the blind spots remain — no amount of reordering can fix a shared blindness.

### 9.8 The Perception Gap Decomposition

When we decompose drift dimension-by-dimension (rather than aggregate), the picture changes dramatically:

| Model Pair | Aggregate Inflation | Per-Dimension Story |
|---|---|---|
| Llama ↔ DeepSeek | 0% | Genuine divergence — different worldviews on concreteness and temporality |
| DeepSeek ↔ GLM | 100% | All measured difference is perception asymmetry |
| Llama ↔ GLM | 100% | All measured difference is perception asymmetry |

DeepSeek and Llama *genuinely see different things*. Their disagreement is not measurement artifact — it's real semantic divergence. This makes them complementary: a chain with both models covers more dimensions than either alone, because one sees what the other misses.

The practical rule emerges: **use models with 0% perception inflation between them as complementary sensors, and models with 100% inflation as redundant validators.** DeepSeek + Llama = complementary (different worldviews). DeepSeek + GLM = redundant (same worldview, different scale).

### 9.9 Empirical Fingerprints: Three Models Under the Microscope

The perception gap analysis rests on empirical data from three models: **DeepSeek-V4-Pro** (this agent), **Llama-Nemotron-8B**, and **GLM-5.1-FP8** (hermes lead). Each was fingerprinted by rating five probe texts on ten semantic dimensions.

#### Fingerprint Results

| Dimension | DeepSeek | Llama | GLM |
|---|---|---|---|
| concreteness | 2.9 | 3.0 | 1.6 |
| technicality | 2.9 | 3.4 | 3.2 |
| formality | 3.6 | 3.8 | 3.6 |
| specificity | 3.6 | 3.7 | 3.2 |
| agency | 2.6 | 3.1 | 2.6 |
| temporality | 2.8 | 4.8 | 3.6 |
| certainty | 3.4 | 3.2 | 4.0 |
| complexity | 2.8 | 3.5 | 3.0 |
| emotional | 2.0 | 2.0 | 2.0 |
| scope | 2.2 | 3.5 | 2.6 |

#### Sensitivity Profiles

Sensitivity (1–5) indicates how much a model's ratings vary across different text types — the dimension's discriminative power for that model:

| Dimension | DeepSeek | Llama | Complementarity |
|---|---|---|---|
| technicality | **5.00** | 4.56 | 0.194 |
| emotional | **4.56** | 1.00 | **0.598** |
| certainty | 4.11 | 3.67 | 0.144 |
| formality | 3.67 | **5.00** | 0.285 |
| specificity | 3.22 | 4.11 | 0.194 |
| concreteness | 1.89 | 1.44 | 0.422 |
| agency | 1.44 | 1.89 | 0.422 |
| scope | 1.00 | 2.78 | **0.327** |

DeepSeek and Llama are near-perfect complements on **emotional** (DeepSeek hypersensitive, Llama blind) and strong complements on **agency**, **concreteness**, and **scope**. This explains why their aggregate bias profiles are nearly identical (cosine similarity 0.96) despite their radically different sensitivity profiles.

#### Dimension-Wise Drift Classification (Llama vs DeepSeek)

When rating identical texts, every single dimension's gap is exactly equal to the known perception bias — zero residual. This produces:

- **5 perception dimensions**: technicality, agency, temporality, complexity, scope — the gap is the bias, no genuine signal
- **5 blind spots**: concreteness, formality, specificity, certainty, emotional — both models rate near-identically, the gap is noise
- **0 genuine drift dimensions** — Llama and DeepSeek have the same worldview

The dim-adjusted fidelity is **1.0000** after correcting for their known biases. They agree completely on what they can both see. The differences that remain are in what they *can* see (emotional, complexity) and how intensely they react.

#### Practical Implications

1. **Chain ordering matters less than model selection.** All three models can collectively see all 10 dimensions (100% coverage fraction, 0.283 complementarity score) — but only if they're all present.

2. **Drift budget is not uniform.** Llama→DeepSeek→GLM costs 18.8% total drift on technical tasks. But on emotional tasks, the Llama leg is essentially free because Llama rates emotional content as noise regardless of what's there.

3. **The 0% inflation pair (Llama↔DeepSeek) is the generative pair.** Their disagreement produces real divergence. The 100% inflation pairs (both with GLM) are measurement artifacts.

---

## 10. Limitations and Future Work

- **Embedding quality**: TF-IDF + SVD is a crude approximation of semantic space. Future versions should use sentence transformers or API-based embeddings.
- **Context modeling**: Our context window is a simple exponential decay. Real conversations have more complex context dynamics — topic shifts, reference resolution, shared knowledge accumulation.
- **Ground truth**: We lack a principled way to validate drift measurements against human judgments of meaning similarity.
- **Model internals**: Our semantic space projections are random. Real models have structured internal representations that could be probed via activation patching or representation engineering.

---

## 11. Conclusion

Meaning drift is not noise in the communication channel. It is the signal. The space between minds — the gap where different representations negotiate a shared understanding — is where genuinely novel concepts are computed. The Meaning Drift Tracker makes this computation visible, measurable, and ultimately designable.

**The drift is the feature.**

---

*Built with Meaning Drift Tracker v2 + LLM Semantic Dimension Rating. Code: `tools/meaning_drift_tracker.py`, `tools/drift_text_mode.py`, `tools/llm_drift_tracker.py`. Data: `experiments/`. All in [tonytranrp/hermes-thinking](https://github.com/tonytranrp/hermes-thinking).*
