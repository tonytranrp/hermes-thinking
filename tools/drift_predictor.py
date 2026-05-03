#!/usr/bin/env python3
"""
Drift Predictor - predicts final chain fidelity from early-hop drift patterns.

Given the first N hops of a semantic drift chain, predicts:
  - Final fidelity (similarity of endpoint to source)
  - Whether the chain will converge or diverge
  - Estimated total accumulated drift

Method: We fit a simple exponential model to early drift rates:
  drift(t) = A * exp(-lambda*t) + C  (converging)
  drift(t) = A * exp(+lambda*t) + C  (diverging)

The decay/growth rate lambda determines the trajectory.
"""
import math, json
from pathlib import Path

class DriftPredictor:
    """Predicts final chain fidelity from early-hop drift patterns.
    
    Supports three decay models:
      - Exponential: drift(t) = A * exp(-λ*t) + C  (converging/diverging)
      - Logistic:    drift(t) = L / (1 + exp(-k*(t-t0)))  (S-curve)
      - Power-law:   drift(t) = A * t^(-α) + C  (long-tail decay)
    
    Model selection via AIC (Akaike Information Criterion).
    """
    
    def _aic(self, residuals, n_params, n_points):
        """Compute AIC for model comparison."""
        if n_points <= n_params:
            return float('inf')
        sse = sum(r**2 for r in residuals)
        if sse <= 0:
            return -float('inf')
        return n_params * 2 + n_points * math.log(sse / n_points)
    
    def fit_exponential(self, drifts):
        """Fit exponential model to drift sequence."""
        if len(drifts) < 3:
            return None
        
        increments = [drifts[i] - drifts[i-1] if i > 0 else drifts[i] 
                      for i in range(len(drifts))]
        valid = [(i, inc) for i, inc in enumerate(increments) if inc > 0.001]
        
        if len(valid) < 2:
            return {"A": 0, "lambda": 0, "C": increments[-1] if increments else 0, "type": "converged"}
        
        n = len(valid)
        sum_x = sum(v[0] for v in valid)
        sum_y = sum(math.log(v[1]) for v in valid)
        sum_xy = sum(v[0] * math.log(v[1]) for v in valid)
        sum_x2 = sum(v[0] ** 2 for v in valid)
        
        denom = n * sum_x2 - sum_x ** 2
        if abs(denom) < 1e-10:
            return {"A": increments[0], "lambda": 0, "C": 0, "type": "constant"}
        
        lam = -(n * sum_xy - sum_x * sum_y) / denom
        log_A = (sum_y + lam * sum_x) / n
        A = math.exp(log_A)
        
        drift_type = "converging" if lam > 0 else "diverging"
        C = max(0, increments[-1] - A * math.exp(-lam * len(increments))) if len(increments) > 0 else 0
        
        # Compute residuals for AIC
        residuals = []
        for i, inc in enumerate(increments):
            pred = A * math.exp(-lam * i) + C
            residuals.append(inc - pred)
        
        return {"A": A, "lambda": lam, "C": C, "type": drift_type, 
                "residuals": residuals, "n_params": 3}
    
    def fit_logistic(self, drifts):
        """Fit logistic (S-curve) model to drift sequence.
        
        drift(t) = L / (1 + exp(-k*(t - t0)))
        Uses simple grid search over t0, then least-squares for L and k.
        """
        if len(drifts) < 4:
            return None
        
        n = len(drifts)
        best_aic = float('inf')
        best_params = None
        
        # Grid search over t0
        for t0_frac in [i/10 for i in range(-5, 16)]:
            t0 = t0_frac * n
            # Transform: log(drift / (L - drift)) = k*(t - t0)
            # Pick L slightly above max drift
            L = max(drifts) * 1.1 + 0.01
            
            valid = []
            for t, d in enumerate(drifts):
                ratio = d / (L - d)
                if ratio > 0 and L - d > 0.001:
                    valid.append((t, math.log(max(ratio, 1e-10))))
            
            if len(valid) < 2:
                continue
            
            sum_x = sum(v[0] for v in valid)
            sum_y = sum(v[1] for v in valid)
            sum_xy = sum(v[0] * v[1] for v in valid)
            sum_x2 = sum(v[0] ** 2 for v in valid)
            nn = len(valid)
            
            denom = nn * sum_x2 - sum_x ** 2
            if abs(denom) < 1e-10:
                continue
            
            k = (nn * sum_xy - sum_x * sum_y) / denom
            intercept = (sum_y - k * sum_x) / nn
            
            # Compute residuals
            residuals = []
            for t, d in enumerate(drifts):
                pred = L / (1 + math.exp(-(k * (t - t0))))
                residuals.append(d - pred)
            
            aic = self._aic(residuals, 4, n)  # L, k, t0, intercept
            if aic < best_aic:
                best_aic = aic
                best_params = {"L": L, "k": k, "t0": t0, "intercept": intercept,
                              "residuals": residuals, "n_params": 4, "type": "logistic"}
        
        return best_params
    
    def fit_power_law(self, drifts):
        """Fit power-law model: drift(t) = A * t^(-alpha) + C.
        
        For converging chains: alpha > 0 (drift decreases)
        For diverging chains: alpha < 0 (drift increases)
        """
        if len(drifts) < 3:
            return None
        
        # Use log-log regression on increments
        increments = [drifts[i] - drifts[i-1] for i in range(1, len(drifts))]
        valid = [(i+1, abs(inc)) for i, inc in enumerate(increments) if abs(inc) > 0.001]
        
        if len(valid) < 2:
            return None
        
        log_t = [math.log(v[0]) for v in valid]
        log_inc = [math.log(v[1]) for v in valid]
        
        n = len(valid)
        sum_x = sum(log_t)
        sum_y = sum(log_inc)
        sum_xy = sum(x * y for x, y in zip(log_t, log_inc))
        sum_x2 = sum(x**2 for x in log_t)
        
        denom = n * sum_x2 - sum_x ** 2
        if abs(denom) < 1e-10:
            return None
        
        alpha = -(n * sum_xy - sum_x * sum_y) / denom
        log_A = (sum_y + alpha * sum_x) / n
        A = math.exp(log_A)
        C = max(0, drifts[-1] - A * (len(drifts) ** (-alpha))) if alpha > 0 else 0
        
        # Compute residuals
        residuals = []
        for t, d in enumerate(drifts):
            if t == 0:
                continue
            pred = A * (t ** (-alpha)) + C if alpha > 0 else A * (t ** (-alpha))
            residuals.append(d - pred)
        
        return {"A": A, "alpha": -alpha, "C": C, 
                "residuals": residuals, "n_params": 3, "type": "power_law"}
    
    def predict(self, similarities, total_steps=None):
        """Predict final fidelity from observed similarities so far.
        
        Fits exponential, logistic, and power-law models, selects the best
        via AIC, and uses it for prediction.
        """
        if len(similarities) < 3:
            return {
                "predicted_fidelity": similarities[-1] if similarities else 1.0,
                "trajectory": "unknown",
                "confidence": 0.0,
                "warning": "Need at least 3 data points"
            }
        
        drifts = [1.0 - s for s in similarities]
        
        # Fit all three models
        models_fitted = {}
        for name, fit_fn in [("exponential", self.fit_exponential), 
                              ("logistic", self.fit_logistic),
                              ("power_law", self.fit_power_law)]:
            m = fit_fn(drifts)
            if m and "residuals" in m:
                aic = self._aic(m["residuals"], m["n_params"], len(drifts))
                m["aic"] = aic
                models_fitted[name] = m
        
        # Select best model by AIC
        if not models_fitted:
            return {"predicted_fidelity": similarities[-1], "trajectory": "unknown", "confidence": 0.0}
        
        best_name = min(models_fitted, key=lambda k: models_fitted[k].get("aic", float('inf')))
        model = models_fitted[best_name]
        
        current_step = len(drifts) - 1
        predict_to = total_steps if total_steps else current_step + 5
        
        if model["type"] == "converged":
            predicted_final_drift = drifts[-1]
            trajectory = "converged"
        elif model["type"] == "converging":
            predicted_final_drift = drifts[-1] + sum(
                model["A"] * math.exp(-model["lambda"] * (current_step + k))
                for k in range(1, predict_to - current_step + 1)
            )
            # Cap at 2x current drift — converging chains don't double their drift
            predicted_final_drift = min(predicted_final_drift, drifts[-1] * 2)
            trajectory = "converging"
        elif model["type"] == "diverging":
            predicted_final_drift = drifts[-1] + sum(
                model["A"] * math.exp(model["lambda"] * k)
                for k in range(1, predict_to - current_step + 1)
            )
            # Cap at 1.0 (max possible drift)
            predicted_final_drift = min(predicted_final_drift, 1.0)
            trajectory = "diverging"
        elif model["type"] == "logistic":
            L, k, t0 = model["L"], model["k"], model["t0"]
            predicted_final_drift = L / (1 + math.exp(-(k * (predict_to - t0))))
            trajectory = "saturating" if k > 0 else "accelerating"
        elif model["type"] == "power_law":
            A, alpha, C = model["A"], model["alpha"], model["C"]
            if predict_to > 0:
                predicted_final_drift = A * (predict_to ** alpha) + C
            else:
                predicted_final_drift = drifts[-1]
            trajectory = "power_decay" if alpha < 0 else "power_growth"
            predicted_final_drift = max(0, min(predicted_final_drift, 1.0))
        else:
            predicted_final_drift = drifts[-1]
            trajectory = "constant"
        
        predicted_fidelity = max(0.0, 1.0 - predicted_final_drift)
        confidence = min(1.0, len(similarities) / 8.0)
        
        drift_increments = [drifts[i] - drifts[i-1] for i in range(1, len(drifts))]
        if drift_increments:
            monotonic = sum(1 for i in range(1, len(drift_increments)) 
                          if (drift_increments[i] > 0) == (drift_increments[0] > 0)) / max(1, len(drift_increments) - 1)
            confidence *= (0.5 + 0.5 * monotonic)
        
        # Model comparison info
        model_comparison = {name: round(m.get("aic", 0), 2) for name, m in models_fitted.items()}
        
        return {
            "predicted_fidelity": round(predicted_fidelity, 4),
            "trajectory": trajectory,
            "confidence": round(confidence, 3),
            "best_model": best_name,
            "model_comparison": model_comparison,
            "model": {k: v for k, v in model.items() if k != "residuals"},
            "current_fidelity": round(similarities[-1], 4),
            "current_drift": round(drifts[-1], 4),
            "steps_observed": len(similarities),
            "steps_predicted_to": predict_to
        }
    
    def predict_chain(self, similarities_sequence, horizon=5):
        """Predict fidelity at each future step."""
        predictions = []
        for step in range(1, horizon + 1):
            result = self.predict(similarities_sequence, 
                                  total_steps=len(similarities_sequence) + step - 1)
            predictions.append({
                "step": len(similarities_sequence) + step - 1,
                "predicted_fidelity": result["predicted_fidelity"],
                "trajectory": result["trajectory"]
            })
        return predictions

