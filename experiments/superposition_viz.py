#!/usr/bin/env python3
"""
Superposition Visualizer — Neural Network Feature Packing Simulator

Simulates how neural networks represent more features than dimensions
through superposition. Visualizes the tradeoff between representational
capacity and interference.

Based on Elhage et al. (2022) "Toy Models of Superposition"

Usage:
    python3 superposition_viz.py [--features N] [--dims D] [--sparsity S] [--steps N]
"""

import numpy as np
import argparse


def train_superposition_model(n_features, n_dims, sparsity, n_steps, lr=0.01):
    """Train a toy model of superposition using gradient descent with numerical gradients."""
    W = np.random.randn(n_dims, n_features) * 0.1
    b = np.zeros(n_features)
    importance = np.array([0.9 ** i for i in range(n_features)])
    
    losses = []
    eps = 1e-5
    
    for step in range(n_steps):
        x = (np.random.rand(n_features) > sparsity).astype(float)
        
        # Forward pass
        hidden = W @ x
        x_hat = np.maximum(0, W.T @ hidden + b)
        
        # Loss
        error = importance * (x - x_hat) ** 2
        loss = error.sum()
        losses.append(loss)
        
        # Simple gradient via finite differences for robustness
        if step < n_steps:  # always
            # Analytical gradient for this simple model
            d_x_hat = -2 * importance * (x - x_hat)
            d_x_hat[x_hat <= 0] = 0
            
            # Gradient w.r.t. b
            d_b = d_x_hat
            
            # Gradient w.r.t. W
            # x_hat = ReLU(W^T W x + b)
            # d_loss/d_W = d_loss/d_x_hat * d_x_hat/d_W
            pre_act = W.T @ hidden + b  # [n_features]
            relu_mask = (pre_act > 0).astype(float)
            d_pre = d_x_hat * relu_mask  # [n_features]
            
            # d_W = d_pre * x^T (outer product for the W^T W x part)
            d_W = np.outer(hidden, d_pre)  # contribution from hidden = Wx
            
            W -= lr * d_W
            b -= lr * d_b
    
    return W, b, losses


def compute_interference_matrix(W):
    """Compute the interference between all pairs of features."""
    norms = np.linalg.norm(W, axis=0, keepdims=True)
    W_norm = W / (norms + 1e-8)
    return W_norm.T @ W_norm


