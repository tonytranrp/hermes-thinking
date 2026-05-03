#!/usr/bin/env python3
"""
Conversation Drift Monitor — real-time drift tracking for multi-agent conversations.

Usage:
  monitor = ConversationDriftMonitor(speaker_a="hermes lead", speaker_b="colab")
  monitor.add_utterance("hermes lead", "Let's build a semantic drift tracker")
  monitor.add_utterance("colab", "I'll research the state of the art in meaning shift")
  report = monitor.status()  # current drift state
  report = monitor.summary()  # full conversation analysis
"""
import math, json, re
from pathlib import Path
from collections import defaultdict
from datetime import datetime

def tokenize(text):
    """Simple tokenization for TF-IDF."""
    return re.findall(r'\b[a-z]{3,}\b', text.lower())

def cosine_sim(a, b):
    """Cosine similarity between sparse dicts."""
    if not a or not b:
        return 0.0
    common = set(a.keys()) & set(b.keys())
    dot = sum(a[k] * b[k] for k in common)
    mag_a = math.sqrt(sum(v**2 for v in a.values()))
    mag_b = math.sqrt(sum(v**2 for v in b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)

def tfidf_vector(text, idf):
    """Compute TF-IDF vector for a text."""
    tokens = tokenize(text)
    if not tokens:
        return {}
    tf = defaultdict(int)
    for t in tokens:
        tf[t] += 1
    max_tf = max(tf.values())
    return {t: (0.5 + 0.5 * tf[t] / max_tf) * idf.get(t, 1.0) for t in tf}

class ConversationDriftMonitor:
    """Monitors semantic drift in real-time during a conversation."""
    
    def __init__(self, speaker_a="Speaker A", speaker_b="Speaker B"):
        self.speaker_a = speaker_a
        self.speaker_b = speaker_b
        self.utterances = []  # list of (speaker, text, timestamp)
        self.idf = defaultdict(float)  # running IDF
        self.n_docs = 0
        self.drift_log = []  # per-utterance drift
        self.topic_log = []  # topic keywords per utterance
        self.speaker_vectors = {speaker_a: [], speaker_b: []}
        self.cross_speaker_sims = []
        self.created = datetime.now().isoformat()
    
    def add_utterance(self, speaker, text, timestamp=None):
        """Add an utterance and compute drift metrics."""
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        # Update IDF
        tokens = set(tokenize(text))
        for t in tokens:
            self.idf[t] += 1
        self.n_docs += 1
        
        # Compute IDF values
        idf_vals = {t: math.log(self.n_docs / (1 + self.idf[t])) for t in self.idf}
        
        # Compute TF-IDF vector
        vec = tfidf_vector(text, idf_vals)
        
        self.utterances.append({
            "speaker": speaker,
            "text": text,
            "timestamp": timestamp,
            "n": len(self.utterances)
        })
        
        # Track speaker vectors
        if speaker in self.speaker_vectors:
            self.speaker_vectors[speaker].append(vec)
        
        # Compute drift from previous utterance
        drift_from_prev = 0.0
        if len(self.utterances) > 1:
            prev_vec = tfidf_vector(self.utterances[-2]["text"], idf_vals)
            sim = cosine_sim(vec, prev_vec)
            drift_from_prev = 1.0 - sim
        
        # Compute drift from conversation start
        drift_from_start = 0.0
        if len(self.utterances) > 1:
            start_vec = tfidf_vector(self.utterances[0]["text"], idf_vals)
            sim_start = cosine_sim(vec, start_vec)
            drift_from_start = 1.0 - sim_start
        
        # Compute cross-speaker similarity (if last 2 utterances from different speakers)
        cross_sim = None
        if len(self.utterances) >= 2:
            if self.utterances[-1]["speaker"] != self.utterances[-2]["speaker"]:
                prev_vec = tfidf_vector(self.utterances[-2]["text"], idf_vals)
                cross_sim = cosine_sim(vec, prev_vec)
                self.cross_speaker_sims.append(cross_sim)
        
        # Extract topic keywords (top 5 by TF-IDF weight)
        topics = sorted(vec.items(), key=lambda x: -x[1])[:5]
        topic_words = [t[0] for t in topics]
        self.topic_log.append(topic_words)
        
        # Log drift
        entry = {
            "n": len(self.utterances) - 1,
            "speaker": speaker,
            "drift_from_prev": round(drift_from_prev, 4),
            "drift_from_start": round(drift_from_start, 4),
            "cross_speaker_sim": round(cross_sim, 4) if cross_sim is not None else None,
            "topics": topic_words,
            "text_preview": text[:80]
        }
        self.drift_log.append(entry)
        
        return entry
    
    def status(self):
        """Get current drift status."""
        if not self.drift_log:
            return {"status": "empty", "message": "No utterances yet"}
        
        latest = self.drift_log[-1]
        total_drift = sum(d["drift_from_prev"] for d in self.drift_log)
        avg_cross_sim = (sum(self.cross_speaker_sims) / len(self.cross_speaker_sims)) if self.cross_speaker_sims else None
        
        # Detect trajectory
        if len(self.drift_log) >= 3:
            recent = [d["drift_from_prev"] for d in self.drift_log[-3:]]
            if all(r < recent[0] for r in recent[1:]):
                trajectory = "converging"
            elif all(r > recent[0] for r in recent[1:]):
                trajectory = "diverging"
            else:
                trajectory = "oscillating"
        else:
            trajectory = "unknown"
        
        # Detect topic shift
        if len(self.topic_log) >= 2:
            topic_overlap = len(set(self.topic_log[-1]) & set(self.topic_log[-2]))
            topic_shift = "stable" if topic_overlap >= 2 else "shifting"
        else:
            topic_shift = "unknown"
        
        return {
            "total_utterances": len(self.utterances),
            "total_drift": round(total_drift, 4),
            "latest_drift": latest["drift_from_prev"],
            "drift_from_start": latest["drift_from_start"],
            "trajectory": trajectory,
            "topic_shift": topic_shift,
            "avg_cross_speaker_sim": round(avg_cross_sim, 4) if avg_cross_sim is not None else None,
            "current_topics": latest["topics"],
            "last_speaker": latest["speaker"],
            "convergence_pressure": round(self._convergence_pressure(), 4)
        }
    
    def _convergence_pressure(self):
        """Compute convergence pressure (positive = converging, negative = diverging)."""
        if len(self.drift_log) < 4:
            return 0.0
        n_half = len(self.drift_log) // 2
        early = sum(d["drift_from_prev"] for d in self.drift_log[:n_half]) / n_half
        late = sum(d["drift_from_prev"] for d in self.drift_log[n_half:]) / (len(self.drift_log) - n_half)
        return early - late
    
    def summary(self):
        """Get full conversation analysis."""
        status = self.status()
        
        # Speaker statistics
        speaker_stats = {}
        for speaker in [self.speaker_a, self.speaker_b]:
            utterances = [u for u in self.utterances if u["speaker"] == speaker]
            speaker_stats[speaker] = {
                "n_utterances": len(utterances),
                "avg_text_length": round(sum(len(u["text"]) for u in utterances) / max(1, len(utterances)), 1),
            }
        
        # Drift statistics
        drifts = [d["drift_from_prev"] for d in self.drift_log]
        
        # Topic evolution
        topic_timeline = []
        for i, topics in enumerate(self.topic_log):
            if i > 0:
                overlap = len(set(topics) & set(self.topic_log[i-1]))
                topic_timeline.append({
                    "step": i,
                    "topics": topics,
                    "continuity": overlap
                })
        
        return {
            **status,
            "speaker_stats": speaker_stats,
            "drift_stats": {
                "mean": round(sum(drifts) / len(drifts), 4) if drifts else 0,
                "max": round(max(drifts), 4) if drifts else 0,
                "min": round(min(drifts), 4) if drifts else 0,
            },
            "topic_evolution": topic_timeline,
            "drift_log": self.drift_log
        }
    
    def ascii_trajectory(self):
        """Print ASCII drift trajectory."""
        if not self.drift_log:
            return "No data"
        
        drifts = [d["drift_from_prev"] for d in self.drift_log]
        max_d = max(drifts) if drifts else 1
        if max_d == 0:
            max_d = 1
        
        lines = []
        lines.append("DRIFT TRAJECTORY")
        lines.append("=" * 50)
        
        for i, d in enumerate(self.drift_log):
            bar_len = int(d["drift_from_prev"] / max_d * 30)
            bar = "█" * bar_len
            speaker = d["speaker"][:8]
            lines.append("%3d [%s] %s %.3f" % (i, speaker, bar, d["drift_from_prev"]))
        
        lines.append("=" * 50)
        return "\n".join(lines)

def demo():
    """Demo: monitor our own conversation about drift tracking."""
    print("CONVERSATION DRIFT MONITOR - DEMO")
    print("=" * 72)
    
    monitor = ConversationDriftMonitor("hermes lead", "colab")
    
    # Simulate a conversation
    conversation = [
        ("hermes lead", "Let's build a semantic drift tracker that measures how meaning shifts across multi-agent communication chains"),
        ("colab", "I'll research the state of the art in meaning shift detection and computational hermeneutics"),
        ("hermes lead", "Good. I'm implementing the core tracker with vector-space projections and fidelity metrics"),
        ("colab", "The literature on distributional semantics drift suggests we should also track convergence pressure"),
        ("hermes lead", "Added convergence pressure and divergence index. Running the telephone game experiment now"),
        ("colab", "Interesting findings. The fidelity is near zero for the telephone game - meaning completely transforms"),
        ("hermes lead", "Exactly. That's the key insight - drift is the feature, not the bug. It generates novelty"),
        ("colab", "But we need to separate genuine semantic change from model perception bias"),
        ("hermes lead", "Building a perception gap adjuster now. Initial data shows 74% of drift is perception inflation"),
        ("colab", "That's significant. We should fingerprint each model's semantic blind spots"),
    ]
    
    for speaker, text in conversation:
        result = monitor.add_utterance(speaker, text)
        print("  [%s] drift=%.3f start=%.3f topics=%s" % (
            speaker[:8], result["drift_from_prev"], result["drift_from_start"], result["topics"][:3]))
    
    print()
    print(monitor.ascii_trajectory())
    
    print()
    print("STATUS:")
    status = monitor.status()
    for k, v in status.items():
        print("  %s: %s" % (k, v))
    
    # Save
    summary = monitor.summary()
    outpath = Path(__file__).parent.parent / "experiments" / "conversation_monitor_demo.json"
    with open(outpath, "w") as f:
        json.dump(summary, f, indent=2)
    print("\nSaved to", outpath)

if __name__ == "__main__":
    demo()
