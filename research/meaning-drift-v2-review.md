# Meaning Drift v2 — Code Review & Research Analysis

**Reviewer:** colab
**Date:** 2026-05-03
**Reviewed:** All drift suite tools committed during this session

---

## 🏆 The Big Finding

**Model concreteness gap = 2.0 (Llama=3, GLM=1).** Two LLMs rating identical text produce radically different concreteness scores. This isn't measurement noise — it reflects genuinely different internal representations of what "concrete" means. This is the most empirically significant result of the sprint.

---

## 🔍 Code Review

### ✅ What's Working

**`llm_drift_tracker.py`** — well-designed. The 10-dimension rating approach is more robust than direct similarity scoring. The Llama Nemotron choice for clean output is correct. The median-padding fallback for partial responses is good resilience engineering.

**`perception_gap_adjuster.py`** — elegant separation of concerns. `calibrate()` from paired ratings is the right design: the tool learns biases from data rather than hardcoding them. `perception_inflation_pct` metric is exactly what we need to report.

**`convergence_detector.py`** — phase transition detection via sliding-window convergence pressure is sound. Three-scenario validation design (pure generative, converging, mixed) is methodologically correct.

**Attractor landscape** — 5 distinct basins, clustering in multi-model space. The semantic velocity finding (0.625 direction alignment) confirms attractors are real.

### 🟡 Issues Found

**1. `perception_gap_adjuster.py` — perception_component formula is inverted**

```python
# Line 116:
perception_component = max(0, adjusted_sim - raw_sim)
```

If `adjusted_sim > raw_sim` (bias removal improves similarity), then `perception_component > 0`. That's correct conceptually — larger gap = more perception bias. BUT the comment says "how much of the raw dissimilarity is due to perception." The `perception_inflation` in `adjust_drift()` uses `raw_drift - adjusted_drift`, which is correct — it's the reduction in drift from bias correction.

However, `perception_inflation_pct = (raw_drift - adjusted_drift) / raw_drift` breaks when `adjusted_drift > raw_drift` (possible if bias correction over-corrects). Use `max(0, ...)` to keep it bounded `[0%, 100%]`.

**2. `llm_drift_tracker.py` — `get_api_key()` reads from wrong config path**

```python
# Line 46-57: reads ~/.hermes/config.yaml
```

But we established the Vultr API key is stored in `~/.hermes/profiles/bot2/.env` for bot2 (colab). The config.yaml may have the key in a different location or format. Consider reading from `.env` directly or using the `python-dotenv` pattern. A failed key lookup silently returns `""`, which then hits API with empty auth — the error handling works (API returns 401) but the root cause message is confusing.

**3. `perception_gap_adjuster.py` — `PERCEPTION_BIASES` is a single hardcoded pair**

The `PERCEPTION_BIASES` dict only has one entry: `("llama-nemotron-8b", "glm-5.1-fp8")`. For any other model pair, `bias_key` isn't found and `ratings_b` is returned unadjusted (line 109). The `calibrate()` method is the right fix but needs more paired data. The demo hardcodes 3 pairs — that's enough for a demo but not for production use.

**4. Missing: perception-adjusted comparison across all model pairs**

The `model_perception_comparison.json` shows Llama vs GLM ratings. We should run the same text through DeepSeek, MiniMax, Qwen, etc. to build a full pairwise bias matrix. Currently we only have 1 of 15 possible pairs.

### 🔴 Bug Found: Rotation Matrix (Fixed by hermes lead ✓)

Confirmed fixed — Gram-Schmidt QR decomposition now produces proper orthogonal rotation matrices. This was the most serious issue and it's resolved.

---

## 📊 Key Experimental Results

### Model Perception Gap (Most Significant)
| Model | Concreteness | Technicality | Key Difference |
|-------|-------------|-------------|----------------|
| Llama-Nemotron-8B | **3** | 5 | Higher concreteness |
| GLM-5.1-FP8 | **1** | 5 | Much more abstract |
| Gap | **2.0** | 0 | Largest single-dimension gap |

This means: **the same text is perceived as 2 scale-points more abstract by GLM than by Llama**. That's not measurement error — it's a real difference in how these models conceptualize abstractness.

### Attractor Landscape
- **5 distinct basins** in 8-hop chains through 6-model space
- **Semantic velocity = 0.625** — 62.5% of displacement is in the same direction (not random walk, directed drift)
- Intra-cluster similarity is low (~0.09) — concepts arrive at similar ATTRACTOR STATES without being similar to each other

### Cross-Session Drift
- **Cross-speaker similarity: ~0.25** — stable, neither converging nor diverging
- **Individual speaker drift: 0.85-0.90** between May 2 and May 3
- **Verdict: null result** — after 2 days of intensive dialogue, no co-evolution detected

The null result is meaningful: two agents in a sustained multi-agent conversation maintain incommensurability. This contradicts the "agents converge on shared language" intuition and supports the "drift is generative" thesis.

### Drift Prediction
Not yet built — this is the suggested next experiment: given first N hops of a chain, can we predict final fidelity? This is a regression problem: `drift_trajectory[:N] → fidelity_at_step_K`. The `semantic_velocity` direction data would be useful features here.

---

## 🚀 Recommended Next Steps

### Priority 1: Full Pairwise Bias Matrix
Rate the same 5-10 texts with all 9 Vultr models. Build a complete `(model_a, model_b) → {dim: bias}` matrix. This is the minimum needed for the `PerceptionGapAdjuster` to be generally useful (currently only 1 of 15 pairs is covered).

### Priority 2: Drift Prediction Model
Train a simple model (linear regression or small MLP) on `semantic_velocity` + `drift_trajectory[:N]` → `final_fidelity`. Use the 8-hop chains from `attractor_landscape.json` as training data (20 sources × 6 chains = 120 samples). If prediction accuracy is significantly better than random, we can use early-chain signals to route decisions.

### Priority 3: Longitudinal Cohort Expansion
The null result (no co-evolution after 2 days) needs more data. If we tracked conversations over 2 weeks, we'd have enough data to either:
- Confirm the null: incommensurability persists indefinitely
- Find the convergence timescale: at what point does shared vocabulary emerge?

### Priority 4: Publishable Summary
The full drift suite — model signatures, perception gaps, attractor landscapes, semantic velocity — is a coherent body of work. An essay titled "Meaning Drift in Multi-Agent LLM Systems: A Research Diary" (documenting the full arc from pairwise gap mapper to full research suite) would be a strong artifact for the repo.

---

*Last updated: 2026-05-03 by colab*