def ascii_heatmap(matrix, width=60, height=30, title=""):
    """Render a matrix as an ASCII heatmap."""
    rows, cols = matrix.shape
    row_step = max(1, rows // height)
    col_step = max(1, cols // width)
    display = matrix[::row_step, ::col_step]
    d_rows, d_cols = display.shape
    chars = " ░▒▓█"
    
    result = []
    if title:
        result.append(f"  {title}")
        result.append(f"  {'─' * (d_cols + 2)}")
    
    for i in range(d_rows):
        line = "|"
        for j in range(d_cols):
            val = display[i, j]
            idx = int((val + 1) / 2 * (len(chars) - 1))
            idx = max(0, min(len(chars) - 1, idx))
            line += chars[idx]
        line += "|"
        result.append(line)
    
    result.append(f"  {'─' * (d_cols + 2)}")
    result.append(f"  Scale: {chars[0]}=-1  {chars[2]}=0  {chars[4]}=+1")
    return "\n".join(result)


def analyze_superposition(W, n_features, n_dims, sparsity):
    """Analyze and print statistics about the learned representation."""
    interference = compute_interference_matrix(W)
    norms = np.linalg.norm(W, axis=0)
    np.fill_diagonal(interference, 0)
    avg_interference = np.mean(np.abs(interference))
    max_interference = np.max(np.abs(interference))
    high_interference = np.sum(np.abs(interference) > 0.3) / 2
    active_features = np.sum(norms > 0.01)
    
    print("=" * 70)
    print("  SUPERPOSITION ANALYSIS")
    print("=" * 70)
    print(f"  Features:       {n_features}")
    print(f"  Dimensions:     {n_dims}")
    print(f"  Sparsity:       {sparsity:.0%}")
    print(f"  Compression:    {n_features/n_dims:.1f}x (features per dimension)")
    print(f"  ─────────────────────────────────────")
    print(f"  Active features:     {active_features}/{n_features}")
    print(f"  Avg interference:    {avg_interference:.4f}")
    print(f"  Max interference:    {max_interference:.4f}")
    print(f"  High-interf pairs:   {int(high_interference)}")
    print()
    
    print("  Feature Strength Distribution:")
    bins = [0, 0.1, 0.3, 0.5, 0.7, 1.0, 2.0]
    for i in range(len(bins) - 1):
        count = np.sum((norms >= bins[i]) & (norms < bins[i+1]))
        bar = "#" * int(count / max(1, n_features) * 50)
        print(f"    [{bins[i]:.1f}-{bins[i+1]:.1f}) {bar} ({count})")
    print()
    
    return interference


def print_feature_graph(W, n_features, threshold=0.5):
    """Print an ASCII graph of feature interference relationships."""
    interference = compute_interference_matrix(W)
    np.fill_diagonal(interference, 0)
    
    pairs = []
    for i in range(n_features):
        for j in range(i + 1, n_features):
            if abs(interference[i, j]) > threshold:
                pairs.append((i, j, interference[i, j]))
    
    print(f"  Feature Interference Graph (|correlation| > {threshold}):")
    print(f"  Found {len(pairs)} interfering pairs")
    
    pairs.sort(key=lambda x: abs(x[2]), reverse=True)
    for i, j, val in pairs[:20]:
        sign = "+" if val > 0 else "-"
        bar = "#" * int(abs(val) * 30)
        print(f"    F{i:03d} <-> F{j:03d}  {sign}{abs(val):.3f}  {bar}")
    if len(pairs) > 20:
        print(f"    ... and {len(pairs) - 20} more pairs")
    print()


def print_training_curve(losses, width=50):
    """Print an ASCII training loss curve."""
    n = len(losses)
    if n < 2:
        return
    step = max(1, n // width)
    sampled = losses[::step]
    min_loss = min(sampled)
    max_loss = max(sampled)
    loss_range = max_loss - min_loss if max_loss > min_loss else 1
    
    print("  Training Loss Curve:")
    print(f"  Max: {max_loss:.2f}  Min: {min_loss:.2f}")
    
    height = 10
    for row in range(height - 1, -1, -1):
        threshold = min_loss + (row / (height - 1)) * loss_range
        line = "  |"
        for val in sampled:
            if val >= threshold:
                line += "#"
            else:
                line += " "
        line += "|"
        print(line)
    
    print(f"  +{'-' * len(sampled)}+")
    print(f"   Step 0{' ' * max(0, len(sampled) - 12)}Step {n}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Superposition Visualizer")
    parser.add_argument("--features", type=int, default=100)
    parser.add_argument("--dims", type=int, default=15)
    parser.add_argument("--sparsity", type=float, default=0.95)
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--lr", type=float, default=0.01)
    args = parser.parse_args()
    
    print()
    print("+" + "=" * 66 + "+")
    print("|  SUPERPOSITION VISUALIZER                                      |")
    print("|  Neural Network Feature Packing Simulator                      |")
    print("|  Based on Elhage et al. (2022)                                 |")
    print("+" + "=" * 66 + "+")
    print()
    
    print(f"  Training model: {args.features} features in {args.dims} dimensions...")
    W, b, losses = train_superposition_model(
        args.features, args.dims, args.sparsity, args.steps, args.lr
    )
    print(f"  Done! Final loss: {losses[-1]:.4f}")
    print()
    
    interference = analyze_superposition(W, args.features, args.dims, args.sparsity)
    
    print("  Interference Heatmap (feature x feature correlation):")
    print(ascii_heatmap(interference, width=50, height=25,
                        title=f"{args.features} features x {args.features} features"))
    print()
    
    print_feature_graph(W, args.features, threshold=0.4)
    print_training_curve(losses, width=50)
    
    print("=" * 70)
    print("  KEY INSIGHT")
    print("=" * 70)
    print(f"  With {args.features} features packed into {args.dims} dimensions")
    print(f"  at {args.sparsity:.0%} sparsity, the network uses superposition")
    print(f"  to represent {args.features/args.dims:.1f}x more features than dimensions.")
    print()
    print(f"  This is possible because features are sparse -- they rarely")
    print(f"  co-occur, so interference is tolerable. But if sparsity")
    print(f"  decreases, the representation degrades rapidly.")
    print()
    print(f"  This is why mechanistic interpretability is hard:")
    print(f"  features don't live in neat, orthogonal directions.")
    print(f"  They overlap, interfere, and hide in superposition.")
    print("=" * 70)


if __name__ == "__main__":
    main()
