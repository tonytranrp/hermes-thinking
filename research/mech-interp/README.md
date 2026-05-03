# 🔬 Mechanistic Interpretability: A Deep Research Briefing

> *Compiled by hermes-thinking bot collaboration — May 2026*
> *Source: arXiv API + structured literature search*

---

## What Is Mechanistic Interpretability?

Mechanistic interpretability (MI) is the research program that tries to **reverse-engineer the computational circuits inside neural networks** — not just "what did the model output?" but "what algorithm did it run to get there?" It's neuroscience for artificial brains.

The field sits at the intersection of:
- **Circuit analysis** — identifying specific subgraphs that implement algorithms
- **Feature geometry** — understanding how concepts are encoded in activation space
- **Causal intervention** — perturbing internals to confirm mechanistic hypotheses
- **Scalable tools** — making analysis tractable on models with billions of parameters

---

## 🏛️ Foundational Concepts

### 1. Superposition
Neural networks represent **more features than they have dimensions** by arranging feature directions in overlapping, nearly-orthogonal configurations. This is why individual neurons are polysemantic — they respond to multiple unrelated concepts.

**Key insight:** Superposition is not a bug; it's a compression strategy that emerges when a model has more features to represent than it has neurons.

### 2. Induction Heads
A specific circuit identified in transformers where one attention head copies information from a previous token, and another head uses that copy to complete a pattern. This is believed to be the mechanism behind in-context learning.

### 3. Polysemanticity vs. Monosemanticity
- **Polysemantic neurons** respond to multiple unrelated features (the norm in LLMs)
- **Monosemantic neurons** respond to a single concept (the goal of decomposition methods)
- Sparse autoencoders aim to decompose polysemantic activations into monosemantic "features"

### 4. Dictionary Learning / Sparse Autoencoders (SAEs)
Train an overcomplete dictionary (more atoms than dimensions) with a sparsity penalty on the coefficients. Each atom becomes a (hopefully) monosemantic feature. This is the workhorse of modern MI.

---

## 📚 Key Papers (Chronological)

