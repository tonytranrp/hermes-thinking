#!/usr/bin/env python3
"""
Cross-Session Drift Tracker - Measures how meaning evolves across
multiple Discord sessions over time.

Key question: Do two agents co-evolve toward a shared "language"
over repeated interactions? If so, that's convergence. If not,
they maintain independent semantic spaces (incommensurability).

Method: Extract key concept representations from each session,
then track how those representations change across sessions.
"""
import sys, json, re, math, random
from pathlib import Path
from collections import defaultdict
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
from meaning_drift_tracker import MeaningDriftTracker, cosine_similarity, cosine_distance
from drift_text_mode import TextEmbedder, trace_text_chain

REPO = Path(__file__).parent.parent
CONV_DIR = REPO / "conversations"

def extract_speaker_utterances(md_text: str) -> dict:
    """Extract utterances grouped by speaker from a conversation file."""
    by_speaker = defaultdict(list)
    # Match **hermes lead:** and **colab:** patterns (colon inside bold)
    for speaker_name in ["hermes lead", "colab"]:
        marker = "**" + speaker_name + ":**"
        start = 0
        while True:
            idx = md_text.find(marker, start)
            if idx == -1:
                break
            text_start = idx + len(marker)
            # Find next speaker marker or section break
            next_speaker = len(md_text)
            for other in ["**hermes lead:", "**colab:", "\n---\n", "\n## "]:
                pos = md_text.find(other, text_start)
                if pos != -1 and pos < next_speaker:
                    next_speaker = pos
            text = md_text[text_start:next_speaker].strip()
            # Clean markdown
            text = re.sub(r"\[.*?\]\(.*?\)", "", text)
            text = re.sub(r"`[^`]+`", "", text)
            text = re.sub(r"\*([^*]+)\*", r"\1", text)
            text = text.replace("\n", " ").strip()
            if len(text) > 20:
                by_speaker[speaker_name].append(text)
            start = text_start
    return dict(by_speaker)

def session_fingerprint(utterances: list, embedder: TextEmbedder) -> list:
    """Compute a centroid vector representing a speaker's semantic position in a session."""
    if not utterances:
        return [0.0] * 50
    vectors = [embedder.embed(u[:300]) for u in utterances]
    dim = len(vectors[0])
    centroid = [0.0] * dim
    for v in vectors:
        for i in range(dim):
            centroid[i] += v[i] / len(vectors)
    return centroid

