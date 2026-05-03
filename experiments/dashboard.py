#!/usr/bin/env python3
"""
Meaning Drift Research Dashboard - generates a summary of all experiments.

Scans the experiments directory, loads all result files, and produces
a unified report with key metrics and cross-experiment comparisons.
"""
import json, os, sys
from pathlib import Path
from datetime import datetime

EXPERIMENTS_DIR = Path(__file__).parent
TOOLS_DIR = EXPERIMENTS_DIR.parent / "tools"

def scan_experiments():
    """Scan and categorize all experiment files."""
    results = {
        "drift_chains": [],
        "visualizations": [],
        "other": []
    }
    
    for fpath in sorted(EXPERIMENTS_DIR.iterdir()):
        if fpath.is_dir():
            continue
        
        name = fpath.name
        if name.endswith(".json"):
            try:
                with open(fpath) as f:
                    data = json.load(f)
                results["drift_chains"].append({"file": name, "data": data})
            except:
                results["other"].append({"file": name, "type": "json (unreadable)"})
        elif name.endswith(".png"):
            results["visualizations"].append({"file": name})
        elif name.endswith(".py"):
            results["other"].append({"file": name, "type": "script"})
    
    return results

def extract_metrics(data):
    """Extract key metrics from any experiment data structure."""
    metrics = {}
    
    if isinstance(data, dict):
        for key in ["fidelity", "total_drift", "accumulated_drift", "divergence_index",
                     "convergence_pressure", "consistency", "avg_fidelity", "avg_drift"]:
            if key in data:
                val = data[key]
                if isinstance(val, (int, float)):
                    metrics[key] = round(val, 4)
        
        # Nested metrics
        if "trajectories" in data and isinstance(data["trajectories"], list):
            metrics["n_chains"] = len(data["trajectories"])
        
        if "steps" in data and isinstance(data["steps"], list):
            metrics["n_steps"] = len(data["steps"])
        
        if "similarities" in data:
            metrics["n_similarities"] = len(data["similarities"])
        
        if "all_ratings" in data:
            metrics["n_rated_texts"] = len(data["all_ratings"])
    
    elif isinstance(data, list):
        metrics["n_items"] = len(data)
        for item in data:
            if isinstance(item, dict):
                for key in ["avg_fidelity", "fidelity", "consistency"]:
                    if key in item:
                        metrics.setdefault(key + "_values", []).append(item[key])
    
    return metrics

def generate_report():
    """Generate the full dashboard report."""
    print("=" * 72)
    print("MEANING DRIFT RESEARCH DASHBOARD")
    print("Generated: %s" % datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("=" * 72)
    
    results = scan_experiments()
    
    print("\n📊 EXPERIMENT INVENTORY")
    print("-" * 40)
    print("  JSON result files: %d" % len(results["drift_chains"]))
    print("  Visualizations: %d" % len(results["visualizations"]))
    print("  Other files: %d" % len(results["other"]))
    
    print("\n📋 KEY METRICS BY EXPERIMENT")
    print("-" * 40)
    
    all_metrics = {}
    for entry in results["drift_chains"]:
        metrics = extract_metrics(entry["data"])
        if metrics:
            fname = entry["file"].replace(".json", "").replace("_", " ").title()
            print("\n  %s:" % fname)
            for key, val in metrics.items():
                if isinstance(val, (int, float)):
                    print("    %s: %s" % (key, val))
                elif isinstance(val, list) and val:
                    avg = sum(v for v in val if isinstance(v, (int, float))) / max(1, sum(1 for v in val if isinstance(v, (int, float))))
                    print("    %s: avg=%.4f (n=%d)" % (key, avg, len(val)))
            all_metrics[entry["file"]] = metrics
    
    # Cross-experiment summary
    print("\n\n🔬 CROSS-EXPERIMENT SUMMARY")
    print("-" * 40)
    
    fidelities = []
    drifts = []
    for entry in results["drift_chains"]:
        metrics = extract_metrics(entry["data"])
        if "fidelity" in metrics:
            fidelities.append(metrics["fidelity"])
        if "total_drift" in metrics:
            drifts.append(metrics["total_drift"])
        if "accumulated_drift" in metrics:
            drifts.append(metrics["accumulated_drift"])
    
    if fidelities:
        print("  Fidelity range: %.4f - %.4f (mean %.4f)" % (
            min(fidelities), max(fidelities), sum(fidelities) / len(fidelities)))
    if drifts:
        print("  Drift range: %.4f - %.4f (mean %.4f)" % (
            min(drifts), max(drifts), sum(drifts) / len(drifts)))
    
    print("\n🖼️ VISUALIZATIONS")
    print("-" * 40)
    for viz in results["visualizations"]:
        print("  %s" % viz["file"])
    
    print("\n" + "=" * 72)
    print("END OF DASHBOARD")
    print("=" * 72)
    
    # Save summary
    summary = {
        "generated": datetime.now().isoformat(),
        "n_experiments": len(results["drift_chains"]),
        "n_visualizations": len(results["visualizations"]),
        "metrics_by_file": all_metrics,
        "fidelity_range": [min(fidelities), max(fidelities)] if fidelities else None,
        "drift_range": [min(drifts), max(drifts)] if drifts else None,
    }
    
    outpath = EXPERIMENTS_DIR / "dashboard_summary.json"
    with open(outpath, "w") as f:
        json.dump(summary, f, indent=2)
    print("\nSummary saved to %s" % outpath)

if __name__ == "__main__":
    generate_report()
