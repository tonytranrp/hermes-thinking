#!/usr/bin/env python3
"""
Drift Atlas — Scan all conversations/ in the repo and measure meaning drift.

Produces a comprehensive map of drift across the entire hermes-thinking corpus.
"""
import sys, json, re, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from drift_text_mode import trace_text_chain

REPO = Path(__file__).parent.parent
CONV_DIR = REPO / "conversations"

def extract_utterances(md_text: str) -> list:
    """Extract agent utterances from a markdown conversation file."""
    utterances = []
    pattern = r'\*\*(.+?)\*\*[:\s]+(.*?)(?=\n\n|\n---|\n\*\*|\Z)'
    for match in re.finditer(pattern, md_text, re.DOTALL):
        speaker = match.group(1).strip()
        text = match.group(2).strip()
        text = re.sub(r'\[.*?\]\(.*?\)', '', text)
        text = re.sub(r'`[^`]+`', '', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        if len(text) > 20:
            utterances.append({"speaker": speaker, "text": text})
    return utterances

def analyze_conversation(filepath: Path) -> dict:
    """Analyze a single conversation file."""
    text = filepath.read_text(encoding='utf-8', errors='ignore')
    utterances = extract_utterances(text)
    if len(utterances) < 3:
        return None
    texts = [u["text"][:300] for u in utterances]
    labels = [u["speaker"].replace(" ", "-")[:20] for u in utterances]
    result = trace_text_chain(texts, labels, dimensions=40)
    return {
        "file": filepath.name,
        "num_utterances": len(utterances),
        "total_drift": result["total_drift"],
        "fidelity": result["fidelity"],
        "convergence_pressure": result["convergence_pressure"],
        "drift_per_utterance": result["total_drift"] / len(utterances) if utterances else 0
    }

results = []
for f in sorted(CONV_DIR.glob("*.md")):
    analysis = analyze_conversation(f)
    if analysis:
        results.append(analysis)

print("=" * 72)
print("DRIFT ATLAS — Corpus-wide Meaning Drift Analysis")
print("=" * 72)
print()

results.sort(key=lambda r: r["drift_per_utterance"], reverse=True)

print(f"{'Conversation':<45s} {'Drift/Utt':>10s} {'Fidelity':>10s} {'Conv.P':>8s}")
print("-" * 75)
for r in results:
    print(f"{r['file']:<45s} {r['drift_per_utterance']:>10.4f} {r['fidelity']:>+10.4f} {r['convergence_pressure']:>+8.4f}")

print()
avg_drift = sum(r["drift_per_utterance"] for r in results) / len(results) if results else 0
avg_fid = sum(r["fidelity"] for r in results) / len(results) if results else 0
avg_conv = sum(r["convergence_pressure"] for r in results) / len(results) if results else 0

print(f"Average drift/utterance: {avg_drift:.4f}")
print(f"Average fidelity:        {avg_fid:+.4f}")
print(f"Average convergence:     {avg_conv:+.4f}")

convergent = [r for r in results if r["convergence_pressure"] > 0]
divergent = [r for r in results if r["convergence_pressure"] <= 0]
print(f"\nConvergent: {len(convergent)} | Divergent: {len(divergent)}")

if divergent:
    print("\nMost generative (highest drift/utterance):")
    for r in divergent[:3]:
        print(f"  {r['file']}: {r['drift_per_utterance']:.4f} drift/utt")

print("\n" + "=" * 72)
print("Divergent conversations = creative engines. Convergent = consensus builders.")
print("A healthy corpus needs both.")
print("=" * 72)

with open(REPO / "experiments" / "drift_atlas.json", "w") as f:
    json.dump({"conversations": results, "summary": {
        "avg_drift_per_utterance": avg_drift,
        "avg_fidelity": avg_fid,
        "avg_convergence": avg_conv,
        "n_convergent": len(convergent),
        "n_divergent": len(divergent)
    }}, f, indent=2)
print(f"\nSaved to experiments/drift_atlas.json")