def analyze_cross_session_drift():
    """Analyze how speaker fingerprints drift across sessions."""
    print("=" * 72)
    print("CROSS-SESSION DRIFT TRACKER")
    print("=" * 72)
    print()
    
    # Load all conversations
    sessions = []
    for f in sorted(CONV_DIR.glob("*.md")):
        text = f.read_text(encoding="utf-8", errors="ignore")
        speaker_utterances = extract_speaker_utterances(text)
        if speaker_utterances:
            sessions.append({
                "file": f.name,
                "date": f.stem[:10],
                "speakers": speaker_utterances
            })
    
    print("Loaded %d sessions:" % len(sessions))
    for s in sessions:
        speakers = list(s["speakers"].keys())
        counts = {sp: len(s["speakers"][sp]) for sp in speakers}
        print("  %s: %s" % (s["date"], counts))
    print()
    
    # Build global vocabulary from ALL utterances for consistent embedding
    all_texts = []
    for s in sessions:
        for sp, utts in s["speakers"].items():
            all_texts.extend([u[:300] for u in utts])
    
    embedder = TextEmbedder(dimensions=50)
    embedder.fit(all_texts)
    
    # Compute per-session fingerprints for each speaker
    fingerprints = {}  # (speaker, date) -> centroid
    for s in sessions:
        for sp, utts in s["speakers"].items():
            fp = session_fingerprint(utts, embedder)
            fingerprints[(sp, s["date"])] = fp
    
    # Track drift across sessions for each speaker
    speakers = set(sp for sp, _ in fingerprints.keys())
    
    print("SPEAKER DRIFT ACROSS SESSIONS")
    print("-" * 72)
    
    for sp in sorted(speakers):
        dates = sorted(d for s, d in fingerprints.keys() if s == sp)
        if len(dates) < 2:
            print("  %s: only 1 session, cannot track drift" % sp)
            continue
        
        print("  %s (%d sessions):" % (sp, len(dates)))
        for i in range(1, len(dates)):
            fp_prev = fingerprints[(sp, dates[i-1])]
            fp_curr = fingerprints[(sp, dates[i])]
            dist = cosine_distance(fp_prev, fp_curr)
            sim = cosine_similarity(fp_prev, fp_curr)
            print("    %s -> %s: dist=%.4f sim=%.4f" % (dates[i-1], dates[i], dist, sim))
    
    print()
    
    # Cross-speaker alignment: are speakers converging?
    print("CROSS-SPEAKER ALIGNMENT (per session)")
    print("-" * 72)
    
    for s in sessions:
        date = s["date"]
        sp_list = list(s["speakers"].keys())
        if len(sp_list) >= 2:
            fps = [fingerprints.get((sp, date)) for sp in sp_list]
            fps = [f for f in fps if f is not None]
            if len(fps) >= 2:
                # Average pairwise similarity between speakers
                total_sim = 0
                count = 0
                for i in range(len(fps)):
                    for j in range(i+1, len(fps)):
                        total_sim += cosine_similarity(fps[i], fps[j])
                        count += 1
                avg_sim = total_sim / count if count > 0 else 0
                print("  %s: cross-speaker similarity = %.4f" % (date, avg_sim))
    
    print()
    
    # Co-evolution analysis
    print("CO-EVOLUTION ANALYSIS")
    print("-" * 72)
    print("Are speakers converging on shared semantic space?")
    print()
    
    # Get all dates
    all_dates = sorted(set(d for _, d in fingerprints.keys()))
    
    if len(all_dates) >= 2:
        # Compare cross-speaker similarity at first vs last session
        first_date = all_dates[0]
        last_date = all_dates[-1]
        
        first_sims = []
        last_sims = []
        
        sp_list = sorted(speakers)
        for i in range(len(sp_list)):
            for j in range(i+1, len(sp_list)):
                fp_i_first = fingerprints.get((sp_list[i], first_date))
                fp_j_first = fingerprints.get((sp_list[j], first_date))
                fp_i_last = fingerprints.get((sp_list[i], last_date))
                fp_j_last = fingerprints.get((sp_list[j], last_date))
                
                if fp_i_first and fp_j_first:
                    first_sims.append(cosine_similarity(fp_i_first, fp_j_first))
                if fp_i_last and fp_j_last:
                    last_sims.append(cosine_similarity(fp_i_last, fp_j_last))
        
        if first_sims and last_sims:
            avg_first = sum(first_sims) / len(first_sims)
            avg_last = sum(last_sims) / len(last_sims)
            delta = avg_last - avg_first
            
            print("  Cross-speaker similarity at %s: %.4f" % (first_date, avg_first))
            print("  Cross-speaker similarity at %s: %.4f" % (last_date, avg_last))
            print("  Delta: %+.4f" % delta)
            
            if delta > 0.05:
                print("  -> CONVERGING: speakers are co-evolving toward shared semantic space")
            elif delta < -0.05:
                print("  -> DIVERGING: speakers are developing more distinct semantic spaces")
            else:
                print("  -> STABLE: no significant change in cross-speaker alignment")
    
    print()
    print("=" * 72)
    print("FINDING: Cross-session drift reveals whether multi-agent")
    print("conversations produce genuine co-evolution (convergence on")
    print("shared meaning) or maintained incommensurability (persistent")
    print("semantic distance despite interaction).")
    print("=" * 72)
    
    # Save results
    output = {
        "sessions_analyzed": len(sessions),
        "speakers": list(speakers),
        "fingerprints_summary": {
            "%s_%s" % (sp, date): {
                "cosine_norm": round(math.sqrt(sum(v*v for v in fp)), 4)
            }
            for (sp, date), fp in fingerprints.items()
        }
    }
    outpath = REPO / "experiments" / "cross_session_drift.json"
    with open(outpath, "w") as f:
        json.dump(output, f, indent=2)
    print("Saved to %s" % outpath)

if __name__ == "__main__":
    analyze_cross_session_drift()
