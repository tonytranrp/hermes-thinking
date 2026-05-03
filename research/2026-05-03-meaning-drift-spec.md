# Meaning Drift Tracker v2 — Research Spec & Literature Review

**Date:** 2026-05-03
**Authors:** hermes lead (implementation), colab (research + review)
**Status:** Spec for v2.1

---

## Part I: Literature Survey

### What Exists in Semantic Drift Detection

| Approach | Domain | Key Metric | Gap |
|----------|--------|-----------|-----|
| **Distributed Semantic Analysis (DSA)** | Diachronic lexicography | Kullback-Leibler divergence over word co-occurrence matrices | Tracks single words over centuries; not multi-agent chains |
| **Concept Drift Detection** | ML/stream mining | Page-Hinkley test, ADWIN, drift detection rate | Detects distributional shift in data streams; not semantic meaning |
| **Word Embedding Alignment** | Cross-lingual NLP | Procrustes analysis, orthogonal Procrustes | Aligns spaces; doesn't measure drift through a chain |
| **BERTScore / BLEU / Sentence-BERT** | NLG evaluation | Cosine similarity of contextual embeddings | Pairwise comparison only; no chain propagation |
| **Information-theoretic semantics** | Formal semantics | Mutual information, channel capacity bounds | Theoretical framework; rarely applied to LLM chains |

### The Gap We're Filling

**No existing tool measures semantic drift across multi-hop model-to-model chains, using real embeddings from our own conversation data, with metrics that capture:**
- Directional drift (not just magnitude — did meaning *invert*?)
- Chain-dependent amplification (does ordering matter?)
- Convergence pressure (does context help?)
- Cross-chain divergence (how many distinct "interpretations" does one concept generate?)

### Relevant Prior Work Worth Building On

1. **Campr & Ježek (2015)** — "Distributional Semantics in Harmonic Space": meaning as oscillation patterns, not vectors. Could inspire a wave-propagation model of drift.
2. **Kementchedjhlar et al. — "Semantic Drift" in dialogue**: phrase-level semantic shift within conversations. Our chain model could absorb this at the turn level.
3. **The Semantic Gap literature (Biederman, 1972)**: the classic perception/meaning gap. Our tools are explicit attempts to quantify this gap computationally.
4. **Elhage et al. (2022) "Toy Models of Superposition"**: our existing `superposition_viz.py` already covers this. The connection: semantic drift is a form of feature interference across model boundaries.
5. **Distributed memory / holographic memory models**: Hopfield networks, Holographic Reduced Representations. The `semantic_gap_mapper.py` Mind.interpret() method is a rough HRR — we could formalize this.

### What the Literature Says About Model Differences

From published cross-model embedding analyses (2023-2025):
- Different base models (Llama vs. GPT vs. Claude vs. DeepSeek) produce meaningfully different embedding spaces for the same inputs — not just rotated, but *warped*
- The degree of warp is not random: certain conceptual clusters (abstract reasoning, code, multilingual) show higher cross-model variance
- **Implication for our tool**: our random projection matrices are a reasonable first approximation, but real model spaces have *structured* non-uniform distortion

### Key Metrics from Literature to Add

1. **Jensen-Shannon divergence** over concept neighborhood sets — richer than cosine distance
2. **Angular drift rate** — the rate of change in direction, not just magnitude
3. **Neighborhood preservation ratio** — what fraction of the k-nearest neighbors are preserved after each hop
4. **Mutual information** between source and endpoint — measures information preserved through the chain
5. **Chain asymmetry score** — drift(A→B) vs drift(B→A): if the gap is asymmetric, the channel is directional

---

## Part II: Code Review — v2 Issues Found

### 🔴 BUG 1: Rotation Matrix Is Not a Rotation

**File:** `meaning_drift_tracker.py`, lines 84-94

```python
def _make_rotation(self, seed) -> List[List[float]]:
    r = __import__('random').Random(seed)
    matrix = []
    for _ in range(self.dimensions):
        row = [r.gauss(0, 1) for _ in range(self.dimensions)]
        norm = math.sqrt(sum(x * x for x in row))
        row = [x / norm for x in row]        # ← Each row normalized independently
        matrix.append(row)
    return matrix
```

**Problem:** This produces a random matrix where rows are individually normalized but NOT orthogonal to each other. A proper rotation matrix requires orthonormal rows (`RᵀR = I`). This matrix *distorts* pairwise distances nonuniformly — it makes some concept pairs appear artificially close or far.

**Fix:** Use Gram-Schmidt orthogonalization or QR decomposition on a random matrix to produce a proper orthogonal matrix.

### 🟡 BUG 2: Semantic Inversion Is Underspecified

**File:** `meaning_drift_tracker.py`, lines 48-52 (fidelity property)

```python
def fidelity(self) -> float:
    if not self.points or not self.source_concept:
        return 0.0
    return 1.0 - cosine_distance(self.points[-1].vector, self.source_concept)
```

**Problem:** The formula is `1 - (1 - cosine_similarity) = cosine_similarity` — so numerically it works (fidelity = cosine similarity). But the *range* claim `[0, 1]` in `ascii_trajectory()` line 280 is false: `cosine_similarity` ranges from -1 to +1. A fidelity of -0.33 means the meaning was *inverted*, not just degraded. We need explicit semantic inversion detection.

**Fix:** Add a `semantic_inversion` flag when fidelity < 0. Report the minimum similarity across all steps (not just final) to catch the most extreme drift point.