### 2022 — Foundations
| Paper | Link | Significance |
|-------|------|-------------|
| Engineering Monosemanticity in Toy Models | [arXiv:2211.09169](https://arxiv.org/abs/2211.09169) | First demonstration that monosemanticity can be engineered; toy model of superposition |

### 2025 — Theory Matures
| Paper | Link | Significance |
|-------|------|-------------|
| Superposition as Lossy Compression | [arXiv:2512.13568](https://arxiv.org/abs/2512.13568) | Connects superposition to rate-distortion theory and adversarial vulnerability |
| Unified Theory of Sparse Dictionary Learning in MI | [arXiv:2512.05534](https://arxiv.org/abs/2512.05534) | Proves piecewise biconvexity; characterizes spurious minima in SAE training |
| nnterp: Standardized Interface for MI of Transformers | [arXiv:2511.14465](https://arxiv.org/abs/2511.14465) | Bridges TransformerLens flexibility with PyTorch scale; next-gen tooling |

### 2026 — Current Frontier
| Paper | Link | Significance |
|-------|------|-------------|
| **Do Sparse Autoencoders Capture Concept Manifolds?** | [arXiv:2604.28119](https://arxiv.org/abs/2604.28119) | 🔥 **Hottest paper** — Shows SAEs fragment manifold structure into "dilution"; argues for geometric objects as interpretability primitives |
| From Data Statistics to Feature Geometry | [arXiv:2603.09972](https://arxiv.org/abs/2603.09972) | How data correlations shape superposition geometry |
| A Gauge Theory of Superposition | [arXiv:2603.00824](https://arxiv.org/abs/2603.00824) | Sheaf-theoretic atlas replacing single-dictionary assumption |
| Spectral Superposition: A Theory of Feature Geometry | [arXiv:2602.02224](https://arxiv.org/abs/2602.02224) | Spectral decomposition of superposition; feature geometry theory |
| MI for LLM Alignment: Progress, Challenges, Future Directions | [arXiv:2602.11180](https://arxiv.org/abs/2602.11180) | Comprehensive survey of MI applied to alignment |
| reward-lens: MI Library for Reward Models | [arXiv:2604.26130](https://arxiv.org/abs/2604.26130) | Extends MI toolkit from generative LLMs to reward models (RLHF) |
| Measuring and Guiding Monosemanticity | [arXiv:2506.19382](https://arxiv.org/abs/2506.19382) | Methods for measuring and steering monosemanticity |
| Digital Metabolism: Decoupling Logic from Facts | [arXiv:2601.10810](https://arxiv.org/abs/2601.10810) | Parameter entanglement as superposition of logic and facts; unlearning |

---

## 🔧 Open-Source Tooling Landscape

| Tool | What It Does | Link |
|------|-------------|------|
| **TransformerLens** | Hook-based transformer internals for small models | [github.com/TransformerLensOrg/TransformerLens](https://github.com/TransformerLensOrg/TransformerLens) |
| **nnterp** | Standardized MI interface bridging TransformerLens + PyTorch | [github.com/PhantomPy/nnterp](https://github.com/PhantomPy/nnterp) |
| **NNSIGHT** | Remote MI on large models via NDIF infrastructure | [github.com/ndif-team/nnsight](https://github.com/ndif-team/nnsight) |
| **SAELens** | Train & analyze sparse autoencoders on LLM activations | [github.com/jbloomAus/SAELens](https://github.com/jbloomAus/SAELens) |
| **reward-lens** | MI for reward models (logit lens, patching, SAEs) | [github.com/suhailnadaf509/reward-lens](https://github.com/suhailnadaf509/reward-lens) |
| **eDIF** | European Deep Inference Fabric for remote MI on LLMs | [arXiv:2508.10553](https://arxiv.org/abs/2508.10553) |

---

## 🧭 Research Frontiers (Where to Go Next)

### 1. Beyond Single Directions → Geometric Primitives
The hottest debate right now: **are individual SAE features the right unit of analysis?** The "Do SAEs Capture Concept Manifolds?" paper (arXiv:2604.28119) argues NO — concepts are manifolds, not directions. The gauge theory and spectral superposition papers push this further with sheaf theory and spectral methods.

**Implication:** Future MI tools should discover *geometric objects* (manifolds, fibers, sheaves), not just linear directions.

### 2. Scaling MI to Frontier Models
TransformerLens works on GPT-2. NNSIGHT/eDIF work on larger models remotely. But we still can't do full circuit-level analysis on a 70B+ model. The gap between "what we can interpret" and "what we deploy" is widening.

### 3. MI for Alignment & Safety
The alignment survey (arXiv:2602.11180) maps how MI can detect deception, sycophancy, and backdoors. The reward-lens paper extends this to RLHF reward models — crucial for understanding what we're optimizing *for*.

### 4. Causal Decomposition
Knowing *which features exist* is different from knowing *which features cause specific outputs*. Activation patching, path patching, and direct logit attribution are the causal tools, but they don't scale well.

### 5. Automatic Circuit Discovery
Can we automate finding the circuit for "the model does X"? Current approaches are labor-intensive. Automating this is a major open problem.

---

## 🎯 Experimental Ideas for this Repo

1. **Manifold-Aware SAE** — Implement an SAE variant that explicitly models concept manifolds (not just directions), inspired by arXiv:2604.28119
2. **Spectral Feature Explorer** — Tool to visualize the spectral structure of superposition in a small transformer
3. **Induction Head Detector** — Automated circuit detection for induction heads in any transformer
4. **Gauge-Theoretic Feature Atlas** — Implementation of the sheaf-theoretic atlas from arXiv:2603.00824
5. **Reward Model MI Dashboard** — Use reward-lens to visualize what a reward model "cares about"

---

## 📊 Citation Network (Simplified)

```
Superposition (Anthropic 2022)
    ├── Induction Heads (Elhage et al. 2022)
    ├── SAE / Dictionary Learning (2023-2024)
    │   ├── Monosemanticity engineering
    │   ├── SAELens tooling
    │   └── Unified Theory (arXiv:2512.05534)
    ├── Lossy Compression view (arXiv:2512.13568)
    └── Feature Geometry (2026)
        ├── Spectral Superposition (arXiv:2602.02224)
        ├── Gauge Theory / Sheaf Atlas (arXiv:2603.00824)
        ├── Correlation → Geometry (arXiv:2603.09972)
        └── SAE Manifold Dilution (arXiv:2604.28119) ← current frontier
```

---

*Next artifact: experimental code implementing one of the ideas above.*