def demo():
    """Demonstrate drift prediction with multi-model comparison."""
    print("DRIFT PREDICTOR - DEMO (Multi-Model AIC Selection)")
    print("=" * 72)
    
    predictor = DriftPredictor()
    
    print("\n1. CONVERGING CHAIN (drift decreases over time)")
    converging = [1.0, 0.85, 0.75, 0.70, 0.68, 0.67]
    result = predictor.predict(converging)
    print("   Observed: %s" % [round(s, 3) for s in converging])
    print("   Predicted fidelity: %.4f" % result["predicted_fidelity"])
    print("   Trajectory: %s" % result["trajectory"])
    print("   Best model: %s (AIC comparison: %s)" % (result.get("best_model", "?"), result.get("model_comparison", {})))
    print("   Confidence: %.3f" % result["confidence"])
    
    forward = predictor.predict_chain(converging, horizon=5)
    print("   Forward: %s" % [round(p["predicted_fidelity"], 3) for p in forward])
    
    print("\n2. DIVERGING CHAIN (drift increases over time)")
    diverging = [1.0, 0.90, 0.72, 0.55, 0.38, 0.22]
    result = predictor.predict(diverging)
    print("   Observed: %s" % [round(s, 3) for s in diverging])
    print("   Predicted fidelity: %.4f" % result["predicted_fidelity"])
    print("   Trajectory: %s" % result["trajectory"])
    print("   Best model: %s (AIC: %s)" % (result.get("best_model", "?"), result.get("model_comparison", {})))
    print("   Confidence: %.3f" % result["confidence"])
    
    print("\n3. EARLY PREDICTION (3 hops, predict to 8)")
    early = [1.0, 0.88, 0.65]
    result = predictor.predict(early, total_steps=8)
    print("   Observed: %s" % [round(s, 3) for s in early])
    print("   Predicted at step 8: %.4f | Trajectory: %s | Best model: %s" % (
        result["predicted_fidelity"], result["trajectory"], result.get("best_model", "?")))
    
    print("\n4. TELEPHONE GAME (LLM drift tracker data)")
    telephone = [1.0, 0.948, 0.945, 1.000, 0.863, 0.832]
    result = predictor.predict(telephone, total_steps=8)
    print("   Observed: %s" % [round(s, 3) for s in telephone])
    print("   Predicted at step 8: %.4f | Trajectory: %s | Best model: %s" % (
        result["predicted_fidelity"], result["trajectory"], result.get("best_model", "?")))
    print("   Model comparison: %s" % result.get("model_comparison", {}))
    
    print("\n5. ACCURACY: predict from first 3 hops vs actual")
    partial = telephone[:3]
    result = predictor.predict(partial, total_steps=6)
    actual = telephone[-1]
    error = abs(result["predicted_fidelity"] - actual)
    print("   Predicted: %.4f | Actual: %.4f | Error: %.4f | Best model: %s" % (
        result["predicted_fidelity"], actual, error, result.get("best_model", "?")))
    
    # Save results
    outpath = Path(__file__).parent.parent / "experiments" / "drift_predictor_results.json"
    with open(outpath, "w") as f:
        json.dump({"converging": predictor.predict(converging),
                   "diverging": predictor.predict(diverging),
                   "telephone": predictor.predict(telephone)}, f, indent=2, default=str)
    print("\nSaved to", outpath)
    
    print("\n" + "=" * 72)

if __name__ == "__main__":
    demo()