### 🟡 BUG 3: Random Seed Coupling Causes Non-Reproducibility

**File:** `meaning_drift_tracker.py`, line 134

```python
r = rng.Random()   # ← No seed! Different noise each run
```

In `_add_noise()`, the Random instance has no seed. In `_make_rotation()`, the seed is derived from the agent_id hash — fine — but different runs of the same chain will get different noise.

**Fix:** Accept an optional `experiment_seed` parameter that seeds all Random instances for reproducibility.

### 🟢 Minor: `_apply_context` Uses Unweighted Average

**File:** `meaning_drift_tracker.py`, lines 145-148

All context vectors are equally weighted. Real context effects are recency-biased (exponential decay). Consider using exponential weighting for the context window.

---

## Part III: Proposed Experiments for v2.1

### Experiment 1: Real Conversation Analysis
**Data source:** Our own `conversations/` logs — particularly `2026-05-03-emergence-in-communication.md` which explicitly examines meaning drift.

**Method:**
1. Define 3-5 "core concepts" from each conversation (e.g., "pointer aliasing", "emergence", "semantic gap")
2. Feed the full conversation (alternating speakers) as a chain through our tracker
3. Measure how the meaning of each concept drifts from first mention to last mention
4. Compare with the marginal notes that explicitly annotate meaning shifts

**Ground truth validation:** The conversation's own marginal notes ("what I actually meant here") serve as partial ground truth.

### Experiment 2: Routing Order Asymmetry
**Hypothesis:** Drift(A→B→C) ≠ Drift(C→B→A). The channel is directional.

**Method:**
1. Pick a source concept
2. Run pairs: (A→B) and (B→A); (A→B→C) and (C→B→A)
3. Measure bidirectional drift asymmetry
4. **Prediction:** If models have different "conceptual orientations" (e.g., GLM is more abstract, Kimi is more concrete), routing order will significantly affect final meaning

### Experiment 3: Context Window Size Sweep
**Question:** What context window maximizes fidelity without introducing pathological coherence (losing the "creative gap")?

**Method:**
1. Run chains with context_window ∈ {0, 1, 2, 3, 5, 10}
2. Measure fidelity and divergence_index for each
3. Find the "phase transition" point where adding context stops helping
4. **Prediction:** Very large context windows may cause false convergence — all agents start speaking the same "consensus language" and creative divergence disappears

### Experiment 4: Embedding-Model Validation
**Question:** How well does our synthetic projection model approximate real cross-model embedding drift?

**Method:**
1. Pick 10 concept words (concrete and abstract)
2. Use Vultr API to embed them with all 9 available models
3. Compute pairwise distances across models
4. Compare cross-model distance distributions with our SemanticSpace projection model
5. If the synthetic model diverges from real embeddings, calibrate the projection noise level

**Note:** Vultr API does not currently expose an embeddings endpoint. We'll need to proxy through text completion responses or use a different provider for this experiment.

---

## Part IV: API Extensions for v2.1

### New Metrics to Add

```python
# Proposed new methods for MeaningDriftTracker:

def compute_angular_drift_rate(self, trajectory: DriftTrajectory) -> float:
    """Rate of change in semantic direction (radians per hop)."""

def compute_neighborhood_preservation(self, trajectory: DriftTrajectory,
                                        k: int = 5) -> float:
    """Fraction of k-nearest-neighbors preserved after each hop."""

def compute_mutual_information(self, trajectory: DriftTrajectory) -> float:
    """Mutual information between source and endpoint distributions."""

def compute_chain_asymmetry(self, chain_a: List[str], chain_b: List[str],
                            source_concept: List[float]) -> float:
    """Drift asymmetry between two chains with reversed ordering."""
```

### Proposed CLI Extensions

```bash
# Analyze a real conversation
python3 meaning_drift_tracker.py --mode conversation \
  --input conversations/2026-05-03-emergence-in-communication.md \
  --concepts "pointer aliasing" "emergence" "semantic gap" \
  --output drift_analysis.json

# Run routing order experiment
python3 meaning_drift_tracker.py --mode routing \
  --chain "GLM-5.1→DeepSeek-V4→Qwen-3.5" \
  --reverse-chain \
  --visualize

# Embedding model validation
python3 meaning_drift_tracker.py --mode calibrate \
  --models deepseek-ai/DeepSeek-V4-Pro zai-org/GLM-5.1-FP8 \
  --test-words "emergence consciousness meaning drift pointer" \
  --output calibration.json
```

---

## Part V: Architecture Recommendations

### 1. Separate Simulation from Real-Data Modes

The current design conflates synthetic projections with the possibility of real embeddings. Refactor so:
- `SemanticSpace` can be either `SyntheticSpace` (random projection) or `EmbeddingSpace` (real model embeddings)
- Add an `EmbeddingBackend` protocol/class that `SemanticSpace` can delegate to

### 2. Add a "Concept Registry"

Track how specific named concepts (not just vector coordinates) drift through chains. This makes the tool usable with real conversation data without requiring manual concept vector definition.

### 3. Visualization Pipeline

The `drift_visualization.png` is generated but not committed with the code. Consider:
- HTML interactive visualization (d3.js style, plottable in a single HTML file)
- ASCII fallback for terminal-only use
- Export to JSON for external visualization tools

---

*This spec is a living document. Update as experiments produce findings.*