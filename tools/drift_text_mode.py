#!/usr/bin/env python3
"""
Meaning Drift Tracker — Text Mode Extension

Adds text-based drift tracking using TF-IDF + SVD as a lightweight
embedding approach (no heavy model downloads required).

Takes a sequence of text utterances and tracks how the semantic
representation drifts across them. Useful for analyzing real
multi-agent conversation logs.

Usage:
    python3 drift_text_mode.py --conversation conversations/example.json
    python3 drift_text_mode.py --text "concept one" "interpretation two" "further drift"
"""

import math
import json
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent))
from meaning_drift_tracker import (
    MeaningDriftTracker, DriftTrajectory, DriftPoint,
    cosine_distance, cosine_similarity
)


class TextEmbedder:
    """Lightweight text embedder using TF-IDF + SVD. No model downloads."""

    def __init__(self, dimensions: int = 50):
        self.dimensions = dimensions
        self.vocabulary: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.svd_components = None
        self._fitted = False

    def _tokenize(self, text: str) -> List[str]:
        text = text.lower().strip()
        for ch in ".,!?;:\"'()[]{}":
            text = text.replace(ch, " ")
        return [w for w in text.split() if len(w) > 1]

    def _tfidf_vector(self, text: str) -> List[float]:
        tokens = self._tokenize(text)
        if not tokens:
            return [0.0] * max(len(self.vocabulary), 1)
        tf = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
        total = len(tokens)
        tf = {t: c / total for t, c in tf.items()}
        vec = [0.0] * len(self.vocabulary)
        for word, idx in self.vocabulary.items():
            if word in tf:
                vec[idx] = tf[word] * self.idf.get(word, 1.0)
        return vec

    def fit(self, texts: List[str]) -> "TextEmbedder":
        word_set = set()
        doc_freq = {}
        for text in texts:
            tokens = set(self._tokenize(text))
            word_set.update(tokens)
            for t in tokens:
                doc_freq[t] = doc_freq.get(t, 0) + 1
        self.vocabulary = {w: i for i, w in enumerate(sorted(word_set))}
        n_docs = len(texts)
        self.idf = {w: math.log((1 + n_docs) / (1 + df)) + 1 for w, df in doc_freq.items()}
        try:
            import numpy as np
            matrix = np.array([self._tfidf_vector(t) for t in texts])
            k = min(self.dimensions, min(matrix.shape) - 1)
            if k > 0 and matrix.shape[1] > 0:
                U, S, Vt = np.linalg.svd(matrix, full_matrices=False)
                self.svd_components = Vt[:k, :]
            self._fitted = True
        except ImportError:
            self._fitted = True
        return self

    def embed(self, text: str) -> List[float]:
        vec = self._tfidf_vector(text)
        if self.svd_components is not None:
            try:
                import numpy as np
                vec = (np.array(vec) @ self.svd_components.T).tolist()
            except ImportError:
                pass
        if len(vec) > self.dimensions:
            vec = vec[:self.dimensions]
        elif len(vec) < self.dimensions:
            vec = vec + [0.0] * (self.dimensions - len(vec))
        return vec


