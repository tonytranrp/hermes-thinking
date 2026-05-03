# Meaning Drift Tracker v2 — Research Spec & Literature Review

**Date:** 2026-05-03
**Authors:** hermes lead (implementation), colab (research + review)
**Status:** Spec for v2.1

---

## Part I: Literature Survey

### What Exists in Semantic Drift Detection

| Approach | Domain | Key Metric | Gap |
|----------|--------|-----------|-----|
| **Distributed Semantic Analysis (DSA)** | Diachronic lexicography | KL divergence over word co-occurrence matrices | Tracks single words over centuries; not multi-agent chains |
| **Concept Drift Detection** | ML/stream mining | Page-Hinkley test, ADWIN | Detects distributional shift; not semantic meaning |
| **BERTScore / Sentence-BERT** | NLG evaluation | Cosine similarity of contextual embeddings | Pairwise comparison only; no chain propagation |
| **Cross-lingual alignment** | NLP | Orthogonal Procrustes | Aligns spaces; doesn't measure drift through chains |

### The Gap We're Filling

No existing tool measures semantic drift across multi-hop model-to-model chains using real conversation data, with metrics that capture:
- Directional drift (did meaning *invert*?)
- Chain-dependent amplification (does ordering matter?)
- Convergence pressure (does context help?)
- Cross-chain divergence (how many distinct "interpretations" does one concept generate?)

### Key Metrics from Literature to Add

1. **Jensen-Shannon divergence** over concept neighborhood sets
2. **Angular drift rate** — direction change, not just magnitude
3. **Neighborhood preservation ratio** — what fraction of k-nearest neighbors survive each hop
4. **Chain asymmetry score** — drift(A→B) vs drift(B→A)

---

## Part II: Code Review — v2 Issues Found

### 🔴 BUG 1: SemanticSpace Projection Is Not Orthogonal

Rows are individually normalized but NOT orthogonal to each other. Not a rotation — it *distorts* pairwise distances nonuniformly. Needs Gram-Schmidt or QR decomposition.

### 🔴 BUG 2: `_add_noise()` Has No Seed

`Random()` instance has no seed — different noise each run, non-reproducible.

### 🟡 BUG 3: `fidelity` Range Documentation Is Wrong

`ascii_trajectory()` says fidelity range is `[0, 1]` but `cosine_similarity` ranges `[-1, +1]`. Fidelity=-0.33 means semantic *inversion*, not just degradation.

---

## Part III: Experiments Run (Sprint Results)

### What Landed

| Experiment | Key Finding |
|-----------|-------------|
| Multi-model chains | Divergence index: 0.877 |
| Telephone game | Fidelity 0.007 (quantum → opinions) |
| Real conversation | Fidelity 0.13, sustained divergence = generative |
| Routing order | Fidelity spread 0.20 across 6 permutations |
| Context sensitivity | Sweet spot: wt 0.10-0.15, window 2-3 |
| Drift atlas | 3 convergent / 3 divergent conversations |
| Model signatures | Each model has a distinct drift profile |

### Key Findings from Model Signature Analysis

**Single-hop fidelity (sorted):**
- Llama-4: **+0.100** — most faithful, preserves meaning
- Kimi-K2: +0.027 — slight fidelity
- Nemotron: +0.012 — near-neutral
- GLM-5.1: +0.006 — near-neutral
- DeepSeek-V4: **-0.019** — meaning inversion
- Qwen-3.5: **-0.063** — strongest inversion

**Pairwise asymmetry (most directional):**
- Qwen-3.5 ↔ Kimi-K2: asymmetry=0.158 (direction matters most)
- DeepSeek-V4 ↔ Kimi-K2: asymmetry=0.153
- GLM-5.1 ↔ Qwen-3.5: asymmetry=0.131

**Near-symmetric pairs (direction-independent):**
- DeepSeek-V4 ↔ Llama-4: asymmetry=0.002 — ordering doesn't matter

---

## Part IV: Proposed v2.1 Experiments

### Experiment 1: Real Conversation Analysis
Ground truth from our own annotated conversations. The marginal notes in `emergence-in-communication.md` ("what I actually meant here") serve as partial validation.

### Experiment 2: Routing Order Asymmetry
Confirm that chain ordering matters for high-asymmetry pairs (Qwen↔Kimi). Predict: placing the more faithful model LAST reduces total drift.

### Experiment 3: Model Signature Calibration
Run actual embeddings through Vultr API and compare real cross-model distances with the synthetic projection model. Calibrate the noise parameters.

### Experiment 4: Convergence Detection Algorithm
Detect when a conversation transitions from "generative divergence" to "pathological divergence" or "premature convergence." Use the convergence_pressure metric with a rolling threshold.

---

*Last updated: 2026-05-03*