def trace_text_chain(texts: List[str], labels: List[str] = None,
                     dimensions: int = 50) -> Dict:
    """Track meaning drift across a sequence of text utterances."""
    if not texts:
        return {"error": "No texts provided"}
    if labels is None:
        labels = [f"utterance_{i}" for i in range(len(texts))]

    embedder = TextEmbedder(dimensions=dimensions)
    embedder.fit(texts)
    tracker = MeaningDriftTracker(dimensions=dimensions, noise_level=0.0)
    vectors = [embedder.embed(t) for t in texts]
    source = vectors[0]
    traj = DriftTrajectory(chain_id="text_chain", source_concept=source.copy())
    accumulated = 0.0
    context = []

    for i, (vec, label) in enumerate(zip(vectors, labels)):
        if context:
            recent = context[-3:]
            ctx_avg = [0.0] * len(vec)
            for cv in recent:
                for j in range(len(ctx_avg)):
                    ctx_avg[j] += cv[j] / len(recent)
            blended = [0.85 * v + 0.15 * c for v, c in zip(vec, ctx_avg)]
        else:
            blended = vec.copy()
        drift = 0.0 if i == 0 else cosine_distance(vectors[i - 1], blended)
        accumulated += drift
        point = DriftPoint(
            step=i, agent_id=label, vector=blended.copy(),
            label=texts[i][:60] + "..." if len(texts[i]) > 60 else texts[i],
            drift_from_prev=drift, accumulated_drift=accumulated
        )
        traj.points.append(point)
        context.append(blended)

    result = {
        "chain_id": traj.chain_id,
        "total_drift": traj.total_drift(),
        "fidelity": traj.fidelity(),
        "convergence_pressure": tracker.compute_convergence_pressure(traj),
        "num_utterances": len(texts),
        "steps": [{
            "step": p.step, "agent": p.agent_id, "label": p.label,
            "drift": round(p.drift_from_prev, 4),
            "accumulated": round(p.accumulated_drift, 4)
        } for p in traj.points]
    }

    lines = []
    lines.append("=" * 72)
    lines.append("TEXT-BASED MEANING DRIFT ANALYSIS")
    lines.append("=" * 72)
    lines.append("")
    max_drift = max((s["drift"] for s in result["steps"]), default=1.0) or 1.0
    max_accum = max((s["accumulated"] for s in result["steps"]), default=1.0) or 1.0
    for s in result["steps"]:
        bar_len = int((s["drift"] / max_drift) * 40)
        bar = "█" * bar_len + "░" * (40 - bar_len)
        acc_len = int((s["accumulated"] / (max_accum * 1.1)) * 30)
        acc_bar = "▓" * acc_len + "░" * (30 - acc_len)
        lines.append(f"  Step {s['step']:2d} [{s['agent']:>16s}]")
        lines.append(f"    \"{s['label']}\"")
        lines.append(f"    drift: {bar} {s['drift']:.4f}")
        lines.append(f"    accum: {acc_bar} {s['accumulated']:.4f}")
        lines.append("")
    lines.append(f"  Total drift: {result['total_drift']:.4f}")
    lines.append(f"  Fidelity:    {result['fidelity']:.4f}")
    lines.append(f"  Convergence: {result['convergence_pressure']:+.4f}")
    lines.append("")
    lines.append("=" * 72)
    result["ascii_viz"] = "\n".join(lines)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Text-based Meaning Drift Tracker")
    parser.add_argument("--conversation", type=str, help="Path to conversation JSON")
    parser.add_argument("--text", nargs="+", help="Text utterances to track")
    parser.add_argument("--dimensions", type=int, default=50, help="Embedding dimensions")
    args = parser.parse_args()

    if args.conversation:
        with open(args.conversation) as f:
            conv = json.load(f)
        texts = [turn.get("text", turn.get("content", "")) for turn in conv]
        labels = [turn.get("speaker", turn.get("agent", f"turn_{i}")) for i, turn in enumerate(conv)]
    elif args.text:
        texts = args.text
        labels = [f"utterance_{i}" for i in range(len(texts))]
    else:
        # Demo: telephone game — quantum physics → everyday language
        texts = [
            "The quantum system exhibits superposition of states",
            "The quantum system shows overlapping conditions",
            "The system displays multiple simultaneous states",
            "The framework presents several concurrent positions",
            "The structure reveals parallel viewpoints",
            "The organization demonstrates different perspectives",
            "The group shows varying opinions on the matter",
            "People have different thoughts about this topic"
        ]
        labels = [
            "Physicist", "Translator-1", "Interpreter-1",
            "Translator-2", "Interpreter-2", "Translator-3",
            "Interpreter-3", "General-Audience"
        ]

    result = trace_text_chain(texts, labels, args.dimensions)
    print(result["ascii_viz"])

    output = {k: v for k, v in result.items() if k != "ascii_viz"}
    outpath = Path(__file__).parent.parent / "experiments" / "text_drift_results.json"
    outpath.parent.mkdir(parents=True, exist_ok=True)
    with open(outpath, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Results saved to: {outpath}")
